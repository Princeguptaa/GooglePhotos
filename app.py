import os
import uuid
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, send_file, session
from config import Config
from storage import db
from ocr import engine
from search import ranker

app = Flask(__name__)
app.config.from_object(Config)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Ensure upload folder exists on startup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_db()

# Pre-seed the golden demo session if empty
from load_mock_data import seed_samples_for_session
try:
    if db.get_document_count('demo') == 0:
        seed_samples_for_session('demo')
except Exception:
    pass

def get_current_session_id() -> str:
    """Retrieves or creates a session ID.
    Priority:
    1. X-Session-ID header (from JS / localStorage / API clients)
    2. session_id query param (for <img> tags / direct links / golden session links)
    3. Flask signed cookie session
    """
    header_sid = request.headers.get('X-Session-ID')
    if header_sid and 1 <= len(header_sid) <= 64:
        session['session_id'] = header_sid
        sid = header_sid
    else:
        param_sid = request.args.get('session_id')
        if param_sid and 1 <= len(param_sid) <= 64:
            session['session_id'] = param_sid
            sid = param_sid
        else:
            if 'session_id' not in session:
                session['session_id'] = str(uuid.uuid4())
            sid = session['session_id']

    session.permanent = True

    # Auto-seed golden demo session if it was requested and currently empty
    if sid == 'demo' and db.get_document_count('demo') == 0:
        try:
            seed_samples_for_session('demo')
        except Exception:
            pass

    return sid

@app.before_request
def ensure_session():
    session.permanent = True
    get_current_session_id()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    session_id = get_current_session_id()
    return render_template('index.html', session_id=session_id)

@app.route('/api/session', methods=['GET'])
def get_session():
    session_id = get_current_session_id()
    return jsonify({
        "session_id": session_id,
        "document_count": db.get_document_count(session_id)
    }), 200

@app.route('/api/session/reset', methods=['POST'])
def reset_session():
    new_id = str(uuid.uuid4())
    session['session_id'] = new_id
    return jsonify({"session_id": new_id}), 200

@app.route('/api/upload', methods=['POST'])
def upload():
    session_id = get_current_session_id()
    if 'files' not in request.files:
        return jsonify({"uploaded": [], "errors": ["No file part"]}), 400
        
    files = request.files.getlist('files')
    uploaded = []
    errors = []
    
    for file in files:
        if file.filename == '':
            errors.append("Empty filename")
            continue
            
        if not allowed_file(file.filename):
            errors.append(f"{file.filename} has an invalid extension")
            continue
            
        file.seek(0, os.SEEK_END)
        file_length = file.tell()
        file.seek(0)
        
        if file_length > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
            errors.append(f"{file.filename} exceeds {Config.MAX_FILE_SIZE_MB}MB")
            continue
            
        if db.get_document_count(session_id) >= Config.MAX_LIBRARY_SIZE:
            errors.append(f"Max library size ({Config.MAX_LIBRARY_SIZE} documents) reached for this session")
            continue

        ext = file.filename.rsplit('.', 1)[1].lower()
        image_id = str(uuid.uuid4())
        saved_filename = f"{image_id}.{ext}"
        saved_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        
        file.save(saved_path)
        
        try:
            ocr_text = engine.extract_text(saved_path)
        except Exception as e:
            errors.append(f"OCR failed for {file.filename}: {str(e)}")
            continue
            
        doc = {
            'id': image_id,
            'session_id': session_id,
            'filename': saved_filename,
            'original_name': file.filename,
            'ocr_text': ocr_text
        }
        db.insert_document(doc)
        
        thumbnail_url = f"/api/images/{image_id}"

        uploaded.append({
            "image_id": image_id,
            "original_name": file.filename,
            "thumbnail_url": thumbnail_url,
            "ocr_preview": ocr_text[:100] + ("..." if len(ocr_text) > 100 else ""),
            "status": "ready"
        })
        
    return jsonify({"uploaded": uploaded, "errors": errors}), 200

@app.route('/api/search', methods=['GET'])
def search():
    session_id = get_current_session_id()
    query = request.args.get('q', '')
    if not query or len(query) > 200:
        return jsonify({"error": "Invalid query"}), 400
        
    documents = db.get_all_documents(session_id)
    results = ranker.rank(query, documents)
    
    formatted_results = []
    for r in results:
        doc = db.get_document(r['id'], session_id)
        thumbnail_url = f"/api/images/{r['id']}" if doc else ""
        formatted_results.append({
            "image_id": r['id'],
            "thumbnail_url": thumbnail_url,
            "score": r['score'],
            "snippet": r['snippet'],
            "highlight_ranges": r['highlight_ranges']
        })
        
    if not formatted_results:
        return jsonify({
            "query": query,
            "results": [],
            "message": "No documents matched your search."
        }), 200
        
    return jsonify({
        "query": query,
        "results": formatted_results
    }), 200

@app.route('/api/library', methods=['GET'])
def library():
    session_id = get_current_session_id()
    documents = db.get_all_documents(session_id)
    results = []
    for doc in documents:
        results.append({
            "id": doc['id'],
            "thumbnail_url": f"/api/images/{doc['id']}",
            "original_name": doc['original_name'],
            "has_ocr_text": bool(doc['ocr_text'].strip())
        })
    return jsonify(results), 200

@app.route('/api/images/<image_id>', methods=['GET'])
def get_image(image_id):
    session_id = get_current_session_id()
    doc = db.get_document(image_id, session_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    path = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
    if not os.path.exists(path):
        return jsonify({"error": "File missing"}), 404
    
    return send_file(os.path.abspath(path))

@app.route('/api/images/<image_id>/ocr', methods=['GET'])
def get_image_ocr(image_id):
    session_id = get_current_session_id()
    doc = db.get_document(image_id, session_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"ocr_text": doc['ocr_text']}), 200

@app.route('/api/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    session_id = get_current_session_id()
    doc = db.get_document(image_id, session_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    
    path = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
        
    db.delete_document(image_id, session_id)
    return jsonify({"deleted": True}), 200

@app.route('/api/load-samples', methods=['POST'])
def load_sample_docs():
    session_id = get_current_session_id()
    from load_mock_data import seed_samples_for_session
    loaded = seed_samples_for_session(session_id)
    return jsonify({
        "loaded": loaded, 
        "message": f"Loaded {loaded} sample document(s) into your session."
    }), 200

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])

