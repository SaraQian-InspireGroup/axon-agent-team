import re
from decimal import Decimal
from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    text = str(value).strip()
    if not text or text in {"/", "-", "无"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_rate(value: Any) -> float | None:
    """Parse '81.2%' or numeric rate."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "/":
        return None
    text = text.replace("%", "").strip()
    return to_float(text)


def parse_days(value: Any) -> float | None:
    """Parse '21.5天' or numeric days."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "/":
        return None
    text = re.sub(r"天\s*$", "", text).strip()
    return to_float(text)


def round_qty(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(value, 5)
