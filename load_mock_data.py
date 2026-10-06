import os
import shutil
import uuid
from storage.db import init_db, insert_document, get_all_documents
from ocr.engine import extract_text
from config import Config

SAMPLE_OCR_CACHE = {
    "mock_aadhaar.png": "Aadhaar Card Name: Samrat Mehta DOB: 12/05/1995 No: XXXX XXXX 4532",
    "mock_distractor_1.png": "Payment Receipt Amount: Rs 1,500 To: Vikram Singh Date: 22 Jan 2026",
    "mock_distractor_2.png": "ID Card Name: Meera Devi Employee ID: EMP-4421",
    "mock_distractor_3.png": "Invoice #INV-2026-0187 January 2026 Electronics Hub Total: Rs 12,899",
    "mock_marksheet.png": "Semester Mark Sheet University of Delhi Student: Priya Patel Roll No: 2024/CS/0156 CGPA: 8.7",
    "mock_medicine.png": "Prescription Dr. Anita Sharma Patient: Ramesh Kumar Paracetamol 500mg Amoxicillin 250mg",
    "mock_payment.png": "Payment Receipt Amount: Rs 6,500 To: Samrat Mehta Date: 15 March 2026 Ref: TXN9847321",
    "mock_receipt.png": "Invoice #INV-2026-0312 March 2026 Grocery Mart Total: Rs 2,340",
    "mock_manoj_payment.png": "Payment Receipt Amount: Rs 3,200 To: Manoj Kumar Date: 10 Aug 2026 Ref: TXN8877112",
    "mock_manoj_id.png": "Employee ID Card Name: Manoj Kumar Department: Operations EMP-9021",
    "mock_prince_aadhaar.png": "Aadhaar Card Name: Prince Gupta DOB: 15/08/1998 UIDAI No: XXXX XXXX 9120",
    "mock_prince_marksheet.png": "Semester Mark Sheet University of Delhi Student: Prince Gupta Roll No: 2024/CS/0156 CGPA: 8.7",
    "mock_invoice_september.png": "Invoice #INV-2026-0914 September 2026 Cloud Hub Technologies Total: Rs 8,450",
    "mock_prescription_generic.png": "Prescription Dr. Anita Sharma Patient: Sunita Rao Cetirizine 10mg Vitamin D3",
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

    existing_docs = get_all_documents(session_id)
    existing_names = {doc['original_name'] for doc in existing_docs}

    os.makedirs(uploads_dir, exist_ok=True)

    loaded_count = 0
    for filename in sorted(os.listdir(mock_data_dir)):
        if filename in existing_names:
            continue

        if filename.startswith('mock_') and filename.endswith(('.png', '.jpg', '.jpeg')):
            mock_filepath = os.path.join(mock_data_dir, filename)
            
            file_uuid = str(uuid.uuid4())
            ext = filename.rsplit('.', 1)[1].lower()
            saved_filename = f"{file_uuid}.{ext}"
            saved_path = os.path.join(uploads_dir, saved_filename)
            
            shutil.copy2(mock_filepath, saved_path)
            
            if filename in SAMPLE_OCR_CACHE:
                ocr_text = SAMPLE_OCR_CACHE[filename]
            else:
                try:
                    ocr_text = extract_text(saved_path)
                except Exception:
                    ocr_text = ""
            
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
    loaded = seed_samples_for_session('demo')
    print(f"\nLoaded {loaded} documents for session 'demo'.")

if __name__ == '__main__':
    load_mock_data()
