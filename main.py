import logging
import threading

from admin_app import create_app
from config import ADMIN_HOST, ADMIN_PORT, BASE_DIR
from database import Database
from telegram_service import TelegramService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    database = Database(BASE_DIR / "data" / "newaiseller.db")
    app = create_app(database)
    flask_thread = threading.Thread(
        target=lambda: app.run(host=ADMIN_HOST, port=ADMIN_PORT, debug=False, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()
    TelegramService(database).run()


if __name__ == "__main__":
    main()
