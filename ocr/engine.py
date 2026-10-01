import os
from PIL import Image, ImageFilter, UnidentifiedImageError
import pytesseract
from config import Config

def extract_text(image_path: str) -> str:
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = Image.open(image_path)
        img = img.convert('L') # grayscale
        
        width, height = img.size
        if width < 1000:
            img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)
        
        img = img.filter(ImageFilter.SHARPEN)
        
        # We allow overriding tesseract cmd mostly for local dev. On docker it's in PATH.
        if Config.TESSERACT_CMD != 'tesseract':
            pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD
            
        custom_config = f'--oem {Config.TESSERACT_OEM} --psm {Config.TESSERACT_PSM}'
        text = pytesseract.image_to_string(img, config=custom_config)
        
        # Cleanup text
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return ' '.join(cleaned_lines)
        
    except FileNotFoundError:
        raise
    except UnidentifiedImageError:
        return ""
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""
