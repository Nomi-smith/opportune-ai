import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "opportune.db"
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

APP_NAME = "Opportune AI"
APP_VERSION = "0.2.0"
APP_ENV = os.getenv("APP_ENV", "development")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_SEARCH_MODEL = os.getenv("OPENROUTER_SEARCH_MODEL", "openrouter/free")
OPENROUTER_SEARCH_ENGINE = os.getenv("OPENROUTER_SEARCH_ENGINE", "auto")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

OPPORTUNITY_TYPES = [
    "All", "Job", "Internship", "Master's", "Scholarship", "Research"
]

APPLICATION_STATUSES = [
    "Saved", "Interested", "Preparing", "Applied",
    "Interview", "Accepted", "Rejected", "Closed"
]
