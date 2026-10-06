import os
import shutil
import uuid
from storage.db import init_db, insert_document, get_all_documents, clear_session_documents
from ocr.engine import extract_text
from config import Config

# Realistic camera roll photo filenames without revealing document types
SAMPLE_OCR_CACHE = {
    "IMG_20260512_104519.jpg": "Aadhaar Card Name: Samrat Mehta DOB: 12/05/1995 No: XXXX XXXX 4532",
    "IMG_20260122_161540.jpg": "Payment Receipt Amount: Rs 1,500 To: Vikram Singh Date: 22 Jan 2026",
    "IMG_20260405_091218.jpg": "ID Card Name: Meera Devi Employee ID: EMP-4421",
    "IMG_20260128_145022.jpg": "Invoice #INV-2026-0187 January 2026 Electronics Hub Total: Rs 12,899",
    "IMG_20260620_154530.jpg": "Semester Mark Sheet University of Delhi Student: Priya Patel Roll No: 2024/CS/0156 CGPA: 8.7",
    "IMG_20260318_112005.jpg": "Prescription Dr. Anita Sharma Patient: Ramesh Kumar Paracetamol 500mg Amoxicillin 250mg",
    "IMG_20260315_142011.jpg": "Payment Receipt Amount: Rs 6,500 To: Samrat Mehta Date: 15 March 2026 Ref: TXN9847321",
    "IMG_20260312_183045.jpg": "Invoice #INV-2026-0312 March 2026 Grocery Mart Total: Rs 2,340",
    "IMG_20260810_131254.jpg": "Payment Receipt Amount: Rs 3,200 To: Manoj Kumar Date: 10 Aug 2026 Ref: TXN8877112",
    "IMG_20260811_094015.jpg": "Employee ID Card Name: Manoj Kumar Department: Operations EMP-9021",
    "IMG_20260815_120530.jpg": "Aadhaar Card Name: Prince Gupta DOB: 15/08/1998 UIDAI No: XXXX XXXX 9120",
    "IMG_20260816_163012.jpg": "Semester Mark Sheet University of Delhi Student: Prince Gupta Roll No: 2024/CS/0156 CGPA: 8.7",
    "IMG_20260918_103022.jpg": "Invoice #INV-2026-0914 September 2026 Cloud Hub Technologies Total: Rs 8,450",
    "IMG_20260322_171540.jpg": "Prescription Dr. Anita Sharma Patient: Sunita Rao Cetirizine 10mg Vitamin D3",
    "test_medicine.png": "Medicine Paracetamol 500mg",
    "test_payment.png": "yment Amount Rs 6500 Date March 2(",
    "test_receipt.png": "Invoice #INV-2026-0312 Grocery Mart"
}

def seed_samples_for_session(session_id: str = 'demo') -> int:
    mock_data_dir = 'mock_data'
    uploads_dir = Config.UPLOAD_FOLDER
    
    if not os.path.exists(mock_data_dir):
        print(f"Directory {mock_data_dir} does not exist.")
        return 0

    init_db()

    # Clean up any legacy mock_* documents from earlier sessions
    from storage.db import get_connection
    from contextlib import closing
    with closing(get_connection()) as conn:
        with conn:
            conn.execute("DELETE FROM documents WHERE session_id = ? AND original_name LIKE 'mock_%'", (session_id,))

    existing_docs = get_all_documents(session_id)
    existing_names = {doc['original_name'] for doc in existing_docs}

    os.makedirs(uploads_dir, exist_ok=True)

    loaded_count = 0
    # Seed all 14 realistic sample photos
    sample_files = [f for f in sorted(SAMPLE_OCR_CACHE.keys()) if f.startswith('IMG_')]

    for filename in sample_files:
        if filename in existing_names:
            continue

        mock_filepath = os.path.join(mock_data_dir, filename)
        if not os.path.exists(mock_filepath):
            continue

        file_uuid = str(uuid.uuid4())
        ext = filename.rsplit('.', 1)[1].lower()
        saved_filename = f"{file_uuid}.{ext}"
        saved_path = os.path.join(uploads_dir, saved_filename)
        
        shutil.copy2(mock_filepath, saved_path)
        
        ocr_text = SAMPLE_OCR_CACHE[filename]
        
        insert_document({
            'id': file_uuid,
            'session_id': session_id,
            'filename': saved_filename,
            'original_name': filename,
            'ocr_text': ocr_text
        })
        loaded_count += 1

    return loaded_count

def load_mock_data():
    clear_session_documents('demo')
    loaded = seed_samples_for_session('demo')
    print(f"\nLoaded {loaded} realistic sample photo documents for session 'demo'.")

if __name__ == '__main__':
    load_mock_data()
