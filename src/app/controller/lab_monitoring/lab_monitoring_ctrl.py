import time
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.controller.lab_monitoring.user_storage_monitor import UserStorageMonitor
from src.app.controller.lab_monitoring.computer_info_monitor import ComputerInfoMonitor
from src.app.controller.lab_monitoring.physical_device_monitor import PhysicalDeviceMonitor

class LabMonitoringCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        """
        Initializes class instance (lightweight; heavy objects in init()).
        """
        super().__init__()
        self._initialized = False
        self._user_storage_monitor = None
        self._computer_info_monitor = None
        self._physical_device_monitor = None
        self._api_service = None
        self._lab_api_model = None
        self._logger = None

    def init(self):
        if self._initialized:
            return self
        self._app_config = self.model.config_model.app_config
        self._app_settings = self.model.config_model.app_settings
        self._logger = self.model.logging_model.system_logger
        self._computer_model = self.model.computer_model
        self._lab_api_model = self.model.lab_api_model
        self._api_service = self._lab_api_model.service
        self._user_quota_config = self.model.config_model.user_quota_config
        self._lab_computer = self._computer_model.computer_name
        self._user_storage_monitor = UserStorageMonitor(
            self._app_settings.sharing_root_dir,
            self._lab_api_model,
            self._app_config.USER_STORAGE_INFO_FILE,
            quota=self._user_quota_config.default_quota,
            user_quotas=self._user_quota_config.user_quotas
        )
        self._user_storage_monitor.exception.connect(self._handle_exception)

        self._computer_info_monitor = ComputerInfoMonitor(
            self._computer_model,
            self._api_service,
            self._app_config.COMPUTER_INFO_FILE
        )
        self._computer_info_monitor.exception.connect(self._handle_exception)

        self._physical_device_monitor = PhysicalDeviceMonitor(
            self._api_service,
            self._app_config.DEVICE_MONITOR_INFO_FILE,
            poll_interval=TaskScheduleConfig.PHYSICAL_DEVICE_MONITOR
        )
        self._physical_device_monitor.device_inserted.connect(self._handle_device_inserted)
        self._physical_device_monitor.device_removed.connect(self._handle_device_removed)
        self._physical_device_monitor.exception.connect(self._handle_exception)
        self._start_physical_monitor()

        self._initialized = True
        return self

    #====================================================================
    # Internal helpers
    #====================================================================
    def _start_physical_monitor(self):
        if self._physical_device_monitor and not self._physical_device_monitor.isRunning():
            self._physical_device_monitor.start()
            self._logger.info("[PhysicalDeviceMonitor] start")

    def shutdown(self):
        """
        Gracefully stop background monitors (call on application exit).
        """
        try:
            if self._physical_device_monitor and self._physical_device_monitor.isRunning():
                self._physical_device_monitor.kill()
                self._physical_device_monitor.wait()
                self._logger.info("[PhysicalDeviceMonitor] completed")
        except Exception as e:
            self._logger.exception(f"Shutdown error (physical monitor): {e}")

    #====================================================================
    # Private methods
    #====================================================================
    def _handle_device_inserted(self, name, id):
        self._logger.info(f"Device inserted: {name} ({id})")

    def _handle_device_removed(self, name, id):
        self._logger.info(f"Device removed: {name} ({id})")

    def _handle_exception(self, e):
        self._logger.exception(e)

    #====================================================================
    # Public monitor task methods
    #====================================================================
    @task(schedule=TaskScheduleConfig.USER_STORAGE_MONITOR, heavy=True)
    def monitor_user_storage(self):
        if not self._initialized:
            return
        self._user_storage_monitor.run()

    @task(schedule=TaskScheduleConfig.COMPUTER_INFO_MONITOR, heavy=True)
    def monitor_computer_info(self):
        if not self._initialized:
            return
        self._computer_info_monitor.run()

    @task(schedule=TaskScheduleConfig.DEVICE_STATE_REFRESH, heavy=True)
    def refresh_physical_device_state(self):
        if not self._initialized:
            return
        # Refresh session and device filter list (only if monitor alive)
        if self._physical_device_monitor and self._physical_device_monitor.isRunning():
            self._physical_device_monitor.update_session_info(
                self.bus_request("get:session_info")
            )
            self._physical_device_monitor.load_device_filters()

    #====================================================================
    # Accessors
    #====================================================================
    @property
    def user_storage_monitor(self):
        return self._user_storage_monitor

    @property
    def computer_info_monitor(self):
        return self._computer_info_monitor

    @property
    def physical_device_monitor(self):
        return self._physical_device_monitor
