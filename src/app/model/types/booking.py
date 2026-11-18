from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


BOOKING_CODE_PREFIX = "BOOKING-"  # backend-generated codes: "BOOKING-" + 14 hex characters


def parse_booking_code(text: str) -> Optional[str]:
    """The booking code typed on the login screen; ``None`` when the text is a username.

    Only the prefix is normalised: the backend matches codes exactly, so the rest is kept as typed.
    """
    text = (text or "").strip()
    if not text.upper().startswith(BOOKING_CODE_PREFIX) or len(text) == len(BOOKING_CODE_PREFIX):
        return None
    return BOOKING_CODE_PREFIX + text[len(BOOKING_CODE_PREFIX) :]


class BookingStatus(str, Enum):
    """Bench booking status, as the backend's ``BookingStatus``."""

    RESERVED = "reserved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(frozen=True)
class Booking:
    """A bench booking as the agent API returns it (``/agent/bookings/actions/*``).

    Identified by its code only. The backend checks approval, the computer's bench and the time
    window, so a booking returned here is eligible on this computer. Times are naive local time.
    """

    booking_code: str
    booked_for: str
    starts_at: Optional[datetime]
    ends_at: Optional[datetime]
    status: BookingStatus = BookingStatus.RESERVED


class BookingAction(str, Enum):
    """What the agent can do to a running booking; values are the labels shown to the user."""

    EXTEND = "Extend booking"
    COMPLETE = "End booking now"
