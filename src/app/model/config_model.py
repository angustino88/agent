import os
import json
from src.mvc.base_model import BaseModel
from src.app.model.config.app_config import AppConfig, AppConfigDynamic
from src.app.model.config.app_settings import AppSettings
from src.app.model.config.credential_config import CredentialConfig
from src.app.model.config.user_quota_config import UserQuotaConfig
from src.app.model.config.app_config_manager import AppConfigFileManager
from src.app.model.config.app_settings_manager import AppSettingsFileManager
from src.app.model.config.user_quota_config_manager import UserQuotaConfigFileManager

class ConfigModel(BaseModel):
    def __init__(self):
        super().__init__()
        self._app_config = AppConfig()
        self._credential_config = None
        self._app_config_dynamic = None
        self._app_settings = None
        self._user_quota_config = None

    def init(self):
        self._credential_config = CredentialConfig()

        # Load app config with fallback to default
        app_config_mgr = AppConfigFileManager(self._app_config)
        try:
            app_config_mgr.load()
        except:
            app_config_mgr.reset_to_default()
            app_config_mgr.load()
        self._app_config_dynamic = AppConfigDynamic.build(app_config_mgr)

        # Load app settings with fallback to default
        settings_mgr = AppSettingsFileManager(self._app_config)
        try:
            settings_mgr.load()
        except:
            settings_mgr.reset_to_default()
            settings_mgr.load()
        self._app_settings = AppSettings.build(settings_mgr)

        # Load user quota config with fallback to default
        user_quota_mgr = UserQuotaConfigFileManager(self._app_config)
        try:
            user_quota_mgr.load()
        except:
            user_quota_mgr.reset_to_default()
            user_quota_mgr.load()
        self._user_quota_config = UserQuotaConfig.build(user_quota_mgr)

    @property
    def app_config(self):
        return self._app_config

    @property
    def app_config_dynamic(self):
        return self._app_config_dynamic

    @property
    def app_settings(self):
        return self._app_settings

    @property
    def credential_config(self):
        return self._credential_config

    @property
    def user_quota_config(self):
        return self._user_quota_config    
