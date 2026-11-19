import qdarktheme
from winotify import Notification
from src.mvc.base_view import BaseMainView
from src.mvc.console import MessageBoxConsole
from src.app.view.main_window_view import MainWindowView
from src.app.view.login_view import LoginView
from src.app.view.temp_login_view import TempLoginView
from src.app.view.settings_view import SettingsView
from src.app.view.server_config_view import ServerConfigView
from src.app.view.session_info_view import SessionInfoView
from src.app.view.booking_update_view import BookingUpdateView
from src.app.view.health_info_view import HealthInfoView
from src.app.view.device_scan_view import DeviceScanView
from src.app.view.app_update_view import AppUpdateView
from src.app.view.app_info_view import AppInfoView


class MainView(BaseMainView):
    def __init__(self, model, bus, max_workers: int = 4):
        super().__init__(model, bus, max_workers)

    def _setup(self):
        qdarktheme.setup_theme('light')
        self.app_info_view       = self._make(AppInfoView)
        self.app_update_view     = self._make(AppUpdateView)
        self.main_window_view    = self._make(MainWindowView)
        self.login_view          = self._make(LoginView)
        self.temp_login_view     = self._make(TempLoginView)
        self.settings_view       = self._make(SettingsView)
        self.server_config_view  = self._make(ServerConfigView)
        self.session_info_view   = self._make(SessionInfoView)
        self.booking_update_view = self._make(BookingUpdateView)
        self.health_info_view    = self._make(HealthInfoView)
        self.device_scan_view    = self._make(DeviceScanView)

    def _configure(self):
        self.message_box = MessageBoxConsole(
            logger=self.model.logging_model.system_logger,
            formatter='{msg}'
        )

    @property
    def logger(self):
        return self.model.logging_model.system_logger

    def show_notification(self, msg, duration='short'):
        app_config = self.model.config_model.app_config
        toast = Notification(
            app_id=app_config.APP_DISPLAY_NAME,
            title="Notification",
            msg=str(msg),
            duration=duration,
            icon=app_config.APP_ICON
        )
        toast.show()
