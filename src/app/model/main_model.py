from src.mvc.base_model import BaseMainModel
from src.mvc.event_bus import EventBus
from src.app.model.logging_model import LoggingModel
from src.app.model.database_model import DatabaseModel
from src.app.model.config_model import ConfigModel
from src.app.model.computer_model import ComputerModel
from src.app.model.lab_api_model import LabApiModel

class MainModel(BaseMainModel):
    def __init__(self, bus: EventBus, max_workers: int = 4):
        super().__init__(bus, max_workers)

    def _setup(self):
        self.config_model  = self._make(ConfigModel)
        self._make_runtime_dirs(
            self.config_model.app_config.LOCAL_APP_DIR,
            self.config_model.app_config.SHARED_APP_DIR,
            self.config_model.app_config.LOG_DIR,
            self.config_model.app_config.SETTINGS_DIR,
            self.config_model.app_config.INFO_DIR,
            self.config_model.app_config.SHARED_INFO_DIR,
        )
        self.logging_model  = self._make(LoggingModel)
        self.database_model = self._make(DatabaseModel)
        self.computer_model = self._make(ComputerModel)
        self.lab_api_model  = self._make(LabApiModel)

    def _configure(self):
        pass