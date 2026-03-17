"""
Date/time parsing and formatting utilities.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import dateparser

from config.settings import DEFAULT_TIMEZONE


def parse_datetime(
    text: str,
    reference_tz: str | None = None,
) -> datetime | None:
    """
    Parse a natural-language date/time string into a timezone-aware datetime.

    Args:
        text: Natural language like "tomorrow at 1pm", "Friday 3pm", etc.
        reference_tz: IANA timezone string. Defaults to America/Chicago.

    Returns:
        Timezone-aware datetime, or None if parsing fails.
    """
    tz_name = reference_tz or DEFAULT_TIMEZONE
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    settings = {
        "TIMEZONE": tz_name,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": now.replace(tzinfo=None),
        "PREFER_DATES_FROM": "future",
    }

    parsed = dateparser.parse(text, settings=settings)
    if parsed is None:
        return None

    # Ensure it carries the right timezone
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)

    return parsed


def get_time_range(
    range_text: str,
    reference_tz: str | None = None,
) -> tuple[datetime, datetime] | None:
    """
    Convert a range expression like "next 2 days" into (start, end).

    Args:
        range_text: Natural language range like "next 3 days", "this week".
        reference_tz: Optional timezone override.

    Returns:
        Tuple of (start, end) as timezone-aware datetimes, or None.
    """
    tz_name = reference_tz or DEFAULT_TIMEZONE
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    # Try to extract a number-of-days pattern
    lower = range_text.lower().strip()

    # Handle "today"
    if "today" in lower:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end

    # Handle "tomorrow"
    if "tomorrow" in lower:
        start = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        end = start + timedelta(days=1)
        return start, end

    # Handle "next N days"
    import re
    match = re.search(r"(?:next|coming)\s+(\d+)\s+days?", lower)
    if match:
        days = int(match.group(1))
        start = now
        end = now + timedelta(days=days)
        return start, end

    # Handle "this week"
    if "this week" in lower:
        start = now
        days_until_sunday = 6 - now.weekday()
        end = (now + timedelta(days=days_until_sunday + 1)).replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        return start, end

    # Fallback: try parsing as a single date → make it a full-day range
    parsed = parse_datetime(range_text, reference_tz)
    if parsed:
        start = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        return start, end

    return None


def format_datetime(dt: datetime) -> str:
    """
    Format a datetime into a friendly human-readable string.
    Examples: "Monday, March 17 at 1:00 PM"
    """
    return dt.strftime("%A, %B %-d at %-I:%M %p")


def format_date(dt: datetime) -> str:
    """Short date format, e.g. 'March 17'."""
    return dt.strftime("%B %-d")


def format_time(dt: datetime) -> str:
    """Time only, e.g. '1:00 PM'."""
    return dt.strftime("%-I:%M %p")


def now_in_tz(tz_name: str | None = None) -> datetime:
    """Return current time in the given (or default) timezone."""
    tz = ZoneInfo(tz_name or DEFAULT_TIMEZONE)
    return datetime.now(tz)
