import webbrowser
from pathlib import Path
from src.mvc.slot_guard import slot_guard
from src.mvc.base_controller import BaseController

class LogCheckCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        """
        Initializes class instance
        """
        super().__init__()
        self._logger = None
        self._message_box = None

    def init(self):
        """
        Additional initialization after the class instance has been initialized
        """
        self._logger = self.model.logging_model.system_logger
        self._message_box = self.view.message_box
        self.view.main_window_view.ui.log_check_btn.clicked.connect(self.export_and_open_log_dir)
        return self

    #====================================================================
    # Private methods
    #====================================================================
    def _handle_exception(self, e):
        """Shows error message to user."""
        self._logger.exception(e)
        if self._message_box:
            self._message_box.error(e)

    def _export_logs(self) -> Path:
        """Export session & status logs; return directory Path."""
        self.model.logging_model.export_session_log()
        self.model.logging_model.export_status_log()
        return Path(self.model.config_model.app_config.LOG_DIR)

    def _open_dir(self, path: Path):
        try:
            webbrowser.open(str(path.resolve()))
        except Exception as e:
            raise RuntimeError(f"Failed to open log directory: {e}") from e

    #====================================================================
    # Public / slots
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def export_and_open_log_dir(self):
        path = self._export_logs()
        self._open_dir(path)
        if self._message_box:
            self._message_box.info(f"Logs exported to:\n{path}")

    @slot_guard(on_exception=_handle_exception)
    def export_logs_only(self):
        path = self._export_logs()
        if self._message_box:
            self._message_box.info(f"Logs exported (directory not opened):\n{path}")

    @slot_guard(on_exception=_handle_exception)
    def open_log_dir(self):
        path = Path(self.model.config_model.app_config.LOG_DIR)
        self._open_dir(path)