from pydantic import BaseModel

from src.utils.config import ConfigFileManager

APP_SETTINGS_SCHEMA = {
    "prod_server": {
        "type": "dict",
        "schema": {
            "frontend_url": {"type": "string", "required": True},
            # No longer used: the backend URL comes from the enrolled agent identity.
            # Kept optional so settings files written by older versions stay valid.
            "backend_url": {"type": "string", "required": False},
        },
        "required": False,
    },
    "safe_mode": {"type": "boolean", "required": False},
    "sharing_root_dir": {"type": "string", "required": False},
    "tls": {
        "type": "dict",
        "schema": {
            "verify": {"type": "boolean", "required": False},
            "ca_bundle": {"type": "string", "required": False},
        },
        "required": False,
    },
    "active_directory": {
        "type": "dict",
        "schema": {
            "default_domain": {"type": "string", "required": False},
            "search_bases": {"type": "list", "schema": {"type": "string"}, "required": False},
        },
        "required": False,
    },
    "login": {
        "type": "dict",
        "schema": {
            "admin_usernames": {"type": "list", "schema": {"type": "string"}, "required": False},
        },
        "required": False,
    },
    "licenses": {
        "type": "dict",
        "schema": {
            "warn_days": {"type": "integer", "min": 1, "required": False},
            "vector_license_client": {"type": "string", "required": False},
            "builtin_checks": {"type": "list", "schema": {"type": "string"}, "required": False},
            "allowed_roots": {"type": "list", "schema": {"type": "string"}, "required": False},
            "trusted_paths": {"type": "list", "schema": {"type": "string"}, "required": False},
        },
        "required": False,
    },
}

APP_SETTINGS_DEFAULT = {
    "prod_server": {
        "frontend_url": "https://labmango.com",
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
    },
    # Users who log in as administrators (maintenance) without a booking.
    "login": {
        "admin_usernames": ["adminlab"],
    },
    # License checks. The web app configures them per computer; these local settings only bound
    # what the agent may run, and choose built-in checks while the backend serves none.
    "licenses": {
        "warn_days": 30,
        "vector_license_client": "C:\\Program Files\\Vector License Client\\Vector.LicenseClient.exe",
        "builtin_checks": ["vector-license-client"],
        "allowed_roots": [],  # added to Program Files, Program Files (x86) and ProgramData
        "trusted_paths": [],  # tools allowed even when the backend connection is not TLS-verified
    },
}


class AppSettings(BaseModel):
    """Per-user settings file (``app_settings.yml``), editable at runtime."""

    file_manager: ConfigFileManager = None

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True

    @classmethod
    def build(cls, file_manager: ConfigFileManager) -> "AppSettings":
        return cls(file_manager=file_manager)

    def _get(self, key: str):
        section, _, name = key.partition(".")
        default = APP_SETTINGS_DEFAULT[section][name] if name else APP_SETTINGS_DEFAULT[section]
        return self.file_manager.get(key, default)

    def _set(self, key: str, value) -> None:
        self.file_manager.set(key, value)
        self.file_manager.save()

    # ---- Lab Mango web app ------------------------------------------------

    @property
    def frontend_url(self) -> str:
        return self._get("prod_server.frontend_url")

    def set_frontend_url(self, url: str) -> None:
        self._set("prod_server.frontend_url", url)

    # ---- Behaviour ----------------------------------------------------------

    @property
    def safe_mode(self) -> bool:
        return bool(self._get("safe_mode"))

    def set_safe_mode(self, enabled: bool) -> None:
        self._set("safe_mode", enabled)

    @property
    def sharing_root_dir(self) -> str:
        return self._get("sharing_root_dir")

    def set_sharing_root_dir(self, path: str) -> None:
        self._set("sharing_root_dir", path)

    # ---- TLS ----------------------------------------------------------------

    @property
    def tls_verify_enabled(self) -> bool:
        return bool(self._get("tls.verify"))

    @property
    def tls_verify(self) -> bool | str:
        """Value for ``requests``' ``verify``: False, True, or the CA bundle path."""
        if not self.tls_verify_enabled:
            return False
        return self._get("tls.ca_bundle") or True

    # ---- Login --------------------------------------------------------------

    @property
    def ad_default_domain(self) -> str:
        return self._get("active_directory.default_domain")

    @property
    def ad_search_bases(self) -> list[str]:
        return list(self._get("active_directory.search_bases") or [])

    @property
    def admin_usernames(self) -> set[str]:
        return {str(name).lower() for name in (self._get("login.admin_usernames") or [])}

    # ---- Licenses -----------------------------------------------------------

    @property
    def license_warn_days(self) -> int:
        return int(self._get("licenses.warn_days") or 30)

    @property
    def vector_license_client(self) -> str:
        return self._get("licenses.vector_license_client") or ""

    @property
    def license_builtin_checks(self) -> list[str]:
        return list(self._get("licenses.builtin_checks") or [])

    @property
    def license_allowed_roots(self) -> list[str]:
        return list(self._get("licenses.allowed_roots") or [])

    @property
    def license_trusted_paths(self) -> list[str]:
        return list(self._get("licenses.trusted_paths") or [])
