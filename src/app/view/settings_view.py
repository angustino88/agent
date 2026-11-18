from PySide6.QtWidgets import QDialog
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.SettingsGui import Ui_SettingsDialog

@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class SettingsView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._ui_init()

    def _ui_init(self):
        self.ui.debug_enabled_combo.addItems(["True", "False"])                                    
    
    def set_app_debug_enabled(self, enabled):
        self.ui.debug_enabled_combo.setCurrentText("True" if enabled else "False")
    
    def get_app_debug_enabled(self):
        return self.ui.debug_enabled_combo.currentText() == "True"
    
    def set_sharing_dir(self, dir):
        self.ui.sharing_dir_edit.setText(dir)
    
    def get_sharing_dir(self):
        return self.ui.sharing_dir_edit.text()