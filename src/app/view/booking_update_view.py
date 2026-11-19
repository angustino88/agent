from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QDialog

from src.app.model.types.booking import BookingAction
from src.app.view.widgets.BookingUpdateGui import Ui_BookingUpdateDialog
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.utils.metaclass import metaclass_factory


@log_events("showEvent", "closeEvent", logger_name="view.logger")
class BookingUpdateView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_BookingUpdateDialog()
        self.ui.setupUi(self)
        self.ui.label_8.setText("Action")
        self.ui.label_6.setText("Starts at:")
        self.ui.label_7.setText("Ends at:")
        self.ui.booking_status_combo.currentIndexChanged.connect(lambda _: self._on_action_changed())
        self.ui.to_datetime_edit.dateTimeChanged.connect(lambda _: self._validate())

    def init(self):
        self.ui.booking_status_combo.clear()
        for action in BookingAction:
            self.ui.booking_status_combo.addItem(action.value, action)
        self.set_minimum_ends_at_now()

    # ------------------------------------------------------------------ internals

    def _on_action_changed(self) -> None:
        # Ending a booking keeps its booked end time; only extending edits it.
        self.ui.to_datetime_edit.setEnabled(self.get_action() is BookingAction.EXTEND)
        self._validate()

    def _validate(self) -> bool:
        ok = self.get_action() is not BookingAction.EXTEND or (
            self.ui.to_datetime_edit.dateTime() > self.ui.from_datetime_edit.dateTime()
        )
        self.ui.to_datetime_edit.setStyleSheet("" if ok else "QDateTimeEdit { border: 2px solid #d9534f; }")
        return ok

    @staticmethod
    def _to_qt(value: datetime) -> QDateTime:
        return QDateTime.fromSecsSinceEpoch(int(value.timestamp()))

    # ------------------------------------------------------------------ API

    def set_minimum_ends_at_now(self) -> None:
        self.ui.to_datetime_edit.setMinimumDateTime(QDateTime.currentDateTime())

    def set_window(self, starts_at: datetime | None, ends_at: datetime | None) -> None:
        if starts_at:
            self.ui.from_datetime_edit.setDateTime(self._to_qt(starts_at))
        if ends_at:
            self.ui.to_datetime_edit.setDateTime(self._to_qt(ends_at))
        self._validate()

    def set_action(self, action: BookingAction) -> None:
        index = self.ui.booking_status_combo.findData(action)
        if index >= 0:
            self.ui.booking_status_combo.setCurrentIndex(index)
        self._on_action_changed()

    def get_action(self) -> BookingAction:
        # Qt returns item data of a ``str`` enum as a plain ``str``: convert it back, or an identity
        # check against BookingAction.EXTEND fails (end time disabled, Update would end the booking).
        data = self.ui.booking_status_combo.currentData()
        try:
            return BookingAction(data)
        except ValueError:
            return BookingAction.EXTEND

    def get_ends_at(self) -> datetime | None:
        """The chosen end time (naive local time), or ``None`` when it is not after the start."""
        return self.ui.to_datetime_edit.dateTime().toPython() if self._validate() else None

    def set_update_enabled(self, enabled: bool) -> None:
        self.ui.update_btn.setEnabled(enabled)
