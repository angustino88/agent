from pydantic import BaseModel
from src.utils.config import ConfigFileManager

APP_SETTINGS_SCHEMA = {
    "prod_server": {
        "type": "dict",
        "schema": {
            "frontend_url": {"type": "string", "required": True},
            "backend_url":  {"type": "string", "required": True}
        },
        "required": False
    },
    "safe_mode": {
        "type": "boolean",
        "required": False
    },
    "sharing_root_dir": {
         "type": "string",
         "required": False
    }
}

APP_SETTINGS_DEFAULT = {
    "prod_server": {
        "frontend_url": "https://labmango.com",
        "backend_url": "https://api.labmango.com"
    },
    "safe_mode": False,
    "sharing_root_dir": "C:\\sharing",
}

class AppSettings(BaseModel):
    """Runtime, adjustable application feature flags."""

    file_manager:         ConfigFileManager = None

    class Config:
        arbitrary_types_allowed      = True
        validate_assignment          = True

    @classmethod
    def build(cls, file_manager: ConfigFileManager) -> "AppSettings":
        return cls(
            file_manager = file_manager,
        )

    @property
    def prod_frontend_url(self) -> str:
        return self.file_manager.get('prod_server.frontend_url', APP_SETTINGS_DEFAULT['prod_server']['frontend_url'])

    @property
    def prod_backend_url(self) -> str:
        return self.file_manager.get('prod_server.backend_url', APP_SETTINGS_DEFAULT['prod_server']['backend_url'])

    @property
    def safe_mode(self) -> bool:
        return self.file_manager.get('safe_mode', APP_SETTINGS_DEFAULT['safe_mode'])

    @property
    def sharing_root_dir(self) -> str:
        return self.file_manager.get('sharing_root_dir', APP_SETTINGS_DEFAULT['sharing_root_dir'])

    def set_prod_frontend_url(self, url: str):
        self.file_manager.set('prod_server.frontend_url', url)
        self.file_manager.save()
    
    def set_prod_backend_url(self, url: str):
        self.file_manager.set('prod_server.backend_url', url)
        self.file_manager.save()
    
    def set_safe_mode(self, enabled: bool):
        self.file_manager.set('safe_mode', enabled)
        self.file_manager.save()
    
    def set_sharing_root_dir(self, dir: str):
        self.file_manager.set('sharing_root_dir', dir)
        self.file_manager.save()