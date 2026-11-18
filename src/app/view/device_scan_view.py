from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.DeviceScanGui import Ui_DeviceScanDialog


@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class DeviceScanView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_DeviceScanDialog()
        self.ui.setupUi(self)
        self._scan_active = False

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._ui_init()

    def _ui_init(self):
        self.ui.device_table.horizontalHeader().setStretchLastSection(True)
        self.ui.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #7D6A8E;   /* Muted mauve/purple */
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 12px;
                border: none;
            }

            QPushButton:hover {
                background-color: #6B5680;   /* Slightly darker mauve */
                color: #FFFFFF;
            }

            QPushButton:pressed {
                background-color: #4C3A5B;   /* Deep mauve */
                color: #FFFFFF;
            }

            QPushButton:disabled {
                background-color: #B0A2B8;   /* Soft pale mauve */
                color: #FFFFFF;
            }
        """)

        self.ui.push_btn.setStyleSheet("""
            QPushButton {
                background-color: #4DA8A0;   /* Muted teal */
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 12px;
                border: none;
            }

            QPushButton:hover {
                background-color: #3B8C87;   /* Slightly deeper teal */
                color: #FFFFFF;
            }

            QPushButton:pressed {
                background-color: #276662;   /* Deep teal for press */
                color: #FFFFFF;
            }

            QPushButton:disabled {
                background-color: #9CC3C0;   /* Soft pale teal */
                color: #FFFFFF;
            }
        """)

        self.ui.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A4E69;   /* Base muted indigo */
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 12px;
                border: none;
            }

            QPushButton:hover {
                background-color: #373B52;   /* Darker indigo on hover */
                color: #FFFFFF;
            }

            QPushButton:pressed {
                background-color: #222435;   /* Deep navy-indigo on press */
                color: #E0E0E0;              /* Slightly softer text */
            }

            QPushButton:disabled {
                background-color: #D3D3D3;   /* Neutral gray */
                color: #7A7A7A;
            }
        """)
    
    def set_scan_active(self):
        self._scan_active = True
        self.ui.scan_btn.setText('Stop')
        self.ui.scan_btn.setEnabled(True)
        self.ui.scan_btn.setStyleSheet("background-color: #e63946; color: white;")

    def set_scan_inactive(self):
        self._scan_active = False
        self.ui.scan_btn.setText('Scan')
        self.ui.scan_btn.setEnabled(True)
        self.ui.scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A4E69;   /* Base muted indigo */
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 12px;
                border: none;
            }

            QPushButton:hover {
                background-color: #373B52;   /* Darker indigo on hover */
                color: #FFFFFF;
            }

            QPushButton:pressed {
                background-color: #222435;   /* Deep navy-indigo on press */
                color: #E0E0E0;              /* Slightly softer text */
            }

            QPushButton:disabled {
                background-color: #D3D3D3;   /* Neutral gray */
                color: #7A7A7A;
            }
        """)

    def console(self, text: str):
        self.ui.console_output.appendPlainText(text)
    
    def clear_console_log(self):
        self.ui.console_output.clear()

    def update_device_table(self, dev_list):
        table = self.ui.device_table
        table.clearContents()
        table.setRowCount(len(dev_list))  # ensure table has enough rows

        for row, dev in enumerate(dev_list):
            name, dev_id, status = dev

            # Status
            status_text = "✅" if status else "❌"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 0, status_item)

            # Device Name
            table.setItem(row, 1, QTableWidgetItem(str(name)))

            # Device ID
            table.setItem(row, 2, QTableWidgetItem(str(dev_id)))

    def closeEvent(self, event):
        if self._scan_active:
            QMessageBox.warning(
                self,
                "Scan Active",
                "Please stop scanning before closing this window.",
                QMessageBox.Ok
            )
            event.ignore()
        else:
            event.accept()