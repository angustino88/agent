from PySide6.QtWidgets import QDialog
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.SessionInfoGui import Ui_SessionInfoDialog


@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class SessionInfoView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_SessionInfoDialog()
        self.ui.setupUi(self)

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._ui_init()

    def update_btn_style(self):
        self.ui.end_booking_btn.setStyleSheet("""
            QPushButton {
                background-color: #C96A77;   /* Muted rose base */
                color: #FFFFFF;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #B05B67;   /* Slightly deeper rose */
            }
            QPushButton:pressed {
                background-color: #8A444E;   /* Deep muted rose */
            }
            QPushButton:disabled {
                background-color: #D9A4AC;   /* Soft pale rose */
                color: #FFFFFF;
            }
        """)

        self.ui.refresh_booking_btn.setStyleSheet("""
            QPushButton {
                background-color: #5D6390;   /* Muted indigo-blue */
                color: #FFFFFF;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4A4E7B;   /* Slightly darker */
            }
            QPushButton:pressed {
                background-color: #333758;   /* Deep indigo */
            }
            QPushButton:disabled {
                background-color: #B0B3C9;   /* Pale muted indigo */
                color: #FFFFFF;
            }
        """)

        self.ui.update_booking_btn.setStyleSheet("""
            QPushButton {
                background-color: #42A39B;   /* Muted teal */
                color: #FFFFFF;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #379187;   /* Slightly deeper teal */
            }
            QPushButton:pressed {
                background-color: #276B66;   /* Deep teal */
            }
            QPushButton:disabled {
                background-color: #8FC4BF;   /* Pale teal */
                color: #FFFFFF;
            }
        """)

    def _ui_init(self):
        self.update_btn_style()
        self.clear_info()
    
    @staticmethod
    def _format(value) -> str:
        return value.strftime("%m/%d/%Y, %H:%M") if value else "-"

    def set_session(self, session, ends_at=None):
        """Show a :class:`RemoteSession`; ``ends_at`` overrides the booking end (temporary sessions)."""
        self.ui.booking_number_edit.setText(session.booking_code or "-")
        self.ui.remote_user_edit.setText(session.remote_user)
        self.ui.remote_ip_edit.setText(session.remote_ip)
        self.ui.remote_computer_edit.setText(session.remote_computer)
        self.ui.from_datetime_edit.setText(self._format(session.starts_at))
        self.ui.to_datetime_edit.setText(self._format(ends_at or session.ends_at))
        self.set_minutes_left(0)

    def clear_info(self):
        self.ui.booking_number_edit.clear()
        self.ui.remote_user_edit.clear()
        self.ui.remote_ip_edit.clear()
        self.ui.remote_computer_edit.clear()
        self.ui.from_datetime_edit.clear()
        self.ui.to_datetime_edit.clear()
        self.ui.hour_lcdNumber.display(0)
        self.ui.minute_lcdNumber.display(0)

    def set_ends_at(self, ends_at):
        self.ui.to_datetime_edit.setText(self._format(ends_at))

    def set_minutes_left(self, minutes_left: int):
        hours, minutes = divmod(int(minutes_left), 60)
        self.ui.hour_lcdNumber.display(hours)
        self.ui.minute_lcdNumber.display(minutes)

    def show_dialog(self):
        self.show()
        if self.isMinimized():
            self.showNormal()     # Restore from minimized

        self.raise_()             # Bring to front
        self.activateWindow()     # Give focus
        
    def keyPressEvent(self, event):
        event.ignore()
