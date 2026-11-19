"""Reports this computer's live activity (``PATCH /agent/equipment/activity``) and logs it locally."""

import threading

from src.app.controller.activity.activity_monitor import ActivityMonitor
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.model.types.activity_status import ActivityStatus
from src.app.model.types.remote_session import RemoteSession
from src.mvc.base_controller import BaseController
from src.mvc.task_schedule import task


class ActivityCtrl(BaseController):
    def __init__(self):
        super().__init__()
        self._session: RemoteSession | None = None
        self._activity_monitor = ActivityMonitor()
        self._activity_monitor.status_changed.connect(self._on_status_changed)

    def init(self):
        self._logger = self.model.logging_model.system_logger
        self._session_logger = self.model.logging_model.session_logger
        self._backend_model = self.model.backend_model
        self._computer_name = self.model.computer_model.computer_name
        self._activity_monitor.exception.connect(lambda e: self._logger.warning(f"[Activity] {e}"))

        self.expose_get("inactive_seconds", lambda: self._activity_monitor.inactive_seconds_total)
        self.bus_subscribe("session:started", self._on_session_started)
        self.bus_subscribe("session:ended", lambda _: self._on_session_ended())

    # ------------------------------------------------------------------ events

    def _on_session_started(self, session: RemoteSession) -> None:
        self._session = session
        self._activity_monitor.on_session_started(session)

    def _on_session_ended(self) -> None:
        self._session = None
        self._activity_monitor.on_session_ended()

    def _on_status_changed(self, change: tuple) -> None:
        status, _inactive_minutes = change
        try:
            self._session_logger.insert_status_log(self._computer_name, status.value, self._session)
        except Exception as e:
            self._logger.warning(f"[Activity] Local status log failed: {e}")
        threading.Thread(target=self._report, args=(status, self._session), daemon=True).start()

    def _report(self, status: ActivityStatus, session: RemoteSession | None) -> None:
        self._backend_model.report_activity(status, session)

    # ------------------------------------------------------------------ scheduled

    @task(schedule=TaskScheduleConfig.ACTIVITY_MONITOR, heavy=True)
    def monitor_activity(self):
        self._activity_monitor.run()
