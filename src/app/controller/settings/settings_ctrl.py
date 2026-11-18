import os
import webbrowser
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController

class SettingsCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._logger = None
        self._app_config_dynamic = None
        self._app_settings = None
        self._message_box = None
        self._settings_view = None

    def init(self):
        if self._initialized:
            return self
        self._logger = self.model.logging_model.system_logger
        self._app_config = self.model.config_model.app_config
        self._app_config_dynamic = self.model.config_model.app_config_dynamic
        self._app_settings = self.model.config_model.app_settings
        self._message_box = self.view.message_box
        self._settings_view = self.view.settings_view
        self._settings_view.ui.user_quota_btn.clicked.connect(self.open_user_quota_config)
        self._settings_view.ui.save_btn.clicked.connect(self.save)
        self._settings_view.ui.cancel_btn.clicked.connect(self.cancel)
        self.view.main_window_view.ui.settings_btn.clicked.connect(self.show_dialog)
        self._initialized = True
        return self

    #====================================================================
    # Private helpers
    #====================================================================
    def _handle_exception(self, e):
        self._logger.exception(e)
        self._message_box.error(e, parent=self._settings_view)

    def _load_all(self):
        self._settings_view.set_app_debug_enabled(self._app_config_dynamic.app_debug_enabled)
        self._settings_view.set_sharing_dir(self._app_settings.sharing_root_dir)

    def _save_all(self):
        debug_enabled = self._settings_view.get_app_debug_enabled()
        sharing_dir = self._settings_view.get_sharing_dir()
        self._app_config_dynamic.set_app_debug_enabled(debug_enabled)
        self._app_settings.set_sharing_root_dir(sharing_dir)

    #====================================================================
    # Public / slot methods
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        if not self._initialized:
            self.init()
        self._load_all()
        self._settings_view.exec()
    
    @slot_guard(on_exception=_handle_exception)
    def open_user_quota_config(self):
        quota_file = self._app_config.USER_QUOTA_CONFIG_FILE
        if quota_file and os.path.exists(quota_file):
            webbrowser.open(f'file:///{os.path.abspath(quota_file)}')
        else:
            self._message_box.error("User quota config file not found.", parent=self._settings_view)

    @slot_guard(on_exception=_handle_exception)
    def save(self):
        self._save_all()
        self._message_box.info("Configuration saved.", parent=self._settings_view)
        self._settings_view.accept()
    
    @slot_guard(on_exception=_handle_exception)
    def cancel(self):
        self._settings_view.close()