from PySide6.QtWidgets import QDialog
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.HealthInfoGui import Ui_HealthInfoDialog


@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class HealthInfoView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_HealthInfoDialog()
        self.ui.setupUi(self)

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._ui_init()

    def _ui_init(self):
        pass

    def console(self, text: str):
        self.ui.console_output.appendPlainText(text)
    
    def clear(self):
        self.ui.console_output.clear()