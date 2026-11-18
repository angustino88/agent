from enum import Enum

class BookingStatus(Enum):
	UNKNOWN       = 'unknown'
	AVAILABLE     = 'available'
	IN_PROGRESS   = 'in-progress'
	DONE          = 'done'
	CANCEL        = 'cancel'
	EXPIRED       = 'expired'