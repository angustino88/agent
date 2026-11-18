from __future__ import annotations
from typing import Optional
from src.mvc.slot_guard import slot_guard
from src.mvc.base_controller import BaseController
from src.app.model.types.booking_status import BookingStatus

class BookingUpdateCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._logger = None
        self._lab_api_model = None
        self._message_box = None
        self._booking_update_view = None
        self._lab_session_controller = None

    def init(self):
        if self._initialized:
            return self
        self._logger = self.model.logging_model.system_logger
        self._lab_api_model = self.model.lab_api_model
        self._message_box = self.view.message_box
        self._booking_update_view = self.view.booking_update_view
        self._booking_update_view.ui.update_btn.clicked.connect(self.update_booking)
        self._booking_update_view.ui.cancel_btn.clicked.connect(self.close_dialog)
        self.bus_subscribe("booking_update:show", lambda _: self.show_dialog())
        self._initialized = True
        return self

    #====================================================================
    # Private methods
    #====================================================================
    def _handle_exception(self, e: Exception):
        self._logger.exception(e)
        self._message_box.error(e, parent=self._booking_update_view)

    def _ensure_session(self):
        session = self.bus_request("get:session_info")
        if not session or not getattr(session, "booking_code", None):
            raise RuntimeError("No active booking/session.")
        return session

    def _apply_update(self, selected_status: str, to_datetime) -> None:
        code = self._ensure_session().booking_code
        if selected_status == BookingStatus.IN_PROGRESS.value:
            self._lab_api_model.extend_booking(code, to_datetime)
            return
        if selected_status == BookingStatus.DONE.value:
            self._lab_api_model.complete_booking(code)
            return
        raise ValueError("Invalid booking status selected.")

    def _after_success(self):
        self.bus_emit("session:recheck")
        self._message_box.info(f"Booking updated successfully", parent=self._booking_update_view)
        self.close_dialog()

    #====================================================================
    # pyqtSlot methods
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        self.bus_emit("session:recheck")
        session = self._ensure_session()
        v = self._booking_update_view
        v.set_minimum_to_datetime_now()
        v.set_from_datetime(session.from_datetime)
        v.set_to_datetime(session.to_datetime)
        v.set_booking_status(BookingStatus.IN_PROGRESS.value)
        v.show()

    @slot_guard(on_exception=_handle_exception)
    def close_dialog(self):
        self._booking_update_view.close()

    @slot_guard(on_exception=_handle_exception)
    def update_booking(self):
        v = self._booking_update_view
        selected_status = v.get_booking_status()
        to_datetime = v.get_to_datetime()

        if selected_status == BookingStatus.IN_PROGRESS.value and to_datetime is None:
            raise ValueError("To datetime is required for updating an in-progress booking.")

        v.set_enabled_update(False)
        try:
            self._apply_update(selected_status, to_datetime)
            self._after_success()
        finally:
            v.set_enabled_update(True)
