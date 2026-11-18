from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QMessageBox
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.mvc.icon import IconMixin
from src.app.view.widgets.MainWindowGui import Ui_MainWindow

@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class MainWindowView(QMainWindow, BaseView, IconMixin, metaclass=metaclass_factory(QMainWindow, BaseView)):
    def __init__(self):
        super().__init__()
        IconMixin.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    def init(self):
        self._app_config  = self.model.config_model.app_config
        self._computer_model = self.model.computer_model
        self._computer_name = self._computer_model.computer_name
        self._computer_ip = self._computer_model.computer_ip
        self._ui_init()
    
    def _ui_init(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.ui.computer_name_edit.setText(self._computer_name)
        self.ui.computer_ip_edit.setText(self._computer_ip)
        self.ui.device_icon_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }

            QPushButton:hover {
                background-color: transparent;
            }

            QPushButton:pressed {
                background-color: transparent;
            }
        """)

    #=========================================================================
    # Public
    #=========================================================================
    def set_admin_enabled(self, enabled):
        self.ui.check_update_action.setEnabled(enabled)
        self.ui.settings_btn.setEnabled(enabled)
        self.ui.server_config_btn.setEnabled(enabled)
        self.ui.device_monitor_btn.setEnabled(enabled)
        self.ui.log_check_btn.setEnabled(enabled)
        self.ui.health_check_btn.setEnabled(enabled)
 
    def restore_and_focus_window(self):
        if self.isMinimized() or not self.isVisible():
            self.showNormal()
            self.activateWindow()
            self.raise_()

    def closeEvent(self, event):
        """
        Override exit method of QMainWindow
        """
        if not self._app_config.SYS_TRAY_ENABLED:
            reply = QMessageBox.question(self, 'Quit', 'Are you sure you want to quit?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                    event.accept()
            else:
                event.ignore()
        else:
            self.hide()
            event.ignore()