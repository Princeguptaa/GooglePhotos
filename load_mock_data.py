import os
import shutil
import uuid
from app import app
from storage.db import init_db, insert_document, get_all_documents
from ocr.engine import extract_text
from config import Config

def load_mock_data():
    mock_data_dir = 'mock_data'
    uploads_dir = Config.UPLOAD_FOLDER
    
    if not os.path.exists(mock_data_dir):
        print(f"Directory {mock_data_dir} does not exist.")
        return

    # Initialize db just in case
    init_db()

    # Create app context to run DB queries safely
    with app.app_context():
        # Get existing original_names so we don't duplicate
        existing_docs = get_all_documents()
        existing_names = {doc['original_name'] for doc in existing_docs}

        os.makedirs(uploads_dir, exist_ok=True)

        loaded_count = 0
        for filename in os.listdir(mock_data_dir):
            if filename in existing_names:
                print(f"Skipping {filename}, already loaded.")
                continue

            if filename.endswith(('.png', '.jpg', '.jpeg')):
                mock_filepath = os.path.join(mock_data_dir, filename)
                
                # Generate unique ID and copy
                file_uuid = str(uuid.uuid4())
                ext = filename.rsplit('.', 1)[1].lower()
                saved_filename = f"{file_uuid}.{ext}"
                saved_path = os.path.join(uploads_dir, saved_filename)
                
                shutil.copy2(mock_filepath, saved_path)
                
                # Extract text
                ocr_text = extract_text(saved_path)
                
                # Insert DB
                insert_document({
                    'id': file_uuid,
                    'filename': saved_filename,
                    'original_name': filename,
                    'ocr_text': ocr_text
                })
                loaded_count += 1
                print(f"Loaded {filename} as {file_uuid}")

        print(f"\nLoaded {loaded_count} new documents.")

if __name__ == '__main__':
    load_mock_data()
