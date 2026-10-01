import os
import re
import pytesseract
from PIL import Image, ImageFilter, UnidentifiedImageError
from config import Config

def extract_text(image_path: str) -> str:
    """
    Extracts text from an image using Tesseract OCR with preprocessing.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    try:
        # 1. Open image with Pillow
        img = Image.open(image_path)
        
        # 2. Convert to grayscale
        img = img.convert('L')
        
        # 3. Resize if small
        width, height = img.size
        if width < 1000:
            img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
            
        # 4. Sharpen
        img = img.filter(ImageFilter.SHARPEN)
        
        # 5. Run Tesseract
        # Configure tesseract executable path if set
        if getattr(Config, 'TESSERACT_CMD', None):
            pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
            
        tesseract_config = getattr(Config, 'TESSERACT_CONFIG', '--oem 3 --psm 6')
        raw_text = pytesseract.image_to_string(img, config=tesseract_config)
        
        # 6. Clean text
        # Replace multiple whitespaces/newlines with a single space
        cleaned_text = re.sub(r'\s+', ' ', raw_text)
        # Strip leading/trailing whitespace
        cleaned_text = cleaned_text.strip()
        
        # 7. Return cleaned string
        return cleaned_text
        
    except UnidentifiedImageError:
        return ''
    except Exception as e:
        # In case of other unexpected errors, returning empty string might be safer for MVP,
        # but for now we'll catch UnidentifiedImageError explicitly as per requirements.
        return ''
