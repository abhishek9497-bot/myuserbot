from types import SimpleNamespace
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, User
from telegram_service import classify_event


class Chat:
    pass


class Channel:
    pass


def event(entity, private=True, out=False, service=False):
    return SimpleNamespace(sender=entity, chat=entity, is_private=private, out=out, service=service)


def test_private_users_including_no_username_are_accepted():
    assert classify_event(event(User(id=1, username=None, bot=False))) == "private_user"


def test_unresolved_private_peer_user_is_accepted():
    unresolved = SimpleNamespace(is_private=True, peer_id=PeerUser(42), sender=None, chat=None)
    assert classify_event(unresolved) == "private_unresolved"


def test_bots_groups_megagroups_channels_outgoing_and_service_are_ignored():
    assert classify_event(event(User(id=1, username="bot", bot=True))) == "bot"
    assert classify_event(event(Chat(), private=False)) == "group"
    assert classify_event(event(Channel(), private=False)) == "channel"
    assert classify_event(event(Channel(), private=False)) == "channel"
    assert classify_event(event(User(id=5), out=True)) == "outgoing"
    assert classify_event(event(User(id=6), service=True)) == "service"


def test_peer_group_and_channel_are_rejected_before_unresolved_fallback():
    assert classify_event(SimpleNamespace(is_private=False, peer_id=PeerChat(2))) == "group"
    assert classify_event(SimpleNamespace(is_private=False, peer_id=PeerChannel(3))) == "channel"
