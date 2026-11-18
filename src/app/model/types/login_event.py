from enum import Enum

class LoginEvent(Enum):
    REMOTE_LOGIN  = 'remote_login'
    REMOTE_LOGOUT = 'remote_logout'
    SCREEN_LOGIN  = 'screen_login'
    SCREEN_LOGOUT = 'screen_logout'