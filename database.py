import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    keywords TEXT NOT NULL DEFAULT '[]',
                    match_type TEXT NOT NULL DEFAULT 'ANY_KEYWORD',
                    reply_text TEXT NOT NULL DEFAULT '',
                    image_path TEXT,
                    send_text INTEGER NOT NULL DEFAULT 1,
                    send_image INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 0,
                    cooldown_seconds INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS message_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    username TEXT,
                    incoming_text TEXT NOT NULL DEFAULT '',
                    matched_rule_id INTEGER,
                    reply_sent INTEGER NOT NULL DEFAULT 0,
                    cooldown_blocked INTEGER NOT NULL DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    telegram_message_id INTEGER
                );
                CREATE UNIQUE INDEX IF NOT EXISTS message_log_event
                    ON message_log(telegram_user_id, telegram_message_id)
                    WHERE telegram_message_id IS NOT NULL;
                CREATE TABLE IF NOT EXISTS rule_cooldowns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    rule_id INTEGER NOT NULL,
                    last_sent_at TEXT NOT NULL,
                    UNIQUE(telegram_user_id, rule_id)
                );
            """)

    def list_rules(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM rules"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY priority DESC, id ASC"
        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["keywords_list"] = json.loads(item["keywords"] or "[]")
            item["enabled"] = bool(item["enabled"])
            item["send_text"] = bool(item["send_text"])
            item["send_image"] = bool(item["send_image"])
            result.append(item)
        return result

    def get_rule(self, rule_id: int) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["keywords_list"] = json.loads(item["keywords"] or "[]")
        return item

    def save_rule(self, values: dict[str, Any], rule_id: int | None = None) -> int:
        now = utc_now()
        fields = (values["name"], json.dumps(values["keywords_list"], ensure_ascii=False),
              values.get("match_type", "ANY_KEYWORD"), values.get("reply_text", ""), values.get("image_path"),
                  int(values.get("send_text", True)), int(values.get("send_image", False)),
                  int(values.get("enabled", True)), int(values.get("priority", 0)),
                  int(values.get("cooldown_seconds", 0)))
        with self.connect() as connection:
            if rule_id is None:
                cursor = connection.execute(
                    """INSERT INTO rules (name, keywords, match_type, reply_text, image_path,
                    send_text, send_image, enabled, priority, cooldown_seconds, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", fields + (now, now))
                return int(cursor.lastrowid)
            connection.execute(
                """UPDATE rules SET name=?, keywords=?, match_type=?, reply_text=?, image_path=?,
                send_text=?, send_image=?, enabled=?, priority=?, cooldown_seconds=?, updated_at=?
                WHERE id=?""", fields + (now, rule_id))
            return rule_id

    def delete_rule(self, rule_id: int) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            connection.execute("DELETE FROM rule_cooldowns WHERE rule_id = ?", (rule_id,))

    def is_duplicate(self, user_id: int, message_id: int | None) -> bool:
        if message_id is None:
            return False
        with self.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM message_log WHERE telegram_user_id=? AND telegram_message_id=?",
                (user_id, message_id)).fetchone() is not None

    def cooldown_remaining(self, user_id: int, rule_id: int, cooldown_seconds: int) -> int:
        if cooldown_seconds <= 0:
            return 0
        with self.connect() as connection:
            row = connection.execute(
                "SELECT last_sent_at FROM rule_cooldowns WHERE telegram_user_id=? AND rule_id=?",
                (user_id, rule_id)).fetchone()
        if not row:
            return 0
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(row["last_sent_at"])).total_seconds()
        return max(0, int(cooldown_seconds - elapsed))

    def update_cooldown(self, user_id: int, rule_id: int) -> None:
        now = utc_now()
        with self.connect() as connection:
            connection.execute("""INSERT INTO rule_cooldowns (telegram_user_id, rule_id, last_sent_at)
                VALUES (?, ?, ?) ON CONFLICT(telegram_user_id, rule_id)
                DO UPDATE SET last_sent_at=excluded.last_sent_at""", (user_id, rule_id, now))

    def log_message(self, user_id: int, username: str | None, text: str,
                    rule_id: int | None, reply_sent: bool, cooldown_blocked: bool,
                    message_id: int | None) -> None:
        with self.connect() as connection:
            connection.execute("""INSERT OR IGNORE INTO message_log
                (telegram_user_id, username, incoming_text, matched_rule_id, reply_sent,
                cooldown_blocked, timestamp, telegram_message_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, text, rule_id, int(reply_sent), int(cooldown_blocked), utc_now(), message_id))

    def stats(self) -> dict[str, int]:
        with self.connect() as connection:
            values = connection.execute("""SELECT
                (SELECT COUNT(*) FROM rules) total_rules,
                (SELECT COUNT(*) FROM rules WHERE enabled=1) enabled_rules,
                (SELECT COUNT(*) FROM rules WHERE enabled=0) disabled_rules,
                (SELECT COUNT(*) FROM message_log WHERE matched_rule_id IS NOT NULL) matched_messages,
                (SELECT COUNT(*) FROM message_log WHERE cooldown_blocked=1) cooldown_blocked_messages""").fetchone()
        return dict(values)

    def recent_matches(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("""SELECT message_log.*, rules.name rule_name
                FROM message_log LEFT JOIN rules ON rules.id=message_log.matched_rule_id
                WHERE matched_rule_id IS NOT NULL ORDER BY timestamp DESC LIMIT ?""", (limit,)).fetchall()
        return [dict(row) for row in rows]
