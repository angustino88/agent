from datetime import datetime
from dataclasses import dataclass

@dataclass(frozen=True)
class SessionInfo:
	booking_code	: str
	lab_computer    : str
	is_maintenance  : bool
	technical_user	: str
	remote_user		: str
	remote_user_displayname: str
	remote_ip		: str
	remote_computer	: str
	from_datetime	: datetime
	to_datetime		: datetime