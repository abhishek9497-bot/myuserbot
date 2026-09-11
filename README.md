# NewAISeller

A small local Telegram DM automation tool. It uses your existing personal Telegram account through Telethon. There is no AI, bot account, public hosting, or admin login.

## Setup

1. Install Python 3.11 or newer.
2. Open this folder in a terminal and install dependencies:
   `python -m pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Add your Telegram API ID and API hash from https://my.telegram.org. Never share them.
5. Create the Telegram session with:
   `python login_telegram.py`
6. Complete the phone, verification code, and, only if requested, 2FA prompts.
7. Start the application:
   `python main.py`
8. Open http://127.0.0.1:5000. The dashboard opens directly without login.

## Rules

Open **Rules**, choose **Add rule**, enter comma-separated keywords, fixed text, priority, and a cooldown number/unit. Enable text and/or image delivery. Uploaded JPG, JPEG, PNG, and WEBP files are stored under `static/uploads/` with generated filenames.

Rules are checked by priority. A response is sent only for an incoming one-to-one message from a normal Telegram user. Cooldowns are independent for each Telegram user and rule, persist in SQLite, and begin only after text or image delivery succeeds. Repeated delivery of the same Telegram message ID is ignored.

## Troubleshooting

- Run `python setup_check.py` to check `.env`, dependencies, folders, and database initialization.
- If login does not start, remove the session only when you intentionally want to authenticate again, then rerun `python login_telegram.py`.
- If the panel is unreachable, confirm that `ADMIN_HOST=127.0.0.1` and the selected port is free.
- The listener ignores groups, channels, bots, service messages, and your own outgoing messages.
- Stop the application with Ctrl+C.

## Tests

Run `pytest -q`. Tests use a temporary SQLite database and do not contact Telegram.
