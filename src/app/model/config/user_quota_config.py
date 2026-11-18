from pydantic import BaseModel
from src.utils.config import ConfigFileManager

USER_QUOTA_CONFIG_SCHEMA = {
    "users": {
        "type": "dict",
        "required": False,
        "schema": {
            # username: quota (float)
            # Example: "alice": 20.0
        }
    }
}

USER_QUOTA_CONFIG_DEFAULT = {
    "users": {}
}

class UserQuotaConfig(BaseModel):
    """Runtime, adjustable application feature flags."""

    file_manager:    ConfigFileManager = None
    default_quota:   float = 15.0

    class Config:
        arbitrary_types_allowed      = True
        validate_assignment          = True

    @classmethod
    def build(cls, file_manager: ConfigFileManager) -> "UserQuotaConfig":
        return cls(
            file_manager = file_manager,
        )

    @property
    def user_quotas(self) -> dict:
        return self.file_manager.get('users', USER_QUOTA_CONFIG_DEFAULT['users'])

    def get_quota_for_user(self, username: str) -> float:
        """Return the quota for a given user, falling back to default if not set."""
        return self.user_quotas.get(username, self.default_quota)