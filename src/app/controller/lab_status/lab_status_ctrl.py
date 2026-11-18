import threading
from datetime import datetime
from src.utils.datetime import iso_datetime
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.controller.lab_status.lab_status_monitor import LabStatusMonitor

class LabStatusCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        """
        Initializes class instance
        """
        super().__init__()
        self._session_info = None
        self._last_status = None
        self._lab_status_monitor = LabStatusMonitor()
        self._lab_status_monitor.status.connect(self._handle_lab_status)
        self._session_start_time = None
        self._session_end_time = None
        self._total_inactive_time = 0
        self._last_inactive_time = 0

    def init(self):
        """
        Additional initialization after the class instance has been initialized
        """
        self._logger = self.model.logging_model.system_logger
        self._session_logger = self.model.logging_model.session_logger
        self._message_box = self.view.message_box
        self._session_info_view = self.view.session_info_view
        self._main_window_view = self.view.main_window_view
        self._lab_api_model = self.model.lab_api_model
        self._api_service = self.model.lab_api_model.service
        self._lab_computer = self.model.computer_model.computer_name

        # EventBus wiring
        self.bus_subscribe("session:started", lambda session_info: self.on_session_start(session_info))
        self.bus_subscribe("session:ended", lambda _: self.on_session_end())
    
    #====================================================================
    # Private methods
    #====================================================================
    def _log_lab_status(self, status, inactive_time):
        if status.value != self._last_status:
            self._last_status = status.value
            if self._session_info != None:
                self._session_logger.insert_status_log(
                    self._lab_computer,
                    status.value,
                    getattr(self._session_info, "remote_user", ""),
                    getattr(self._session_info, "remote_user_displayname", ""),
                    getattr(self._session_info, "remote_computer", ""),
                    getattr(self._session_info, "remote_ip", "")
                )
            else:
                self._session_logger.insert_status_log(
                    self._lab_computer,
                    status.value,
                    "-", "-", "-", "-"
                )

    def _send_lab_status(self, status, inactive_since_dt):
        def send():
            body = {
                "status": status.value,
                "inactive_time": iso_datetime(inactive_since_dt) if inactive_since_dt else None,
                "booking_code": "",
                "remote_user": "",
                "remote_user_displayname": "",
                "remote_ip": "",
                "remote_computer": ""
            }
            if self._session_info is not None:
                body.update({
                    "booking_code": getattr(self._session_info, "booking_code", ""),
                    "remote_user": getattr(self._session_info, "remote_user", ""),
                    "remote_user_displayname": getattr(self._session_info, "remote_user_displayname", ""),
                    "remote_ip": getattr(self._session_info, "remote_ip", ""),
                    "remote_computer": getattr(self._session_info, "remote_computer", "")
                })
            try:
                self._api_service.send_lab_status(**body, timeout=2)
            except Exception as e:
                self._logger.warning(f'Error sending lab status: {e}')

        threading.Thread(target=send, daemon=True).start()

    def _handle_lab_status(self, lab_status):
        status, inactive_time_mins, inactive_since_dt = lab_status

        delta = inactive_time_mins - self._last_inactive_time
        if delta > 0:
            self._total_inactive_time += delta
        self._last_inactive_time = inactive_time_mins
        try:
            self._log_lab_status(status, inactive_time_mins)
        except Exception as e:
            self._logger.warning(f'Error logging lab status: {e}')

        try:
            self._send_lab_status(status, inactive_since_dt)
        except Exception as e:
            self._logger.warning(f'Error sending lab status: {e}')

    def _persist_session_end(self, start_time, end_time, info, total_seconds, active_minutes):
        """Write local + remote session logs."""
        try:
            self._session_logger.insert_session_log(
                self._lab_computer,
                start_time,
                end_time,
                int(total_seconds // 60),
                active_minutes,
                getattr(info, "booking_code", ""),
                getattr(info, "remote_user", ""),
                getattr(info, "remote_user_displayname", ""),
                getattr(info, "remote_computer", ""),
                getattr(info, "remote_ip", "")
            )
        except Exception as e:
            self._logger.warning(f"Error logging session info: {e}")

        try:
            self._api_service.send_session_log(
                login_time=iso_datetime(start_time),
                logout_time=iso_datetime(end_time),
                active_time=active_minutes,
                remote_user=getattr(info, "remote_user", ""),
                remote_user_displayname=getattr(info, "remote_user_displayname", ""),
                remote_computer=getattr(info, "remote_computer", ""),
                remote_ip=getattr(info, "remote_ip", ""),
                booking_code=getattr(info, "booking_code", "")
            )
        except Exception as e:
            self._logger.warning(f"Error sending session info: {e}")

    #====================================================================
    # Public methods
    #====================================================================
    def on_session_start(self, session_info, start_time: datetime | None = None):
        self._session_info = session_info
        self._lab_status_monitor.on_session_start(session_info)
        self._session_start_time = start_time or datetime.now()
        self._session_end_time = None
        self._total_inactive_time = 0
    
    def on_session_end(self, end_time: datetime | None = None):
        self._lab_status_monitor.on_session_end()
        self._session_end_time = end_time or datetime.now()

        start = self._session_start_time
        end = self._session_end_time
        info = self._session_info or type("Empty", (), {})()

        total_seconds = (end - start).total_seconds() if start else 0
        inactive_seconds = int(self._total_inactive_time * 60)
        active_seconds = max(0, int(total_seconds - inactive_seconds))
        active_minutes = active_seconds // 60

        self._persist_session_end(start, end, info, total_seconds, active_minutes)

        self._logger.info(
            f"[SessionEnd] booking={getattr(info,'booking_code','')} user={getattr(info,'remote_user','')} "
            f"total={int(total_seconds)}s inactive={inactive_seconds}s active={active_seconds}s"
        )

        self._session_info = None
        self._session_start_time = None
        self._session_end_time = None
        self._total_inactive_time = 0

    @task(schedule=TaskScheduleConfig.LAB_STATUS_MONITOR, heavy=True)
    def monitor_lab_status(self):
        self._lab_status_monitor.run()

    #====================================================================
    # pyqtSlot method - which connected to UI signal
    #====================================================================
