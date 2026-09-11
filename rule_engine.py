import re
import unicodedata
from typing import Any


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower().strip()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def normalize_keywords(value: str | list[str]) -> list[str]:
    parts = value if isinstance(value, list) else re.split(r"[,\n]", value)
    return [normalized for part in parts if (normalized := normalize_text(part))]


def rule_matches(message: str, rule: dict[str, Any]) -> bool:
    text = normalize_text(message)
    keywords = [normalize_text(keyword) for keyword in rule.get("keywords_list", rule.get("keywords", []))]
    keywords = [keyword for keyword in keywords if keyword]
    match_type = rule.get("match_type", "ANY_KEYWORD").upper()
    if not text or not keywords:
        return False
    if match_type == "EXACT":
        return any(text == keyword for keyword in keywords)
    if match_type == "CONTAINS":
        return any(keyword in text for keyword in keywords)
    return any(keyword in text.split() or keyword in text for keyword in keywords)


def find_matching_rule(message: str, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    for rule in sorted((rule for rule in rules if rule.get("enabled", True)),
                       key=lambda item: (-int(item.get("priority", 0)), int(item.get("id", 0)))):
        if rule_matches(message, rule):
            return rule
    return None
