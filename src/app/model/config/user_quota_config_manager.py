from __future__ import annotations
import os
from src.utils.config import JsonParserUtil, ConfigFileManager, ConfigDefault, ConfigValidator
from src.app.model.config.user_quota_config import USER_QUOTA_CONFIG_SCHEMA, USER_QUOTA_CONFIG_DEFAULT

FILE_INFO_SCHEMA = {
    'file_info': {
        'type': 'dict',
        'schema': {
            'file_version': {'type': 'string'},
            'file_name': {'type': 'string'},
        }
    }
}

FILE_VERSION = '1.0.0'

class UserQuotaConfigFileManager(ConfigFileManager):
    """
    Manager for user configuration file.
    Handles loading, validation, and schema management for app setting.
    """
    def __init__(self, app_config):
        """
        :param app_config: AppConfig instance with USER_CONFIG_FILE attribute.
        """
        parser = JsonParserUtil
        version_path = 'file_info.file_version'
        file_name = os.path.basename(app_config.USER_QUOTA_CONFIG_FILE)
        file_header = {
            'file_info': {
                'file_version': FILE_VERSION,
                'file_name': file_name
            }
        }

        default = ConfigDefault(version_path=version_path)
        default.set_header(file_header)
        default.add_section(USER_QUOTA_CONFIG_DEFAULT)

        v = ConfigValidator(require_all=False)
        v.add_schema(FILE_INFO_SCHEMA)
        v.add_schema(USER_QUOTA_CONFIG_SCHEMA)
        validator = v.build()

        super().__init__(
            file_path=app_config.USER_QUOTA_CONFIG_FILE,
            version_path=version_path,
            default=default.content,
            parser=parser,
            validator=validator
        )
