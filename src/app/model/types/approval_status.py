from enum import Enum

class ApprovalStatus(Enum):
	APPROVED     = 'approved'
	PENDING      = 'pending'
	REJECTED     = 'rejected'