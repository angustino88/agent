from dataclasses import dataclass

@dataclass(frozen=True)
class StorageQuota:
	username: str
	user_displayname: str
	used: float  # in GB
	quota: float  # in GB