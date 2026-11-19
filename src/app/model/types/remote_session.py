from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class RemoteSession:
    """One login on this computer, from login until logout.

    ``booking_code`` is empty for a login without a booking (temporary or admin login).
    ``ends_at`` is the booking end, or the end of the temporary window.
    """

    computer_name: str
    technical_user: str
    remote_user: str
    remote_user_display_name: str
    remote_ip: str
    remote_computer: str
    booking_code: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    is_maintenance: bool = False

    @property
    def has_booking(self) -> bool:
        return bool(self.booking_code)
