import importlib.util
import os
from pathlib import Path

from config import BASE_DIR, DATABASE_PATH, UPLOAD_DIR
from database import Database


def main() -> int:
    checks = {
        ".env exists": (BASE_DIR / ".env").is_file(),
        "Telegram API ID configured": bool(os.getenv("TELEGRAM_API_ID", "").strip()),
        "Telegram API HASH configured": bool(os.getenv("TELEGRAM_API_HASH", "").strip()),
        "telethon installed": importlib.util.find_spec("telethon") is not None,
        "flask installed": importlib.util.find_spec("flask") is not None,
        "python-dotenv installed": importlib.util.find_spec("dotenv") is not None,
    }
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        db = Database(DATABASE_PATH)
        db.save_rule({"name": "setup check", "keywords_list": ["check"]})
        rule = db.list_rules()[-1]
        db.delete_rule(rule["id"])
        checks["database initializes"] = True
        checks["rules and cooldown tables work"] = True
    except Exception:
        checks["database initializes"] = False
        checks["rules and cooldown tables work"] = False
    checks["static/uploads exists"] = UPLOAD_DIR.is_dir()
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
