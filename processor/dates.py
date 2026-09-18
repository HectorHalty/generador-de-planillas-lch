from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

ARGENTINA = ZoneInfo("America/Argentina/Buenos_Aires")


def local_today() -> date:
    return datetime.now(ARGENTINA).date()


def next_saturday(today: date | None = None) -> date:
    """Upcoming Saturday in Argentina. If today is Saturday, keep today."""
    today = today or local_today()
    return today + timedelta(days=(5 - today.weekday()) % 7)


def format_sheet_date(value: date) -> str:
    return f"{value.day:02d} / {value.month:02d} / {value.year}"


def parse_iso_date(raw: str | None) -> date | None:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    return date.fromisoformat(text)
