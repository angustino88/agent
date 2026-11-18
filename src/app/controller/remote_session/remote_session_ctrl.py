"""Owns the remote session from login to logout: timer, session dialog and session logs."""

from __future__ import annotations

import ctypes
import threading
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtWidgets import QMessageBox

from src.app.controller.remote_session.session_timer import SessionTimer
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.model.types.booking import Booking
from src.app.model.types.login_event import LoginEvent
from src.app.model.types.login_info import LoginInfo
from src.app.model.types.remote_session import RemoteSession
from src.mvc.base_controller import BaseController
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task
from src.utils.remote_desktop import RemoteDesktop

WARN_AT_MINUTES = (10, 5, 1)


class RemoteSessionCtrl(BaseController):
    def __init__(self):
        super().__init__()
        self._warned_at: set[int] = set()
        self._login_info: Optional[LoginInfo] = None
        self._session: Optional[RemoteSession] = None
        self._login_at: Optional[datetime] = None

    def init(self):
        self._logger = self.model.logging_model.system_logger
        self._session_logger = self.model.logging_model.session_logger
        self._app_settings = self.model.config_model.app_settings
        self._backend_model = self.model.backend_model
        self._computer_name = self.model.computer_model.computer_name
        self._message_box = self.view.message_box
        self._session_info_view = self.view.session_info_view
        self._main_window_view = self.view.main_window_view

        self._timer = SessionTimer(self._backend_model)
        self._timer.exception.connect(self._log_exception)
        self._timer.expired.connect(self._on_expired)
        self._timer.minutes_left_changed.connect(self._on_minutes_left_changed)
        self._timer.ends_at_changed.connect(self._on_ends_at_changed)

        ui = self._session_info_view.ui
        ui.end_booking_btn.clicked.connect(self.end_booking)
        ui.refresh_booking_btn.clicked.connect(self.refresh_booking)
        ui.update_booking_btn.clicked.connect(lambda: self.bus_emit("booking_update:show"))
        self._main_window_view.ui.session_info_btn.clicked.connect(self.show_dialog)

        self.expose_get("remote_session", lambda: self._session)
        self.bus_subscribe("session:start", lambda payload: self.start_session(*payload))
        self.bus_subscribe("session:end", lambda _: self.end_session())
        self.bus_subscribe("booking:changed", lambda _: self._timer.recheck_now())

    # ------------------------------------------------------------------ helpers

    def _log_exception(self, e: Exception) -> None:
        self._logger.exception(e)

    def _show_error(self, e: Exception) -> None:
        self._message_box.error(e, parent=self._session_info_view)

    def _temporary_duration(self) -> timedelta:
        """Ten minutes when the backend and web app answer; an hour otherwise (or in safe mode)."""
        if self._app_settings.safe_mode:
            self._logger.warning("[RemoteSession] Safe mode active")
            return timedelta(minutes=60)
        try:
            if self._backend_model.check_alive() and self._backend_model.check_frontend_alive():
                return timedelta(minutes=10)
        except Exception as e:
            self._logger.warning(f"[RemoteSession] Availability check failed: {e}")
        return timedelta(minutes=60)

    # ------------------------------------------------------------------ timer events

    def _on_expired(self) -> None:
        """Disconnect a remote login, lock a console login."""
        event = self._login_info.login_event if self._login_info else None
        try:
            if event == LoginEvent.REMOTE_LOGIN:
                RemoteDesktop.disconnect()
            elif event == LoginEvent.SCREEN_LOGIN:
                ctypes.windll.user32.LockWorkStation()
            else:
                self._logger.warning(f"[RemoteSession] Expired with unsupported login event {event!r}")
        except Exception as e:
            self._logger.exception(e)

    def _on_minutes_left_changed(self, minutes_left: int) -> None:
        self._session_info_view.set_minutes_left(minutes_left)
        for minutes in WARN_AT_MINUTES:
            if minutes_left <= minutes and minutes not in self._warned_at:
                plural = "s" if minutes > 1 else ""
                self.view.show_notification(f"Your session will disconnect in less than {minutes} minute{plural}")
                self._warned_at.add(minutes)
        if minutes_left > max(WARN_AT_MINUTES):
            self._warned_at.clear()

    def _on_ends_at_changed(self, ends_at: datetime) -> None:
        if self._session:
            self._session = replace(self._session, ends_at=ends_at)
        self._session_info_view.set_ends_at(ends_at)
        self._logger.info(f"[RemoteSession] Ends at {ends_at}")

    # ------------------------------------------------------------------ lifecycle

    def start_session(self, login_info: LoginInfo, booking: Optional[Booking]) -> None:
        if self._session is not None:
            self._logger.warning("[RemoteSession] start_session while a session is open; ignored")
            return
        self._login_info = login_info
        self._login_at = datetime.now()
        self._session = RemoteSession(
            computer_name=self._computer_name,
            technical_user=login_info.technical_user,
            remote_user=login_info.username,
            remote_user_display_name=login_info.user_display_name,
            remote_ip=RemoteDesktop.get_client_ip() or "",
            remote_computer=RemoteDesktop.get_client_hostname() or "",
            booking_code=booking.booking_code if booking else None,
            starts_at=booking.starts_at if booking else None,
            ends_at=booking.ends_at if booking else None,
            # An administrator without a booking is maintaining the computer.
            is_maintenance=login_info.login_mode.is_admin and booking is None,
        )
        self._logger.info(f"[RemoteSession] Started {self._session}")
        self._warned_at.clear()
        self._timer.start(self._session, temporary_duration=self._temporary_duration())
        self.bus_emit("session:started", self._session)

        view = self._session_info_view
        view.clear_info()
        view.set_session(self._session, ends_at=self._timer.ends_at)
        view.ui.refresh_booking_btn.setEnabled(self._session.has_booking)
        view.ui.update_booking_btn.setEnabled(self._session.has_booking)
        view.ui.end_booking_btn.setEnabled(self._session.has_booking)
        view.show_dialog()

    def end_session(self) -> None:
        if self._session is None:
            return
        session, login_at, logout_at = self._session, self._login_at or datetime.now(), datetime.now()
        inactive_seconds = float(self.bus_request("get:inactive_seconds") or 0)
        active_seconds = max(0.0, (logout_at - login_at).total_seconds() - inactive_seconds)
        self._timer.stop()
        self._record_session(session, login_at, logout_at, active_seconds)
        self._logger.info(
            f"[RemoteSession] Ended booking={session.booking_code or '-'} user={session.remote_user} "
            f"total={int((logout_at - login_at).total_seconds())}s active={int(active_seconds)}s"
        )
        self.bus_emit("session:ended")
        self._session = None
        self._login_info = None
        self._main_window_view.set_admin_enabled(True)
        self._session_info_view.close()

    def _record_session(
        self, session: RemoteSession, login_at: datetime, logout_at: datetime, active_seconds: float
    ) -> None:
        """Local log first, then queue for the backend (``POST /agent/session-logs``) and try to send."""
        try:
            self._session_logger.insert_session_log(session, login_at, logout_at, active_seconds)
        except Exception as e:
            self._logger.warning(f"[RemoteSession] Local session log failed: {e}")
        try:
            self._backend_model.queue_session_log(session, login_at, logout_at, active_seconds)
        except Exception as e:
            self._logger.warning(f"[RemoteSession] Queuing session log failed: {e}")
            return
        threading.Thread(target=self._backend_model.flush_session_logs, daemon=True).start()

    @task(schedule=TaskScheduleConfig.SESSION_TIMER, heavy=True)
    def run_session_timer(self):
        self._timer.run()

    # ------------------------------------------------------------------ slots

    @slot_guard(on_exception=_show_error)
    def show_dialog(self):
        self._session_info_view.show_dialog()

    @slot_guard(on_exception=_show_error)
    def end_booking(self):
        if self._session is None or not self._session.has_booking:
            self._message_box.info("No running booking to end.", parent=self._session_info_view)
            return
        box = QMessageBox(self._session_info_view)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("End booking")
        box.setText("End the current booking now?")
        box.setInformativeText("The booking will be completed and cannot be resumed.")
        confirm = box.addButton("End booking", QMessageBox.AcceptRole)
        box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(confirm)
        box.setMinimumWidth(400)
        box.adjustSize()
        box.exec()
        if box.clickedButton() != confirm:
            return
        self._backend_model.complete_booking(self._session.booking_code)
        self._timer.recheck_now()
        self._message_box.info("The booking has been ended.", parent=self._session_info_view)

    @slot_guard(on_exception=_show_error)
    def refresh_booking(self):
        self._timer.recheck_now()
