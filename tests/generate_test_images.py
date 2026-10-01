import os
from PIL import Image, ImageDraw, ImageFont

def create_test_image(text, filename):
    # Create a white image
    width, height = 400, 200
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Optional: try to load a font, fallback to default
    try:
        # Try to use a common font if available, else default
        # Note: on windows this might be arial.ttf
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
    
    # Draw the text
    # In newer Pillow, textsize is deprecated, using textbbox
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position to center the text
    position = ((width - text_width) / 2, (height - text_height) / 2)
    
    draw.text(position, text, fill='black', font=font)
    
    # Save the image
    mock_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mock_data')
    os.makedirs(mock_data_dir, exist_ok=True)
    file_path = os.path.join(mock_data_dir, filename)
    image.save(file_path)
    print(f"Created {file_path}")

if __name__ == "__main__":
    create_test_image("Payment Amount Rs 6500 Date March 2026", "test_payment.png")
    create_test_image("Medicine Paracetamol 500mg", "test_medicine.png")
    create_test_image("Invoice #INV-2026-0312 Grocery Mart", "test_receipt.png")
