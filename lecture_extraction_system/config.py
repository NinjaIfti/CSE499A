import os
from pathlib import Path

# Setup directories
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
DB_DIR = BASE_DIR / "database"

UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = f"sqlite:///{DB_DIR}/lectures.db"

# API
COLAB_API_URL = os.getenv("COLAB_API_URL", "http://localhost:8000")
API_TIMEOUT = 300

# Video
FRAME_EXTRACTION_RATE = 30
VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
MAX_VIDEO_SIZE_MB = 500

# Whisper - change to tiny/small/medium/large for speed or accuracy
WHISPER_MODEL = "base"

# OCR - add more languages like ['en', 'es', 'fr'] if needed
OCR_LANGUAGES = ['en']
OCR_CONFIDENCE_THRESHOLD = 0.5

# LLM
CHUNK_SIZE = 1000
MAX_PROMPT_LENGTH = 2000
