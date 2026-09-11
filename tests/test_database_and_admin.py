from database import Database
from admin_app import create_app


def values(**overrides):
    data = {"name": "Payment QR", "keywords_list": ["qr", "payment"], "match_type": "ANY_KEYWORD", "reply_text": "Pay", "send_text": True, "send_image": False, "enabled": True, "priority": 100, "cooldown_seconds": 300}
    data.update(overrides)
    return data


def test_cooldowns_are_per_user_rule_and_persist(tmp_path):
    db = Database(tmp_path / "test.db")
    rule_id = db.save_rule(values())
    assert db.cooldown_remaining(10, rule_id, 300) == 0
    db.update_cooldown(10, rule_id)
    assert db.cooldown_remaining(10, rule_id, 300) > 0
    assert db.cooldown_remaining(11, rule_id, 300) == 0
    reopened = Database(tmp_path / "test.db")
    assert reopened.cooldown_remaining(10, rule_id, 300) > 0


def test_duplicate_event_and_admin_direct_dashboard(tmp_path):
    db = Database(tmp_path / "test.db")
    db.log_message(5, None, "qr", 1, True, False, 100)
    assert db.is_duplicate(5, 100)
    assert not db.is_duplicate(5, 101)
    client = create_app(db).test_client()
    assert client.get("/").status_code == 200
    assert b"Dashboard" in client.get("/").data


def test_admin_rule_lifecycle(tmp_path):
    db = Database(tmp_path / "test.db")
    client = create_app(db).test_client()
    response = client.post("/rules/new", data={"name": "Price", "keywords": "price, rate", "reply_text": "10", "priority": "5", "cooldown_number": "2", "cooldown_unit": "minutes", "send_text": "on", "enabled": "on"}, follow_redirects=True)
    assert response.status_code == 200
    saved = db.list_rules()[0]
    assert saved["cooldown_seconds"] == 120
    client.post(f"/rules/{saved['id']}/edit", data={"name": "New Price", "keywords": "cost", "cooldown_number": "0", "cooldown_unit": "seconds", "enabled": "on"})
    assert db.get_rule(saved["id"])["name"] == "New Price"
    client.post(f"/rules/{saved['id']}/delete")
    assert db.get_rule(saved["id"]) is None
