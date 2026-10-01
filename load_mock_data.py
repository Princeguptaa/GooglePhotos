import os
import shutil
import uuid
from app import app
from storage.db import init_db, insert_document
from ocr.engine import extract_text

def load_data():
    with app.app_context():
        init_db()
        
    mock_dir = os.path.join(os.path.dirname(__file__), 'mock_data')
    uploads_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(uploads_dir, exist_ok=True)
    
    print("Loading mock data...")
    count = 0
    if not os.path.exists(mock_dir):
        print(f"Directory {mock_dir} not found. Run generate_mock_data.py first.")
        return
        
    for filename in os.listdir(mock_dir):
        if not filename.endswith('.png'):
            continue
            
        src_path = os.path.join(mock_dir, filename)
        doc_id = str(uuid.uuid4())
        ext = 'png'
        new_filename = f"{doc_id}.{ext}"
        dst_path = os.path.join(uploads_dir, new_filename)
        
        shutil.copy2(src_path, dst_path)
        
        try:
            text = extract_text(dst_path)
            # if OCR fails locally, insert with fake text for testing? 
            # Or just use the extracted text. If tesseract is not available, it might fail.
        except Exception as e:
            print(f"OCR failed for {filename}: {e}")
            text = filename.replace('_', ' ').replace('.png', '')  # Fallback
            
        insert_document({
            'id': doc_id,
            'filename': new_filename,
            'original_name': filename,
            'ocr_text': text
        })
        count += 1
        
    print(f"Loaded {count} documents.")

if __name__ == '__main__':
    load_data()
