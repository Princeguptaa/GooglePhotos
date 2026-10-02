import os
import re
import signal
import pytesseract
from PIL import Image, ImageFilter, ImageOps, ImageEnhance, UnidentifiedImageError
from config import Config

# Maximum pixel dimension (longest side) fed to Tesseract.
# Phone photos are often 3000-4000px — Tesseract time scales roughly
# quadratically with pixel count, so downsizing to 1000px gives a
# massive speedup with minimal OCR quality loss for document text.
OCR_MAX_DIMENSION = 1000

# Hard timeout in seconds for a single Tesseract invocation.
# On Render free tier (0.1 CPU), large images can take 30-60s+.
# Failing fast is better than a frozen spinner, but 20s was too tight for complex tables.
OCR_TIMEOUT_SECONDS = 40


def extract_text(image_path: str) -> str:
    """
    Extracts text from an image using Tesseract OCR.
    
    Preprocessing pipeline:
    1. EXIF orientation correction (phone photos)
    2. Downsize to OCR_MAX_DIMENSION if too large
    3. Convert to grayscale
    4. Upscale if too small (< 1000px wide)
    5. Sharpen
    6. Run Tesseract with a hard timeout
    7. Clean extracted text
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    try:
        # 1. Open and fix EXIF orientation (phone cameras embed rotation)
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img)

        # 2. Downsize large images — this is the biggest perf win
        width, height = img.size
        longest = max(width, height)
        if longest > OCR_MAX_DIMENSION:
            scale = OCR_MAX_DIMENSION / longest
            new_w = int(width * scale)
            new_h = int(height * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 3. Handle RGBA/transparency safely before converting to grayscale
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg.convert('L')
        else:
            img = img.convert('L')

        # 4. Upscale if too small (improves OCR on tiny images)
        width, height = img.size
        if width < 1000:
            img = img.resize((width * 2, height * 2), Image.Resampling.LANCZOS)

        # 5. Contrast enhancement and Sharpen (helps with low-contrast phone screenshots)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        img = img.filter(ImageFilter.SHARPEN)

        # 6. Configure Tesseract
        if getattr(Config, 'TESSERACT_CMD', None):
            pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD

        tesseract_config = getattr(Config, 'TESSERACT_CONFIG', f"--oem {getattr(Config, 'TESSERACT_OEM', 3)} --psm {getattr(Config, 'TESSERACT_PSM', 3)}")

        # 7. Run Tesseract with hard timeout
        raw_text = pytesseract.image_to_string(
            img,
            config=tesseract_config,
            timeout=OCR_TIMEOUT_SECONDS
        )

        # 8. Clean text
        cleaned_text = re.sub(r'\s+', ' ', raw_text).strip()
        return cleaned_text

    except RuntimeError as e:
        if 'Tesseract process timeout' in str(e):
            raise TimeoutError("Tesseract process timed out") from e
        raise
    except UnidentifiedImageError as e:
        raise ValueError(f"Could not identify or decode image: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected OCR error: {str(e)}") from e

