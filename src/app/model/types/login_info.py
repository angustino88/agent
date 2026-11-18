from dataclasses import dataclass

@dataclass(frozen=True)
class LoginInfo:
	username	     : str
	user_displayname : str
	technical_user   : str
	booking_code     : str
	login_action     : str
	login_mode	     : str