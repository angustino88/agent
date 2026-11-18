from enum import Enum

class AppUpdateState(Enum):
    UNKNOWN      = 0
    NOT_READY    = 1
    READY        = 2
    IN_PROGRESS  = 3
    COMPLETED    = 4
    ERROR        = 5
