import webbrowser
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController

class UserManualCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._logger = None
        self._app_config = None
        self._message_box = None

    def init(self):
        if self._initialized:
            return self
        self._logger = self.model.logging_model.system_logger
        self._app_config = self.model.config_model.app_config
        self._message_box = self.view.message_box
        self.view.main_window_view.ui.user_manual_action.triggered.connect(self.open_user_manual)
        self._initialized = True
        return self

    #====================================================================
    # Private helpers
    #====================================================================
    def _handle_exception(self, e):
        self._logger.exception(e)
        self._message_box.error(e)

    #====================================================================
    # Public / slot methods
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def open_user_manual(self):
        if not self._initialized:
            self.init()
        url = self._app_config.USER_MANUAL_URL
        webbrowser.open(url)