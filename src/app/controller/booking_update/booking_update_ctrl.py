"""Extend or end the running booking (``/agent/bookings/actions/extend`` and ``complete``)."""

from __future__ import annotations

from src.app.model.types.booking import BookingAction
from src.app.model.types.remote_session import RemoteSession
from src.mvc.base_controller import BaseController
from src.mvc.slot_guard import slot_guard


class BookingUpdateCtrl(BaseController):
    def init(self):
        self._logger = self.model.logging_model.system_logger
        self._backend_model = self.model.backend_model
        self._message_box = self.view.message_box
        self._booking_update_view = self.view.booking_update_view
        self._booking_update_view.ui.update_btn.clicked.connect(self.apply)
        self._booking_update_view.ui.cancel_btn.clicked.connect(self.close_dialog)
        self.bus_subscribe("booking_update:show", lambda _: self.show_dialog())

    def _show_error(self, e: Exception) -> None:
        self._logger.warning(f"[BookingUpdate] {e}")
        self._message_box.error(e, parent=self._booking_update_view)

    def _running_session(self) -> RemoteSession:
        session = self.bus_request("get:remote_session")
        if session is None or not session.has_booking:
            raise RuntimeError("No running booking.")
        return session

    @slot_guard(on_exception=_show_error)
    def show_dialog(self):
        session = self._running_session()
        view = self._booking_update_view
        view.set_minimum_ends_at_now()
        view.set_window(session.starts_at, session.ends_at)
        view.set_action(BookingAction.EXTEND)
        view.show()

    @slot_guard(on_exception=_show_error)
    def close_dialog(self):
        self._booking_update_view.close()

    @slot_guard(on_exception=_show_error)
    def apply(self):
        view = self._booking_update_view
        code = self._running_session().booking_code
        action = view.get_action()
        view.set_update_enabled(False)
        try:
            if action is BookingAction.EXTEND:
                ends_at = view.get_ends_at()
                if ends_at is None:
                    raise ValueError("Choose a new end time after the start.")
                self._backend_model.extend_booking(code, ends_at)
                message = "The booking has been extended."
            else:
                self._backend_model.complete_booking(code)
                message = "The booking has been ended."
        finally:
            view.set_update_enabled(True)
        self.bus_emit("booking:changed")
        self._message_box.info(message, parent=view)
        self.close_dialog()
