from datetime import datetime
from dataclasses import dataclass
from .booking_status import BookingStatus
from .approval_status import ApprovalStatus

@dataclass(frozen=True)
class BookingInfo:
	lab_id			 : int
	booking_id		 : int
	booking_code	 : str
	booking_creator  : str
	booking_project  : str
	booking_computer : str
	booking_status 	 : BookingStatus
	from_datetime 	 : datetime
	to_datetime 	 : datetime
	approval_status  : ApprovalStatus
