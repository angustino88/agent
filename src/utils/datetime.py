"""Date/time utility functions."""
from __future__ import annotations

from datetime import datetime, timezone
from tzlocal import get_localzone


def iso_datetime(dt: datetime | None, add_timezone: bool = True) -> str:
    """Format a datetime as an ISO 8601 string.

    When *add_timezone* is ``True`` (default), the local timezone is attached
    to naive datetimes.  When ``False``, any timezone info is stripped.
    """
    if dt is None:
        return ""
    if add_timezone:
        local_tz = get_localzone()
        if dt.tzinfo is None:
            dt = local_tz.localize(dt) if hasattr(local_tz, 'localize') else dt.replace(tzinfo=local_tz)
        return dt.isoformat(timespec="seconds")
    else:
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.isoformat(timespec="seconds")


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(tz=timezone.utc)


def local_now() -> datetime:
    """Return the current local time as a timezone-aware datetime."""
    return datetime.now(tz=get_localzone())


def elapsed_str(start: datetime, end: datetime | None = None) -> str:
    """Human-readable elapsed time between *start* and *end* (or now).

    Examples: ``'2.4s'``, ``'1m 23s'``, ``'2h 5m'``.
    """
    end = end or datetime.now(tz=start.tzinfo)
    delta = end - start
    total = int(delta.total_seconds())
    if total < 60:
        return f"{delta.total_seconds():.1f}s"
    minutes, seconds = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def timestamp_ms() -> int:
    """Return the current UNIX timestamp in milliseconds."""
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def parse_iso(text: str) -> datetime:
    """Parse an ISO 8601 string into a datetime object."""
    return datetime.fromisoformat(text)