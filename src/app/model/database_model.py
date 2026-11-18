from src.mvc.base_model import BaseModel
from src.mvc.task_schedule import task, Schedule
from .database.session_logger import SessionLogger

class DatabaseModel(BaseModel):
    def __init__(self):
        """
        Initializes class instance
        """
        super().__init__()

    def init(self):
        """
        Additional initialization after the class instance has been initialized
        """
        self._app_config = self.model.config_model.app_config
        self._session_logger = SessionLogger(self._app_config.LOG_DB_FILE)