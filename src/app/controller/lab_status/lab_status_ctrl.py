import threading
from datetime import datetime
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.controller.lab_status.lab_status_monitor import LabStatusMonitor
from src.core.agent_api import ActivityReport

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
        """PATCH /agent/equipment/activity. The backend derives inactive/offline timestamps itself
        from status changes, so ``inactive_since_dt`` is only kept for the local log."""
        info = self._session_info
        report = ActivityReport(
            status=status.value,
            booking_code=getattr(info, "booking_code", "") or "" if info else "",
            remote_user=(getattr(info, "remote_user", "") or "").lower() if info else "",
            remote_user_display_name=getattr(info, "remote_user_displayname", "") or "" if info else "",
            remote_computer=getattr(info, "remote_computer", "") or "" if info else "",
            remote_ip=getattr(info, "remote_ip", "") or "" if info else "",
        )
        threading.Thread(target=self._lab_api_model.report_activity, args=(report,), daemon=True).start()

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

    def _persist_session_end(self, start_time, end_time, info, total_seconds, active_seconds):
        """Write the local log, then queue the remote log (POST /agent/session-logs) for delivery."""
        try:
            self._session_logger.insert_session_log(
                self._lab_computer,
                start_time,
                end_time,
                int(total_seconds // 60),
                active_seconds // 60,
                getattr(info, "booking_code", ""),
                getattr(info, "remote_user", ""),
                getattr(info, "remote_user_displayname", ""),
                getattr(info, "remote_computer", ""),
                getattr(info, "remote_ip", "")
            )
        except Exception as e:
            self._logger.warning(f"Error logging session info: {e}")

        if start_time is None:
            return
        try:
            self._lab_api_model.queue_session_log(
                login_at=start_time,
                logout_at=end_time,
                active_seconds=active_seconds,
                remote_user=getattr(info, "remote_user", "") or "",
                remote_ip=getattr(info, "remote_ip", "") or "",
                remote_host=getattr(info, "remote_computer", "") or "",
                booking_code=getattr(info, "booking_code", "") or None,
            )
        except Exception as e:
            self._logger.warning(f"Error queuing session log: {e}")
            return
        threading.Thread(target=self._flush_session_logs, daemon=True).start()

    def _flush_session_logs(self):
        try:
            self._lab_api_model.flush_session_logs()
        except Exception as e:
            self._logger.warning(f"Error sending session logs (will retry): {e}")

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

        self._persist_session_end(start, end, info, total_seconds, active_seconds)

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
