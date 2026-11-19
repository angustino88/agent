from src.mvc.slot_guard import slot_guard
from src.mvc.base_controller import BaseController

class ServerConfigCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._logger = None
        self._app_config = None
        self._app_settings = None
        self._credential_config = None
        self._backend_model = None
        self._gateway_model = None
        self._message_box = None
        self._server_config_view = None

    def init(self):
        if self._initialized:
            return self
        self._logger = self.model.logging_model.system_logger
        self._app_config = self.model.config_model.app_config
        self._app_settings = self.model.config_model.app_settings
        self._credential_config = self.model.config_model.credential_config
        self._backend_model = self.model.backend_model
        self._gateway_model = self.model.gateway_model
        self._message_box = self.view.message_box
        self._server_config_view = self.view.server_config_view
        self._server_config_view.ui.sync_btn.clicked.connect(self.sync_config)
        self._server_config_view.ui.cancel_btn.clicked.connect(self.cancel)
        self.view.main_window_view.ui.server_config_btn.clicked.connect(self.show_dialog)
        self._initialized = True
        return self

    #====================================================================
    # Private helpers
    #====================================================================
    def _handle_exception(self, e):
        self._logger.exception(e)
        self._message_box.error(e, parent=self._server_config_view)

    def _load_backend(self):
        identity = self._backend_model.identity
        self._server_config_view.set_backend(
            self._backend_model.frontend_url,
            identity.backend_url if identity else "(not enrolled)",
            identity.agent_uid if identity else "",
        )

    def _load_gateway(self):
        self._server_config_view.set_service_gateway(self._gateway_model.url, self._gateway_model.client.auth_value or "")

    def _load_otp_master_code(self):
        code = self._credential_config.otp_master_code
        self._server_config_view.set_otp_master_code(code)
    
    def _load_safe_mode(self):
        enabled = self._app_settings.safe_mode
        self._server_config_view.set_safe_mode(enabled)

    def _load_all(self):
        self._load_backend()
        self._load_gateway()
        self._load_otp_master_code()
        self._load_safe_mode()

    #====================================================================
    # Public / slot methods
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        if not self._initialized:
            self.init()
        self._load_all()
        self._server_config_view.exec()

    @slot_guard(on_exception=_handle_exception)
    def sync_config(self):
        self._gateway_model.sync_config(raise_on_error=True)
        self._backend_model.reload_identity()
        self._load_all()
        self._message_box.info("Configuration synchronized successfully", parent=self._server_config_view)

    @slot_guard(on_exception=_handle_exception)
    def refresh(self):
        self._load_all()
        self._message_box.info("Configuration reloaded.", parent=self._server_config_view)
    
    @slot_guard(on_exception=_handle_exception)
    def cancel(self):
        self._server_config_view.close()