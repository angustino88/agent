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
    
    def set_info(self, info):
        self.ui.booking_number_edit.setText(str(getattr(info, "booking_code", "")))
        self.ui.remote_user_edit.setText(str(getattr(info, "remote_user", "")))
        self.ui.remote_ip_edit.setText(str(getattr(info, "remote_ip", "")))
        self.ui.remote_computer_edit.setText(str(getattr(info, "remote_computer", "")))
        from_dt = getattr(info, "from_datetime", None)
        to_dt = getattr(info, "to_datetime", None)
        self.ui.from_datetime_edit.setText(
            from_dt.strftime("%m/%d/%Y, %H:%M") if from_dt else "None"
        )
        self.ui.to_datetime_edit.setText(
            to_dt.strftime("%m/%d/%Y, %H:%M") if to_dt else "None"
        )
        # Optionally set timeleft if info has it
        timeleft = getattr(info, "timeleft", None)
        if timeleft is not None:
            self.set_timeleft(timeleft)
        else:
            self.set_timeleft(0)

    def clear_info(self):
        self.ui.booking_number_edit.clear()
        self.ui.remote_user_edit.clear()
        self.ui.remote_ip_edit.clear()
        self.ui.remote_computer_edit.clear()
        self.ui.from_datetime_edit.clear()
        self.ui.to_datetime_edit.clear()
        self.ui.hour_lcdNumber.display(0)
        self.ui.minute_lcdNumber.display(0)
    
    def set_to_datetime(self, to_datetime: str):
        self.ui.to_datetime_edit.setText(
            to_datetime.strftime("%m/%d/%Y, %H:%M") if to_datetime else "None"
        )

    def set_timeleft(self, timeleft: int):
        hour, minute = divmod(int(timeleft), 60)
        self.ui.hour_lcdNumber.display(hour)
        self.ui.minute_lcdNumber.display(minute)
    
    def show_dialog(self):
        self.show()
        if self.isMinimized():
            self.showNormal()     # Restore from minimized

        self.raise_()             # Bring to front
        self.activateWindow()     # Give focus
        
    def keyPressEvent(self, event):
        event.ignore()
