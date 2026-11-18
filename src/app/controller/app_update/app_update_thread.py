from PySide6.QtCore import Signal
from src.mvc.base_thread import BaseThread, EHandle
import threading

class UpdateCheckThread(BaseThread):
    done = Signal(object)          # PackageUpdate | None
    exception = Signal(Exception)

    def __init__(self, lab_api_model, current_version: str, logger):
        super().__init__(loop=False, e_handle=EHandle.ALL)
        self._lab_api_model = lab_api_model
        self._version = current_version
        self._logger = logger

    def run_user(self):
        try:
            pu = self._lab_api_model.check_package_update(self._version)
            self.done.emit(pu)
        except Exception as e:
            if self._logger:
                self._logger.exception("Update check failed")
            self.exception.emit(e)


class UpdateRunThread(BaseThread):
    success = Signal()
    failed = Signal(str)
    exception = Signal(Exception)
    download_progress = Signal(int)
    install_progress = Signal(int)
    update_progress = Signal(int, str)

    def __init__(self, updater, pkg, app_name, app_dir, download_token, logger):
        super().__init__(loop=False, e_handle=EHandle.ALL)
        self._updater = updater
        self._pkg = pkg
        self._app_name = app_name
        self._app_dir = app_dir
        self._download_token = download_token
        self._logger = logger
        self._cancelled = False
        self._cancel_lock = threading.Lock()

    # Public cooperative cancel
    def cancel(self):
        with self._cancel_lock:
            self._cancelled = True
        # BaseThread may implement interruption
        try:
            self.requestInterruption()
        except Exception:
            pass

    def _is_cancelled(self):
        if self.isInterruptionRequested():
            return True
        with self._cancel_lock:
            return self._cancelled

    def run_user(self):
        # Local helper to stop further work quickly
        class _Cancelled(Exception): ...

        def _check():
            if self._is_cancelled():
                raise _Cancelled()

        try:
            def dl(p):
                if not self._is_cancelled():
                    self.download_progress.emit(p)
                _check()
            def inst(p):
                if not self._is_cancelled():
                    self.install_progress.emit(p)
                _check()
            def upd(p, stage):
                if not self._is_cancelled():
                    self.update_progress.emit(p, stage or "")
                _check()

            _check()
            self._updater.update(
                package=self._pkg,
                app_name=self._app_name,
                app_dir=self._app_dir,
                download_token=self._download_token,
                download_progress=dl,
                install_progress=inst,
                update_progress=upd,
                verify_executable=True
            )
            if not self._is_cancelled():
                self.success.emit()
        except _Cancelled:
            # Silent: controller treats thread finish + cancel flag as cancel outcome
            if self._logger:
                self._logger.info("Update thread cancelled.")
        except Exception as e:
            if self._is_cancelled():
                if self._logger:
                    self._logger.info("Update thread cancelled (exception during shutdown).")
            else:
                if self._logger:
                    self._logger.exception("Update run failed")
                self.failed.emit(str(e))