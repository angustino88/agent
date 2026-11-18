from enum import Enum


class ActivityStatus(str, Enum):
    """Live activity of this computer, as the backend's ``ComputingActivityStatus``."""

    OFFLINE = "offline"
    FREE = "free"
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTAINING = "maintaining"
