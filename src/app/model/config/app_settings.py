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
    },
    "tls": {
        "type": "dict",
        "schema": {
            "verify":    {"type": "boolean", "required": False},
            "ca_bundle": {"type": "string",  "required": False}
        },
        "required": False
    },
    "active_directory": {
        "type": "dict",
        "schema": {
            "default_domain":  {"type": "string", "required": False},
            "search_bases":    {"type": "list", "schema": {"type": "string"}, "required": False},
            "fallback_admins": {"type": "list", "schema": {"type": "string"}, "required": False}
        },
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
    # TLS: off until the gateway and backend serve valid certificates. Set verify: true (and
    # ca_bundle for an internal CA) to check certificates and stop the gateway's HTTP fallback.
    "tls": {
        "verify": False,
        "ca_bundle": "",
    },
    # Active Directory lookup for login. Replace the placeholders with the real forest.
    "active_directory": {
        "default_domain": "DC=,DC=com",
        "search_bases": [
            "DC=apac,DC=Company,DC=com",
            "DC=de,DC=Company,DC=com",
            "DC=emea,DC=Company,DC=com",
        ],
        "fallback_admins": ["adminlab"],
    },
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

    @property
    def tls_verify_enabled(self) -> bool:
        return bool(self.file_manager.get('tls.verify', APP_SETTINGS_DEFAULT['tls']['verify']))

    @property
    def tls_verify(self) -> bool | str:
        """Value for ``requests``' ``verify``: False, True, or the CA bundle path."""
        if not self.tls_verify_enabled:
            return False
        ca_bundle = self.file_manager.get('tls.ca_bundle', APP_SETTINGS_DEFAULT['tls']['ca_bundle'])
        return ca_bundle or True

    @property
    def ad_default_domain(self) -> str:
        return self.file_manager.get('active_directory.default_domain', APP_SETTINGS_DEFAULT['active_directory']['default_domain'])

    @property
    def ad_search_bases(self) -> list[str]:
        return list(self.file_manager.get('active_directory.search_bases', APP_SETTINGS_DEFAULT['active_directory']['search_bases']) or [])

    @property
    def ad_fallback_admins(self) -> set[str]:
        admins = self.file_manager.get('active_directory.fallback_admins', APP_SETTINGS_DEFAULT['active_directory']['fallback_admins'])
        return {str(a).lower() for a in (admins or [])}

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