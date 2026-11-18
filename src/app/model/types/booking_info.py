from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Optional

from .booking_status import BookingStatus


@dataclass(frozen=True)
class BookingInfo:
	"""A booking as the backend's agent API exposes it (``/agent/bookings/actions/*``).

	The agent API identifies a booking by its code only; it no longer returns the numeric id,
	project, computer or approval status. The backend checks approval, bench/computer and the
	time window itself, so a returned booking is already eligible for this computer.
	"""
	booking_code	 : str
	booking_creator  : str
	from_datetime 	 : Optional[datetime]
	to_datetime 	 : Optional[datetime]
	booking_status 	 : BookingStatus = BookingStatus.AVAILABLE
	booking_project  : str = ""
