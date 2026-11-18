import logging
import os
import contextlib
from datetime import datetime
from logging import Logger
from typing import Optional

from src.utils.path import PathUtil
from src.mvc.base_model import BaseModel
from src.app.model.database.session_logger import SessionLogger

class LoggingModel(BaseModel):
    """
    Centralized logging manager for system, update, and session logs.
    Provides consistent log formatting, file handling, and session DB logging.
    """

    _UPDATE_LOG_PATTERN = "update_v{ver}_{ts}.log"
    _UPDATE_LOG_FAILED_SUFFIX = "_failed"

    def __init__(self):
        super().__init__()
        self._system_logger: Optional[Logger] = None
        self._update_logger: Optional[Logger] = None
        self._session_logger: Optional[SessionLogger] = None

        self._system_log_file: Optional[str] = None
        self._update_log_file: Optional[str] = None
        self._app_config = None

    def init(self):
        """
        Perform post-construction initialization.
        """
        self._app_config = self.model.config_model.app_config
        self._app_config_dynamic = self.model.config_model.app_config_dynamic
        self._setup_system_logger()
        self._setup_session_logger()

    def _create_logger(self, name: str, log_file: str, fmt: str) -> Logger:
        """
        Create and return a logger with the given name and file.
        Ensures handlers are not duplicated.
        """
        formatter = logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S")
        handler = logging.FileHandler(log_file)
        handler.setFormatter(formatter)

        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers if logger is re-initialized
        if not logger.handlers:
            logger.addHandler(handler)

        return logger

    def _setup_system_logger(self):
        self._system_log_file = self._app_config.SYS_LOG_FILE
        self._system_logger = self._create_logger(
            "system_logger",
            self._system_log_file,
            "[%(asctime)s] [%(levelname)s] %(message)s"
        )

    def _setup_update_logger(self, version: str, file_path: Optional[str] = None):
        """
        (Re)bind update logger to a file.
        If file_path not provided, use a basic versioned name without timestamp.
        """
        if file_path is None:
            # fallback simple name (no timestamp)
            file_path = PathUtil.join(self._app_config.LOG_DIR, f"update_v{version}.log")
        self._update_log_file = file_path
        self._update_logger = self._create_logger(
            f"update_logger.v{version}",
            file_path,
            "%(asctime)s %(levelname)s %(message)s"
        )

    def _setup_session_logger(self):
        self._session_logger = SessionLogger(self._app_config.LOG_DB_FILE)
        self._session_logger.create_session_log()
        self._session_logger.create_status_log()

    def export_status_log(self):
        if self._session_logger:
            self._session_logger.export_status_log(self._app_config.STATUS_LOG_FILE)

    def export_session_log(self):
        if self._session_logger:
            self._session_logger.export_session_log(self._app_config.SESSION_LOG_FILE)

    def clear_system_log(self):
        """Truncate the system log file."""
        if self._system_log_file:
            open(self._system_log_file, "w").close()

    # ---------------- Update session lifecycle ----------------
    def begin_update_session(self, target_version: str):
        """
        Start an update attempt.
        Creates a new timestamped log file:
          update_v{target_version}_{YYYYmmdd_HHMMSS}.log
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self._UPDATE_LOG_PATTERN.format(ver=target_version, ts=ts)
        file_path = PathUtil.join(self._app_config.LOG_DIR, filename)
        self._setup_update_logger(target_version, file_path=file_path)
        if self._update_logger:
            self._update_logger.info(f"=== BEGIN UPDATE target={target_version} ts={ts} ===")
        return file_path

    def finalize_update_session(self, target_version: str, success: bool):
        """
        Mark current update attempt success/failure.
        If failure: rename file with _failed suffix.
        (Old logs are retained; no pruning.)
        """
        if not self._update_log_file:
            return
        src = self._update_log_file
        if not os.path.isfile(src):
            return
        if success:
            if self._update_logger:
                self._update_logger.info("=== UPDATE SUCCESS ===")
        else:
            failed_path = self._append_failed_suffix(src)
            if failed_path != src:
                with contextlib.suppress(Exception):
                    # Close handler before rename
                    if self._update_logger:
                        for h in list(self._update_logger.handlers):
                            if isinstance(h, logging.FileHandler):
                                h.flush()
                                h.close()
                                self._update_logger.removeHandler(h)
                    os.replace(src, failed_path)
                    # Rebind logger to the failed file (continue logging if needed)
                    self._setup_update_logger(target_version, file_path=failed_path)
                    if self._update_logger:
                        self._update_logger.info("=== UPDATE FAILED ===")

    def _append_failed_suffix(self, path: str) -> str:
        if path.endswith(".log"):
            base, ext = os.path.splitext(path)
            if not base.endswith(self._UPDATE_LOG_FAILED_SUFFIX):
                return f"{base}{self._UPDATE_LOG_FAILED_SUFFIX}{ext}"
        return path

    @property
    def system_log_file(self) -> Optional[str]:
        return self._system_log_file

    @property
    def update_log_file(self) -> Optional[str]:
        return self._update_log_file

    @property
    def session_logger(self) -> Optional[SessionLogger]:
        return self._session_logger

    @property
    def system_logger(self) -> Logger:
        return self._system_logger

    @property
    def update_logger(self) -> Optional[Logger]:
        return self._update_logger
