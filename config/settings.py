import os

from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# ==========================================
# APPLICATION
# ==========================================

APP_NAME = "Opportune AI"
APP_VERSION = "0.1.0"
APP_ENV = os.getenv("APP_ENV", "development")


# ==========================================
# DATABASE
# ==========================================

DATABASE_PATH = "opportune.db"


# ==========================================
# LLM API KEYS
# ==========================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


# ==========================================
# OPPORTUNITY TYPES
# ==========================================

SUPPORTED_OPPORTUNITY_TYPES = [
    "Job",
    "Internship",
    "Master's",
    "Scholarship",
    "Research",
]