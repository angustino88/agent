import os
import sys
from pathlib import Path
from pydantic import BaseModel

from src.utils.path import PathUtil
from src.pkgman.version import Version
from src.utils.config import ConfigFileManager
from src.mvc.config import RuntimeDir, BundledPath, LogFile, ConfigFile, ServiceUrl
from prj.config.version.version_config import VersionConfig
from prj.config.builder.build_config import BuildConfig

def _resolve_repo_root() -> Path:
    env_root = os.environ.get("LABMANGO_ROOT")
    if env_root:
        return Path(env_root)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[3]

def get_app_root() -> Path:
    return _resolve_repo_root()

def get_bundle_dir() -> Path:
    """Return the directory containing bundled read-only resources.

    PyInstaller 6.x (one-dir): bundled data sits in _internal/ (sys._MEIPASS),
    which is one level below the exe.  In development mode this is the project root.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return _resolve_repo_root()

try:
    from prj.config.version.build_info import BuildInfo
except ImportError:
    class BuildInfo:
        GIT_COMMIT: str = 'dev'
        GIT_BRANCH: str = 'dev'
        BUILD_DATE: str = 'dev'

_LOCALAPPDATA: str = os.getenv('LOCALAPPDATA', '')
_PROGRAMDATA: str = os.getenv('PROGRAMDATA', r'C:\ProgramData')

def is_development_mode() -> bool:
    return not getattr(sys, "frozen", False)

APP_CONFIG_SCHEMA = {
    "app_debug": {
        "type": "dict",
        "schema": {
            "enabled": {"type": "boolean", "required": True}
        },
        "required": True
    }
}

APP_CONFIG_DEFAULT = {
    "app_debug":  {"enabled": False}
}

class AppConfigDynamic(BaseModel):
    """Dynamic, user-editable application config loaded from file."""

    file_manager:         ConfigFileManager

    class Config:
        arbitrary_types_allowed      = True
        validate_assignment          = True

    @classmethod
    def build(cls, file_manager: ConfigFileManager) -> "AppConfigDynamic":
        return cls(
            file_manager = file_manager
        )

    @property
    def app_debug_enabled(self) -> bool:
        return self.file_manager.get('app_debug.enabled', APP_CONFIG_DEFAULT['app_debug']['enabled'])

    def set_app_debug_enabled(self, enabled: bool):
        self.file_manager.set('app_debug.enabled', enabled)
        self.file_manager.save()

class AppConfig(BaseModel):
    # Core paths
    ROOT_DIR:           str         = get_app_root()
    BUNDLE_DIR:         BundledPath = get_bundle_dir()
    APP_NAME:           str = BuildConfig.APP_NAME
    APP_DISPLAY_NAME:   str = BuildConfig.APP_DISPLAY_NAME
    APP_VERSION:        Version = Version(VersionConfig.APP_VERSION)
    BUILD_COMMIT:       str = BuildInfo.GIT_COMMIT
    BUILD_BRANCH:       str = BuildInfo.GIT_BRANCH
    BUILD_DATE:         str = BuildInfo.BUILD_DATE
    APP_ICON:           BundledPath = PathUtil.join(BUNDLE_DIR, BuildConfig.ICON_PATH)
    ASSET_DIR:          BundledPath = PathUtil.join(BUNDLE_DIR, 'assets')

    # Local app data
    LOCAL_APP_DIR:      RuntimeDir = PathUtil.join(_LOCALAPPDATA, APP_NAME)

    # Shared machine-wide app data (all Windows users)
    SHARED_APP_DIR:      RuntimeDir = PathUtil.join(_PROGRAMDATA, APP_NAME)
    SHARED_INFO_DIR:     RuntimeDir = PathUtil.join(SHARED_APP_DIR, 'info')
    APP_CONFIG_FILE:     ConfigFile = PathUtil.join(SHARED_INFO_DIR, 'app_config.yml')

    # Logs
    LOG_DIR:            RuntimeDir = PathUtil.join(LOCAL_APP_DIR, 'logs')
    SYS_LOG_FILE:       LogFile = PathUtil.join(LOG_DIR, 'sys.log')
    SESSION_LOG_FILE:   LogFile = PathUtil.join(LOG_DIR, 'session_log.xlsx')
    STATUS_LOG_FILE:    LogFile = PathUtil.join(LOG_DIR, 'status_log.xlsx')
    LOG_DB_FILE:        LogFile = PathUtil.join(LOG_DIR, 'logs.db')

    # Settings & Info directories
    SETTINGS_DIR:              RuntimeDir = PathUtil.join(LOCAL_APP_DIR, 'settings')
    INFO_DIR:                  RuntimeDir = PathUtil.join(LOCAL_APP_DIR, 'info')
    APP_SETTINGS_FILE:         ConfigFile = PathUtil.join(SETTINGS_DIR, 'app_settings.yml')
    USER_STORAGE_INFO_FILE:    ConfigFile = PathUtil.join(SHARED_INFO_DIR, 'user_storage.json')
    USER_QUOTA_CONFIG_FILE:    ConfigFile = PathUtil.join(SHARED_INFO_DIR, 'user_quota_config.json')

    # Agent identity and backend delivery state (machine-wide; shared with the command line)
    AGENT_DIR:                 RuntimeDir = PathUtil.join(SHARED_APP_DIR, 'agent')
    SESSION_LOG_OUTBOX_FILE:   ConfigFile = PathUtil.join(SHARED_APP_DIR, 'agent', 'session_log_outbox.json')

    USER_MANUAL_URL:        str = "https://labmango.readthedocs.io/en/latest/"

    SERVICE_GATEWAY_URL:    ServiceUrl = "http://localhost:8000"
    IS_DEVELOPMENT:         bool = is_development_mode()
    APP_UPDATE_ENABLED:     bool = True
    SYS_TRAY_ENABLED:       bool = True
    
    class Config:
        frozen = True
        arbitrary_types_allowed = True