from telethon import TelegramClient

from config import TELEGRAM_SESSION_NAME, require_setting


def main() -> None:
    client = TelegramClient(
        TELEGRAM_SESSION_NAME,
        int(require_setting("TELEGRAM_API_ID")),
        require_setting("TELEGRAM_API_HASH"),
    )
    with client:
        client.start(phone=lambda: input("Telegram phone number: "))
        print("Telegram login complete. Session saved.")


if __name__ == "__main__":
    main()
