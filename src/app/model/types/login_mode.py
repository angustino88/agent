from enum import Enum

class LoginMode(Enum):
	ADMIN   	    = 'admin'
	TEMP            = 'temp'
	ADMIN_BOOKING   = 'admin_booking'
	USER_BOOKING    = 'user_booking'