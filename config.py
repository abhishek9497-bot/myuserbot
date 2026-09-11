import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def require_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "newaiseller_session")
ADMIN_HOST = os.getenv("ADMIN_HOST", "127.0.0.1")
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "5000"))
DATABASE_PATH = BASE_DIR / "data" / "newaiseller.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
