import os
from PIL import Image, ImageDraw, ImageFont

def create_mock_image(filename, text, size=(800, 400), bg_color=(255, 255, 255), text_color=(0, 0, 0)):
    # Create a new image
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Try to load a font, otherwise use default
    try:
        # Use a larger font for readability
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
        
    # Add text to the image
    # Simple line wrapping or multiple draw calls can be used here.
    # For simplicity, let's just split by ' — ' and draw line by line
    lines = text.split(' — ')
    y_text = 40
    for line in lines:
        try:
            # Pillow >= 8.0.0
            left, top, right, bottom = font.getbbox(line)
            width = right - left
            height = bottom - top
        except AttributeError:
            width, height = draw.textsize(line, font=font)
        
        draw.text((40, y_text), line, font=font, fill=text_color)
        y_text += height + 10
        
    # Save the image
    filepath = os.path.join('mock_data', filename)
    os.makedirs('mock_data', exist_ok=True)
    img.save(filepath)
    print(f"Generated {filepath}")

def main():
    mocks = [
        ("mock_payment.png", "Payment Receipt — Amount: Rs 6,500 — To: Samrat Mehta — Date: 15 March 2026 — Ref: TXN9847321"),
        ("mock_aadhaar.png", "Aadhaar Card — Name: Samrat Mehta — DOB: 12/05/1995 — No: XXXX XXXX 4532"),
        ("mock_receipt.png", "Invoice #INV-2026-0312 — March 2026 — Grocery Mart — Total: Rs 2,340"),
        ("mock_medicine.png", "Prescription — Dr. Anita Sharma — Patient: Ramesh Kumar — Paracetamol 500mg — Amoxicillin 250mg"),
        ("mock_marksheet.png", "Semester Mark Sheet — University of Delhi — Student: Priya Patel — Roll No: 2024/CS/0156 — CGPA: 8.7"),
        ("mock_distractor_1.png", "Payment Receipt — Amount: Rs 1,500 — To: Vikram Singh — Date: 22 Jan 2026"),
        ("mock_distractor_2.png", "ID Card — Name: Meera Devi — Employee ID: EMP-4421"),
        ("mock_distractor_3.png", "Invoice #INV-2026-0187 — January 2026 — Electronics Hub — Total: Rs 12,899")
    ]
    
    for filename, text in mocks:
        create_mock_image(filename, text)

if __name__ == '__main__':
    main()
