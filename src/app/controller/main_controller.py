from src.mvc.base_controller import BaseMainController
from src.app.controller.systray.systray_ctrl import SystrayCtrl
from src.app.controller.app_info.app_info_ctrl import AppInfoCtrl
from src.app.controller.app_update.app_update_ctrl import AppUpdateCtrl
from src.app.controller.user_manual.user_manual_ctrl import UserManualCtrl
from src.app.controller.login.login_ctrl import LoginCtrl
from src.app.controller.activity.activity_ctrl import ActivityCtrl
from src.app.controller.remote_session.remote_session_ctrl import RemoteSessionCtrl
from src.app.controller.monitoring.monitoring_ctrl import MonitoringCtrl
from src.app.controller.booking_update.booking_update_ctrl import BookingUpdateCtrl
from src.app.controller.settings.settings_ctrl import SettingsCtrl
from src.app.controller.server_config.server_config_ctrl import ServerConfigCtrl
from src.app.controller.health_check.health_check_ctrl import HealthCheckCtrl
from src.app.controller.log_check.log_check_ctrl import LogCheckCtrl
from src.app.controller.device_scan.device_scan_ctrl import DeviceScanCtrl

class MainController(BaseMainController):

    def __init__(self, model, view, bus, max_workers: int = 4):
        super().__init__(model, view, bus, max_workers)

    def _setup(self):
        self.systray_controller        = self._make(SystrayCtrl)
        self.app_info_controller       = self._make(AppInfoCtrl)
        self.app_update_controller     = self._make(AppUpdateCtrl)
        self.user_manual_controller    = self._make(UserManualCtrl)
        self.login_controller          = self._make(LoginCtrl)
        self.remote_session_controller = self._make(RemoteSessionCtrl)
        self.activity_controller       = self._make(ActivityCtrl)
        self.monitoring_controller     = self._make(MonitoringCtrl)
        self.booking_update_controller = self._make(BookingUpdateCtrl)
        self.settings_controller       = self._make(SettingsCtrl)
        self.server_config_controller  = self._make(ServerConfigCtrl)
        self.health_check_controller   = self._make(HealthCheckCtrl)
        self.log_check_controller      = self._make(LogCheckCtrl)
        self.device_scan_controller    = self._make(DeviceScanCtrl)

    def _configure(self):
        self.expose_get("runner", lambda: self.runner)
