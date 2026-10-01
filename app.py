import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from config import Config

from storage.db import init_db, insert_document, get_all_documents, get_document, delete_document, get_document_count
from ocr.engine import extract_text
from search.ranker import rank

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Initialize DB on startup
with app.app_context():
    init_db()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        return jsonify({"errors": ["No file part"]}), 400
        
    files = request.files.getlist('files')
    uploaded = []
    errors = []
    
    current_count = get_document_count()
    
    for file in files:
        if file.filename == '':
            continue
            
        if current_count >= app.config['MAX_LIBRARY_SIZE']:
            errors.append(f"Library full. Cannot upload {file.filename}.")
            continue
            
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if ext not in app.config['ALLOWED_EXTENSIONS']:
            errors.append(f"Invalid extension for {file.filename}")
            continue
            
        doc_id = str(uuid.uuid4())
        filename = f"{doc_id}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        if file_size_mb > app.config['MAX_FILE_SIZE_MB']:
            os.remove(filepath)
            errors.append(f"{file.filename} is too large (>10MB)")
            continue
            
        ocr_text = extract_text(filepath)
        
        insert_document({
            'id': doc_id,
            'filename': filename,
            'original_name': file.filename,
            'ocr_text': ocr_text
        })
        
        uploaded.append({
            "image_id": doc_id,
            "original_name": file.filename,
            "thumbnail_url": f"/api/images/{doc_id}",
            "ocr_preview": ocr_text[:50] + "..." if ocr_text else "",
            "status": "ready"
        })
        current_count += 1
        
    return jsonify({"uploaded": uploaded, "errors": errors})

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    if not query or len(query) > 200:
        return jsonify({"query": query, "results": [], "message": "Please enter a valid search term."}), 400
        
    docs = get_all_documents()
    results = rank(query, docs)
    
    if not results:
        return jsonify({"query": query, "results": [], "message": "No documents matched your search."})
        
    return jsonify({"query": query, "results": results})

@app.route('/api/library', methods=['GET'])
def library():
    docs = get_all_documents()
    library_items = [{
        "image_id": d['id'],
        "thumbnail_url": f"/api/images/{d['id']}",
        "original_name": d['original_name'],
        "has_ocr_text": bool(d['ocr_text'])
    } for d in docs]
    return jsonify(library_items)

@app.route('/api/images/<image_id>', methods=['GET'])
def get_image(image_id):
    doc = get_document(image_id)
    if not doc:
        return "Not found", 404
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
    if not os.path.exists(filepath):
        return "File not found", 404
    return send_file(filepath)

@app.route('/api/images/<image_id>/ocr', methods=['GET'])
def get_ocr(image_id):
    doc = get_document(image_id)
    if not doc:
        return "Not found", 404
    return jsonify({"ocr_text": doc['ocr_text']})

@app.route('/api/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    doc = get_document(image_id)
    if not doc:
        return "Not found", 404
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], doc['filename'])
    if os.path.exists(filepath):
        os.remove(filepath)
        
    delete_document(image_id)
    return jsonify({"deleted": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=app.config['DEBUG'])
