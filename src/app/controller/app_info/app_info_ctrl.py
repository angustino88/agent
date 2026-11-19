import sys
from src.mvc.slot_guard import slot_guard
from src.mvc.base_controller import BaseController

class AppInfoCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._logger = None
        self._app_config = None
        self._app_config_dynamic = None
        self._app_settings = None
        self._message_box = None
        self._app_info_view = None

    def init(self):
        if self._initialized:
            return self
        self._logger = self.model.logging_model.system_logger
        self._app_config = self.model.config_model.app_config
        self._app_config_dynamic = self.model.config_model.app_config_dynamic
        self._app_settings = self.model.config_model.app_settings
        self._message_box = self.view.message_box
        self._app_info_view = self.view.app_info_view
        self.view.main_window_view.ui.about_app_action.triggered.connect(self.show_dialog)
        self._log_startup_info()
        self._initialized = True
        return self

    #====================================================================
    # Private helpers
    #====================================================================
    def _handle_exception(self, e):
        self._logger.exception(e)
        self._message_box.error(e, parent=self._settings_view)

    def _log_startup_info(self):
        self._logger.info("=" * 70)
        self._logger.info("[C] Application Startup")
        self._logger.info("-" * 70)
        self._logger.info(f"App Name        : {self._app_config.APP_NAME}")
        self._logger.info(f"Version         : {self._app_config.APP_VERSION}")
        self._logger.info(f"Git Commit      : {self._app_config.BUILD_COMMIT}")
        self._logger.info(f"Git Branch      : {self._app_config.BUILD_BRANCH}")
        self._logger.info(f"Build Date      : {self._app_config.BUILD_DATE}")
        self._logger.info(f"Build Mode      : {'DEVELOPMENT' if self._app_config.IS_DEVELOPMENT else 'PRODUCTION'}")
        self._logger.info(f"Debug Mode      : {'ON' if self._app_config_dynamic.app_debug_enabled else 'OFF'}")
        self._logger.info(f"App Update      : {'YES' if self._app_config.APP_UPDATE_ENABLED else 'NO'}")
        self._logger.info(f"System Tray     : {'ENABLED' if self._app_config.SYS_TRAY_ENABLED else 'DISABLED'}")
        self._logger.info(f"Executable Path : {sys.executable}")
        self._logger.info("=" * 70)

    #====================================================================
    # Public / slot methods
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        if not self._initialized:
            self.init()
        self._app_info_view.show()