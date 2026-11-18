from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QDialog
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.BookingUpdateGui import Ui_BookingUpdateDialog
from src.app.model.types.booking_status import BookingStatus
from datetime import datetime


@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class BookingUpdateView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_BookingUpdateDialog()
        self.ui.setupUi(self)
        self._from_dt: QDateTime | None = None
        self._connect_signals()

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._ui_init()

    def _ui_init(self):
        self.ui.booking_status_combo.clear()
        self.ui.booking_status_combo.addItems([
            BookingStatus.IN_PROGRESS.value,
            BookingStatus.DONE.value
        ])
        self.set_minimum_to_datetime_now()

    def _connect_signals(self):
        self.ui.booking_status_combo.currentTextChanged.connect(self._on_status_change)
        self.ui.to_datetime_edit.dateTimeChanged.connect(self._validate_range)

    def _on_status_change(self, status: str):
        is_done = status == BookingStatus.DONE.value
        # When DONE we ignore custom end-time edits (disable input)
        self.ui.to_datetime_edit.setEnabled(not is_done)
        if is_done and self._from_dt:
            # Force to time = from time to prevent accidental extension
            self.ui.to_datetime_edit.setDateTime(self._from_dt)
        self._validate_range()

    def _validate_range(self):
        from_dt = self.ui.from_datetime_edit.dateTime()
        to_dt = self.ui.to_datetime_edit.dateTime()
        ok = to_dt >= from_dt
        self._apply_valid_style(ok)
        return ok

    def _apply_valid_style(self, ok: bool):
        widget = self.ui.to_datetime_edit
        if ok:
            widget.setStyleSheet("")
        else:
            widget.setStyleSheet("QDateTimeEdit { border: 2px solid #d9534f; }")

    def _to_python(self, qdt: QDateTime) -> datetime:
        return qdt.toPython()

    def set_minimum_to_datetime_now(self):
        now = QDateTime.currentDateTime()
        self.ui.to_datetime_edit.setMinimumDateTime(now)

    def set_booking_status(self, status: str):
        idx = self.ui.booking_status_combo.findText(status)
        if idx >= 0:
            self.ui.booking_status_combo.setCurrentIndex(idx)
        self._on_status_change(self.get_booking_status())

    def get_booking_status(self) -> str:
        return self.ui.booking_status_combo.currentText()

    def set_from_datetime(self, from_datetime: QDateTime | datetime):
        if isinstance(from_datetime, datetime):
            from_datetime = QDateTime.fromSecsSinceEpoch(int(from_datetime.timestamp()))
        self._from_dt = from_datetime
        self.ui.from_datetime_edit.setDateTime(from_datetime)
        # Ensure to >= from
        if self.ui.to_datetime_edit.dateTime() < from_datetime:
            self.ui.to_datetime_edit.setDateTime(from_datetime)
        self._validate_range()

    def set_to_datetime(self, to_datetime: QDateTime | datetime):
        if isinstance(to_datetime, datetime):
            to_datetime = QDateTime.fromSecsSinceEpoch(int(to_datetime.timestamp()))
        self.ui.to_datetime_edit.setDateTime(to_datetime)
        self._validate_range()

    def get_to_datetime(self) -> datetime | None:
        if not self._validate_range():
            return None
        return self._to_python(self.ui.to_datetime_edit.dateTime())

    def is_valid(self) -> bool:
        return self._validate_range()

    def set_enabled_update(self, enabled: bool):
        self.ui.update_btn.setEnabled(enabled)