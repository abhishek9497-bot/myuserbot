import asyncio
from pathlib import Path
from telethon.tl.types import PeerUser
from telegram_service import TelegramService
from database import Database


class Event:
    def __init__(self): self.sent = []
    async def respond(self, value=None, file=None): self.sent.append((value, file))


class UnresolvedPrivateEvent(Event):
    id = 101
    sender_id = 42
    chat_id = 42
    peer_id = PeerUser(42)
    is_private = True
    out = False
    service = False
    raw_text = "QR bhejo"
    sender = None
    chat = None

    async def get_sender(self):
        raise RuntimeError("sender unresolved")

    async def get_chat(self):
        raise RuntimeError("chat unresolved")


def test_text_image_and_missing_image_do_not_crash(tmp_path):
    image = tmp_path / "qr.png"
    image.write_bytes(b"not important for mocked Telegram")
    service = object.__new__(TelegramService)
    event = Event()
    rule = {"send_image": True, "send_text": True, "image_path": str(image), "reply_text": "Pay"}
    assert asyncio.run(service.send_response(event, rule))
    assert len(event.sent) == 2
    event = Event()
    rule["image_path"] = str(Path(tmp_path) / "missing.png")
    assert asyncio.run(service.send_response(event, rule))
    assert len(event.sent) == 1


def test_unresolved_private_dm_reaches_keyword_engine_and_sends_qr_rule(tmp_path):
    database = Database(tmp_path / "test.db")
    image = tmp_path / "qr.png"
    image.write_bytes(b"qr")
    database.save_rule({
        "name": "Payment QR", "keywords_list": ["qr"], "reply_text": "Pay and send screenshot",
        "image_path": str(image), "send_text": True, "send_image": True, "enabled": True, "priority": 100,
    })
    service = object.__new__(TelegramService)
    service.database = database
    event = UnresolvedPrivateEvent()
    asyncio.run(service.handle_event(event))
    assert event.sent == [(None, str(image)), ("Pay and send screenshot", None)]


def test_unresolved_private_dm_without_matching_keyword_sends_nothing(tmp_path):
    database = Database(tmp_path / "test.db")
    database.save_rule({"name": "Payment QR", "keywords_list": ["qr"], "reply_text": "Pay"})
    service = object.__new__(TelegramService)
    service.database = database
    event = UnresolvedPrivateEvent()
    event.raw_text = "hello"
    asyncio.run(service.handle_event(event))
    assert event.sent == []
