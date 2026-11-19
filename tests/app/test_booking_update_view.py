"""The booking update dialog keeps the chosen action as a BookingAction (Qt returns plain str)."""

import pytest

import sys
from pathlib import Path

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
pytest.importorskip("win32api")  # the view's shared base classes need pywin32: runs on the Windows CI
sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))  # generated widgets import qt_embedded

from src.app.model.types.booking import BookingAction  # noqa: E402
from src.app.view.booking_update_view import BookingUpdateView  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_extend_enables_the_end_time_and_end_disables_it(qapp):
    view = BookingUpdateView()
    view.init()
    view.set_action(BookingAction.EXTEND)
    assert view.get_action() is BookingAction.EXTEND
    assert view.ui.to_datetime_edit.isEnabled()
    view.set_action(BookingAction.COMPLETE)
    assert view.get_action() is BookingAction.COMPLETE
    assert not view.ui.to_datetime_edit.isEnabled()
