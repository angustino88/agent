from enum import Enum

class LabStatus(Enum):
	FREE         = 'free'
	OFFLINE      = 'offline'
	ACTIVE       = 'active'
	INACTIVE     = 'inactive'
	MAINTAINING  = 'maintaining'