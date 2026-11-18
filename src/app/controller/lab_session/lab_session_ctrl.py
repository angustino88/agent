import ctypes
from datetime import datetime, timedelta
from dataclasses import replace
from PySide6.QtWidgets import QMessageBox
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController
from src.app.model.types.session_info import SessionInfo
from src.app.model.types.booking_status import BookingStatus
from src.app.model.types.login_event import LoginEvent
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.controller.lab_session.lab_session_monitor import LabSessionMonitor
from src.utils.remote_desktop import RemoteDesktop

NOTIFY_MINUTES = (10, 5, 1)

class LabSessionCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        """
        Initializes class instance
        """
        super().__init__()
        self._notified_times = set()
        self._login_info   = None
        self._session_info = None

    def init(self):
        """
        Additional initialization after the class instance has been initialized
        """
        self._logger = self.model.logging_model.system_logger
        self._app_settings = self.model.config_model.app_settings
        self._message_box = self.view.message_box
        self._session_info_view = self.view.session_info_view
        self._main_window_view = self.view.main_window_view
        self._lab_api_model = self.model.lab_api_model
        self._lab_computer = self.model.computer_model.computer_name
        self._lab_session_monitor = LabSessionMonitor(self._lab_api_model)
        self._lab_session_monitor.exception.connect(self._handle_exception_silent)
        self._lab_session_monitor.expired.connect(self._handle_session_expired)
        self._lab_session_monitor.timeleft.connect(self._handle_timeleft_changed)
        self._lab_session_monitor.new_expired_datetime.connect(self._handle_expired_datetime_updated)
        self._session_info_view.ui.end_booking_btn.clicked.connect(self.on_end_booking_requested)
        self._session_info_view.ui.refresh_booking_btn.clicked.connect(self.refresh_booking)
        self._session_info_view.ui.update_booking_btn.clicked.connect(lambda: self.bus_emit("booking_update:show"))
        self.view.main_window_view.ui.session_info_btn.clicked.connect(self.show_dialog)

        # EventBus wiring
        self.expose_get("session_info", lambda: self._session_info)
        self.bus_subscribe("session:start", lambda payload: self.start_session(*payload))
        self.bus_subscribe("session:end", lambda _: self.end_session())
        self.bus_subscribe("session:recheck", lambda _: self.trigger_recheck_booking())

    #====================================================================
    # Private methods
    #====================================================================
    def _handle_exception_silent(self, e):
        """Logs exceptions silently."""
        self._logger.exception(e)
    
    def _handle_exception(self, e):
        """Shows error message to user."""
        self._message_box.error(e, parent=self._session_info_view)

    def _handle_session_expired(self):
        """Handles session expiration for REMOTE_LOGIN and SCREEN_LOGIN only."""
        try:
            if self._login_info and self._login_info.login_action == LoginEvent.REMOTE_LOGIN:
                RemoteDesktop.disconnect()
            elif self._login_info and self._login_info.login_action == LoginEvent.SCREEN_LOGIN:
                ctypes.windll.user32.LockWorkStation()
            else:
                self._logger.warning(
                    f"Session expired: unsupported login action '{getattr(self._login_info, 'login_action', None)}'. Only REMOTE_LOGIN and SCREEN_LOGIN are handled"
                )
        except Exception as e:
            self._logger.exception(e)

    def _handle_timeleft_changed(self, timeleft):
        """Update UI & notifications."""
        try:
            self._session_info_view.set_timeleft(timeleft)
            for minutes in NOTIFY_MINUTES:
                if timeleft <= minutes and minutes not in self._notified_times:
                    self.view.show_nofication(
                        f"Your session will automatically disconnect in less than {minutes} minute{'s' if minutes > 1 else ''}"
                    )
                    self._notified_times.add(minutes)
            if timeleft > max(NOTIFY_MINUTES):
                self._notified_times.clear()
        except Exception as e:
            self._logger.exception(e)

    def _handle_expired_datetime_updated(self, expired_datetime):
        """Update expiration field."""
        try:
            if self._session_info:
                self._session_info = replace(self._session_info, to_datetime=expired_datetime)
            self._session_info_view.set_to_datetime(expired_datetime)
            self._logger.info(f"[SessionUpdate] expiration -> {expired_datetime}")
        except Exception as e:
            self._logger.exception(e)

    #====================================================================
    # Public methods
    #====================================================================
    @property
    def session_info(self):
        return self._session_info

    def trigger_recheck_booking(self):
        self._lab_session_monitor.trigger_recheck_booking()
    
    def recheck_booking(self):
        self._lab_session_monitor.recheck_booking()

    def start_session(self, login_info, booking_info):
        """Starts a new session (fails if one already active)."""
        if self._session_info is not None:
            self._logger.warning("start_session called while a session is already active; ignoring")
            return

        self._login_info = login_info
        client_ip = RemoteDesktop.get_client_ip()
        client_host = RemoteDesktop.get_client_hostname()

        self._session_info = SessionInfo(
            booking_id=getattr(booking_info, "booking_id", None) if booking_info else None,
            booking_code=getattr(booking_info, "booking_code", None) if booking_info else None,
            lab_computer=self._lab_computer,
            is_maintenance=(
                getattr(booking_info, "booking_project", "").lower() == "maintenance"
                if booking_info else False
            ),
            technical_user=getattr(login_info, "technical_user", ""),
            remote_user=getattr(login_info, "username", ""),
            remote_user_displayname=getattr(login_info, "user_displayname", ""),
            remote_ip=client_ip,
            remote_computer=client_host,
            from_datetime=getattr(booking_info, "from_datetime", None) if booking_info else None,
            to_datetime=getattr(booking_info, "to_datetime", None) if booking_info else None,
        )
        self._logger.info(f"[SessionStart] {self._session_info}")
        self._notified_times.clear()

        duration = self._calculate_initial_duration()
        self._lab_session_monitor.start(self._session_info, duration=duration)
        self.bus_emit("session:started", self._session_info)
        self._session_info_view.clear_info()
        self._session_info_view.set_info(self._session_info)
        has_booking = self._session_info.booking_code is not None
        self._session_info_view.ui.refresh_booking_btn.setEnabled(has_booking)
        self._session_info_view.ui.update_booking_btn.setEnabled(has_booking)
        self._session_info_view.show_dialog()

    def _calculate_initial_duration(self):
        """Decide initial monitor window."""
        try:
            if self._app_settings.safe_mode:
                self._logger.warning(f"Safe mode active")
                return timedelta(minutes=60)

            backend_ok = self._lab_api_model.check_backend_alive()
            frontend_ok = self._lab_api_model.check_frontend_alive()
            if backend_ok and frontend_ok:
                return timedelta(minutes=10)
        except Exception as e:
            self._logger.warning(f"Alive check failed: {e}")
        return timedelta(minutes=60)

    def end_session(self):
        """Ends current session (noop if none)."""
        if self._session_info is None:
            self._logger.debug("end_session called with no active session")
            return
        booking = getattr(self._session_info, "booking_code", None)
        user = getattr(self._session_info, "remote_user", None)
        try:
            self._lab_session_monitor.stop()
        except Exception as e:
            self._logger.exception(f"Error stopping session monitor: {e}")
        try:
            self.bus_emit("session:ended")
        except Exception as e:
            self._logger.exception(f"Error emitting session:ended: {e}")
        self._session_info = None
        self._main_window_view.set_admin_enabled(True)
        self._session_info_view.close()

    @task(schedule=TaskScheduleConfig.LAB_SESSION_MONITOR, heavy=True)
    def monitor_lab_session(self):
        """Periodically runs session monitor."""
        self._lab_session_monitor.run()

    #====================================================================
    # pyqtSlot method - which connected to UI signal
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        self._session_info_view.show_dialog()

    @slot_guard(on_exception=_handle_exception)
    def on_end_booking_requested(self):
        if self._session_info is None:
            self._message_box.info("No active session", parent=self._session_info_view)
            return

        booking_id = getattr(self._session_info, "booking_id", None)
        if not booking_id:
            self._message_box.info("No active booking to end.", parent=self._session_info_view)
            return

        msg = QMessageBox(self._session_info_view)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Confirm End Booking")
        msg.setText("Are you sure you want to end the current booking?")
        msg.setInformativeText("This will mark the booking as done and cannot be undone.")
        confirm_btn = msg.addButton("End Booking", QMessageBox.AcceptRole)
        msg.addButton(QMessageBox.Cancel)
        msg.setDefaultButton(confirm_btn)
        msg.setMinimumWidth(400)
        msg.adjustSize()
        msg.exec()

        if msg.clickedButton() != confirm_btn:
            return

        resp = self._lab_api_model.service.update_booking(
            booking_id=booking_id,
            status=BookingStatus.DONE.value,
        )
        if not getattr(resp, "success", False):
            raise RuntimeError(
                f"Failed marking booking done (id={booking_id}) status={resp.status_code} err={resp.text[:200]}"
            )

        self.trigger_recheck_booking()
        self._message_box.info("Booking has been ended successfully.", parent=self._session_info_view)

    @slot_guard(on_exception=_handle_exception)
    def refresh_booking(self):
        self.recheck_booking()
        self._message_box.info("Booking information refreshed", parent=self._session_info_view)