from PySide6.QtWidgets import QDialog
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.ServerConfigGui import Ui_ServerConfigDialog

@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class ServerConfigView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_ServerConfigDialog()
        self.ui.setupUi(self)

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._ui_init()

    def _ui_init(self):
        pass                                  
    
    def set_prod_server(self, frontend_url, backend_url, api_key):
        self.ui.prod_frontend_edit.setText(frontend_url)
        self.ui.prod_backend_edit.setText(backend_url)
        self.ui.prod_apikey_edit.setText(api_key)
    
    def get_prod_server(self):
        return {
            'frontend_url': self.ui.prod_frontend_edit.text(),
            'backend_url': self.ui.prod_backend_edit.text(),
            'api_key': self.ui.prod_apikey_edit.text()
        }
    
    def set_service_gateway(self, backend_url, api_key):
        self.ui.service_gateway_backend_edit.setText(backend_url)
        self.ui.service_gateway_token_edit.setText(api_key)
    
    def get_service_gateway(self):
        return {
            'backend_url': self.ui.service_gateway_backend_edit.text(),
            'token': self.ui.service_gateway_token_edit.text()
        }
    
    def set_otp_master_code(self, code):
        self.ui.otp_master_code_edit.setText(code)
    
    def get_otp_master_code(self):
        return self.ui.otp_master_code_edit.text()

    def set_safe_mode(self, enabled: bool):
        self.ui.safe_mode_edit.setText(str(enabled))
    
    def get_safe_mode(self):
        return self.ui.safe_mode_edit.text()