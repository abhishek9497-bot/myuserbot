from rule_engine import find_matching_rule, normalize_keywords, normalize_text, rule_matches


def rule(**kwargs):
    return {"id": 1, "enabled": True, "keywords_list": ["qr", "payment kaise karu"], "match_type": "ANY_KEYWORD", "priority": 1, **kwargs}


def test_normalization_and_keyword_types():
    assert normalize_text("  QR!!!   BHEJO ") == "qr bhejo"
    assert normalize_keywords("qr, payment\nscanner") == ["qr", "payment", "scanner"]
    assert rule_matches("qr", rule(match_type="EXACT", keywords_list=["qr"]))
    assert rule_matches("Please send qr code", rule(match_type="CONTAINS", keywords_list=["qr code"]))
    assert rule_matches("PAYMENT KAISE KARU", rule())


def test_priority_and_disabled_rules():
    rules = [rule(id=1, priority=10, keywords_list=["pay"]), rule(id=2, priority=100, keywords_list=["qr"]), rule(id=3, priority=200, enabled=False, keywords_list=["qr"])]
    assert find_matching_rule("qr pay", rules)["id"] == 2
    assert find_matching_rule("hello", rules) is None
