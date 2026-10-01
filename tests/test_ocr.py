import os
import pytest
from ocr.engine import extract_text

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MOCK_DATA_DIR = os.path.join(BASE_DIR, 'mock_data')
TEST_PAYMENT_IMG = os.path.join(MOCK_DATA_DIR, 'test_payment.png')

def test_extract_known_text():
    text = extract_text(TEST_PAYMENT_IMG)
    assert "6500" in text
    assert "Amount" in text

def test_extract_returns_string():
    text = extract_text(TEST_PAYMENT_IMG)
    assert isinstance(text, str)

def test_missing_file():
    with pytest.raises(FileNotFoundError):
        extract_text(os.path.join(MOCK_DATA_DIR, 'does_not_exist.png'))

def test_non_image_file(tmp_path):
    # Create a dummy text file
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("This is not an image.")
    
    text = extract_text(str(dummy_file))
    assert text == ""

def test_whitespace_cleanup(tmp_path, monkeypatch):
    # We can mock pytesseract.image_to_string to return a string with messy whitespace
    import pytesseract
    
    def mock_image_to_string(*args, **kwargs):
        return "  This   has  \n lots of \t whitespace  "
        
    monkeypatch.setattr(pytesseract, "image_to_string", mock_image_to_string)
    
    text = extract_text(TEST_PAYMENT_IMG)
    assert text == "This has lots of whitespace"
    assert "  " not in text
    assert "\n" not in text
    assert "\t" not in text
