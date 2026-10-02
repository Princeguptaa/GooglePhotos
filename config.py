import os

class Config:
    # Paths
    if os.environ.get('RENDER', '').lower() == 'true':
        UPLOAD_FOLDER = '/data/uploads'
        DATABASE_PATH = '/data/instance/documents.db'
    else:
        UPLOAD_FOLDER = os.path.join('static', 'uploads')
        DATABASE_PATH = os.path.join('instance', 'documents.db')

    # Upload constraints
    MAX_FILE_SIZE_MB = 10
    MAX_LIBRARY_SIZE = 30         # Max total uploaded docs
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

    # OCR
    TESSERACT_CMD = os.environ.get('TESSERACT_CMD', 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe' if os.name == 'nt' and os.path.exists('C:\\Program Files\\Tesseract-OCR\\tesseract.exe') else 'tesseract')
    TESSERACT_PSM = 6             # Page segmentation mode
    TESSERACT_OEM = 3             # OCR engine mode

    # Search
    MIN_SCORE_THRESHOLD = 0.20    # Below this → no match (filters incidental noise)
    SNIPPET_MAX_LENGTH = 150      # Chars around best match
    TFIDF_WEIGHT = 0.7
    FUZZY_WEIGHT = 0.3

    # Server
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-prod')
