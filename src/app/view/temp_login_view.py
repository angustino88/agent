from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.TempLoginGui import Ui_TempLoginDialog
from src.app.model.types.booking_status import BookingStatus


@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class TempLoginView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_TempLoginDialog()
        self.ui.setupUi(self)

    def init(self):
        self._app_config = self.model.config_model.app_config
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._ui_init()

    def _ui_init(self):
        self.ui.otp_code_edit.setValidator(QtGui.QIntValidator())
        self.ui.otp_code_edit.setMaxLength(6)
        self.ui.resend_label.setText('<a href="#">Resend</a>')
        self.ui.resend_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.ui.resend_label.setOpenExternalLinks(False)
        self.ui.verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0B36A;  /* Warm golden base */
                color: #1E1E1E;             /* Dark text for contrast */
                border-radius: 4px;         /* Rounded corners */
            }
            QPushButton:hover {
                background-color: #DDA15E;  /* Slightly deeper, same tone as base */
                color: #1E1E1E;             /* Keep text readable */
            }
            QPushButton:pressed {
                background-color: #C68B3C;  /* Deeper, earthy shade on press */
                color: white;
            }
            QPushButton:disabled {
                background-color: #D3D3D3;  /* Neutral gray disabled */
                color: #7A7A7A;
            }
        """)
    
    def get_otp(self) -> str:
        return self.ui.otp_code_edit.text()

    def clear_otp(self):
        self.ui.otp_code_edit.clear()