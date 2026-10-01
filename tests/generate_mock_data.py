import os
from PIL import Image, ImageDraw, ImageFont

MOCK_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'mock_data'))

os.makedirs(MOCK_DATA_DIR, exist_ok=True)

docs = [
    ("mock_payment.png", "Payment Receipt — Amount: Rs 6,500\nTo: Samrat Mehta\nDate: 15 March 2026\nRef: TXN9847321"),
    ("mock_aadhaar.png", "Aadhaar Card\nName: Samrat Mehta\nDOB: 12/05/1995\nNo: XXXX XXXX 4532"),
    ("mock_receipt.png", "Invoice #INV-2026-0312\nMarch 2026\nGrocery Mart\nTotal: Rs 2,340"),
    ("mock_medicine.png", "Prescription\nDr. Anita Sharma\nPatient: Ramesh Kumar\nParacetamol 500mg\nAmoxicillin 250mg"),
    ("mock_marksheet.png", "Semester Mark Sheet\nUniversity of Delhi\nStudent: Priya Patel\nRoll No: 2024/CS/0156\nCGPA: 8.7"),
    ("mock_distractor_1.png", "Payment Receipt — Amount: Rs 1,500\nTo: Vikram Singh\nDate: 22 Jan 2026"),
    ("mock_distractor_2.png", "ID Card\nName: Meera Devi\nEmployee ID: EMP-4421"),
    ("mock_distractor_3.png", "Invoice #INV-2026-0187\nJanuary 2026\nElectronics Hub\nTotal: Rs 12,899")
]

for filename, text in docs:
    # Create white image
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    # Using default font, scale it up simply by drawing multiple times slightly offset or just using default
    # A simple approach for mock data:
    d.text((50, 50), text, fill=(0, 0, 0))
    # resize to make text somewhat readable if default font is too small
    img = img.resize((1600, 1200), Image.Resampling.LANCZOS)
    
    img.save(os.path.join(MOCK_DATA_DIR, filename))

print("Mock data generated successfully!")
