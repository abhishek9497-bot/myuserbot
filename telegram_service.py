import asyncio
import logging
from pathlib import Path
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel, Chat, PeerChannel, PeerChat, PeerUser, User

from config import require_setting, TELEGRAM_SESSION_NAME
from database import Database
from rule_engine import find_matching_rule

logger = logging.getLogger(__name__)


def _entity_type(entity: Any) -> str:
    return type(entity).__name__ if entity is not None else "None"


def _is_type(entity: Any, *types: type, names: tuple[str, ...] = ()) -> bool:
    return entity is not None and (isinstance(entity, types) or _entity_type(entity) in names)


def classify_event(event: Any, sender: Any = None, chat: Any = None) -> str:
    if getattr(event, "out", False):
        return "outgoing"
    if getattr(event, "service", False):
        return "service"
    peer = getattr(event, "peer_id", None)
    if isinstance(peer, PeerChannel) or _entity_type(peer) == "PeerChannel":
        return "channel"
    if isinstance(peer, PeerChat) or _entity_type(peer) == "PeerChat":
        return "group"
    if not getattr(event, "is_private", False):
        entity = chat or getattr(event, "chat", None)
        if _is_type(entity, Channel, names=("Channel",)):
            return "channel"
        if _is_type(entity, Chat, names=("Chat",)):
            return "group"
        return "group"
    entity = sender or getattr(event, "sender", None) or chat or getattr(event, "chat", None)
    if _is_type(entity, User, names=("User",)) and getattr(entity, "bot", False):
        return "bot"
    if _is_type(entity, User, names=("User",)):
        return "private_user"
    if isinstance(peer, PeerUser) or _entity_type(peer) == "PeerUser":
        return "private_unresolved"
    return "private_unresolved"


class TelegramService:
    def __init__(self, database: Database):
        self.database = database
        self.client = TelegramClient(TELEGRAM_SESSION_NAME, int(require_setting("TELEGRAM_API_ID")),
                                     require_setting("TELEGRAM_API_HASH"))
        self.client.add_event_handler(self.handle_event, events.NewMessage(incoming=True))

    async def handle_event(self, event: Any) -> None:
        sender = await self._get_entity(event, "get_sender")
        chat = await self._get_entity(event, "get_chat")
        category = classify_event(event, sender=sender, chat=chat)
        logger.info(
            "Telegram event: message_id=%s sender_id=%s chat_id=%s peer_id_type=%s "
            "event.is_private=%s sender_entity_type=%s chat_entity_type=%s sender.bot=%s "
            "outgoing=%s final_classification=%s",
            getattr(event, "id", None), getattr(event, "sender_id", None),
            getattr(event, "chat_id", None), _entity_type(getattr(event, "peer_id", None)),
            getattr(event, "is_private", None), _entity_type(sender or getattr(event, "sender", None)),
            _entity_type(chat or getattr(event, "chat", None)),
            getattr(sender, "bot", None), getattr(event, "out", False), category,
        )
        if category not in {"private_user", "private_unresolved"}:
            logger.info("Ignored: %s", category)
            return
        if category == "private_unresolved":
            logger.info("Accepted: private_unresolved")
        user = sender or getattr(event, "sender", None)
        user_id = int(getattr(user, "id", getattr(event, "sender_id", getattr(event, "chat_id", 0))))
        message_id = getattr(event, "id", None)
        if self.database.is_duplicate(user_id, message_id):
            logger.info("Duplicate event ignored")
            return
        text = getattr(event, "raw_text", "") or ""
        username = getattr(user, "username", None)
        logger.info("Checking keyword rules")
        rule = find_matching_rule(text, self.database.list_rules(enabled_only=True))
        if rule is None:
            self.database.log_message(user_id, username, text, None, False, False, message_id)
            logger.info("No rule matched")
            return
        rule_id = int(rule["id"])
        remaining = self.database.cooldown_remaining(user_id, rule_id, int(rule["cooldown_seconds"]))
        if remaining:
            self.database.log_message(user_id, username, text, rule_id, False, True, message_id)
            logger.info("Cooldown blocked: user=%s rule=%s remaining=%ss", user_id, rule_id, remaining)
            return
        sent = await self.send_response(event, rule)
        self.database.log_message(user_id, username, text, rule_id, sent, False, message_id)
        if sent:
            self.database.update_cooldown(user_id, rule_id)
            logger.info("Cooldown updated")

    async def _get_entity(self, event: Any, method_name: str) -> Any:
        getter = getattr(event, method_name, None)
        if getter is None:
            return None
        try:
            return await getter()
        except Exception:
            logger.debug("Could not resolve Telegram entity via %s", method_name, exc_info=True)
            return None

    async def send_response(self, event: Any, rule: dict[str, Any]) -> bool:
        delivered = False
        if rule.get("send_image") and rule.get("image_path"):
            image = Path(rule["image_path"])
            if image.is_file():
                try:
                    await event.respond(file=str(image))
                    delivered = True
                    logger.info("Image sent")
                except FloodWaitError as error:
                    logger.error("Telegram FloodWait: %ss", error.seconds)
                    await asyncio.sleep(error.seconds)
                except Exception:
                    logger.exception("Image send failed")
            else:
                logger.error("Image file missing: %s", image)
        if rule.get("send_text") and rule.get("reply_text", "").strip():
            try:
                await event.respond(rule["reply_text"])
                delivered = True
                logger.info("Text sent")
            except FloodWaitError as error:
                logger.error("Telegram FloodWait: %ss", error.seconds)
                await asyncio.sleep(error.seconds)
            except Exception:
                logger.exception("Text send failed")
        return delivered

    def run(self) -> None:
        logger.info("Telegram connecting")
        self.client.start()
        logger.info("Telegram connected")
        self.client.run_until_disconnected()
