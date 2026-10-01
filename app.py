import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from config import Config
from storage import db
from ocr import engine
from search import ranker

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload folder exists on startup
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_db()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload():
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
            
        if db.get_document_count() >= Config.MAX_LIBRARY_SIZE:
            errors.append("Max library size reached")
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
            'filename': saved_filename,
            'original_name': file.filename,
            'ocr_text': ocr_text
        }
        db.insert_document(doc)
        
        thumbnail_url = f"/static/uploads/{saved_filename}"

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
    query = request.args.get('q', '')
    if not query or len(query) > 200:
        return jsonify({"error": "Invalid query"}), 400
        
    documents = db.get_all_documents()
    results = ranker.rank(query, documents)
    
    formatted_results = []
    for r in results:
        doc = db.get_document(r['id'])
        thumbnail_url = f"/static/uploads/{doc['filename']}" if doc else ""
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
    documents = db.get_all_documents()
    results = []
    for doc in documents:
        results.append({
            "id": doc['id'],
            "thumbnail_url": f"/static/uploads/{doc['filename']}",
            "original_name": doc['original_name'],
            "has_ocr_text": bool(doc['ocr_text'].strip())
        })
    return jsonify(results), 200

@app.route('/api/images/<image_id>', methods=['GET'])
def get_image(image_id):
    doc = db.get_document(image_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    path = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
    if not os.path.exists(path):
        return jsonify({"error": "File missing"}), 404
    
    # We should send file relative to the current working directory, or using absolute path.
    return send_file(os.path.abspath(path))

@app.route('/api/images/<image_id>/ocr', methods=['GET'])
def get_image_ocr(image_id):
    doc = db.get_document(image_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"ocr_text": doc['ocr_text']}), 200

@app.route('/api/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    doc = db.get_document(image_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    
    path = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
    if os.path.exists(path):
        os.remove(path)
        
    db.delete_document(image_id)
    return jsonify({"deleted": True}), 200

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])
