import traceback
from typing import Optional
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task, Schedule
from src.mvc.base_controller import BaseController
from src.app.controller.health_check.health_check_thread import HealthCheckThread
from src.app.model.config.task_schedule_config import TaskScheduleConfig

class HealthCheckCtrl(BaseController):
    #====================================================================
    # Initial methods
    #====================================================================
    def __init__(self):
        """
        Controller for on-demand / periodic health checks.
        Thread is created lazily and reused while running.
        """
        super().__init__()
        self._initialized = False
        self._logger = None
        self._health_info_view = None
        self._lab_api_model = None
        self._lab_session_controller = None
        self._health_check_thread: Optional[HealthCheckThread] = None

    def init(self):
        if self._initialized:
            return self
        self._logger = self.model.logging_model.system_logger
        self._health_info_view = self.view.health_info_view
        self._lab_api_model = self.model.lab_api_model
        self.view.main_window_view.ui.health_check_btn.clicked.connect(self.show_dialog)
        self._initialized = True
        return self

    #====================================================================
    # Private methods
    #====================================================================
    def _handle_exception(self, e: Exception):
        tb_str = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
        # Log full traceback but show concise line in UI
        self._logger.exception(tb_str)
        if self._health_info_view:
            self._health_info_view.console(f"Error: {e}")

    def _is_thread_running(self) -> bool:
        return (
            self._health_check_thread is not None
            and self._health_check_thread.isRunning()
        )

    def _start_thread(self, clear_view: bool = True):
        # Reuse if already running
        if self._is_thread_running():
            if clear_view:
                self._health_info_view.console("Health check already running.")
            return

        if clear_view:
            self._health_info_view.clear()

        self._health_check_thread = HealthCheckThread(
            self._lab_api_model,
            self.model.runner,
            self.view.runner,
            self.bus_request("get:runner")
        )
        self._health_check_thread.exception.connect(self._handle_exception)
        self._health_check_thread.health_info.connect(self._health_info_view.console)
        self._health_check_thread.finished.connect(self._on_thread_finished)
        self._health_check_thread.start()
        self._health_info_view.show()
        self._health_info_view.console("Health check started.")

    def _on_thread_finished(self):
        # Thread object will be discarded after finish to allow a clean restart
        self._health_info_view.console("Health check finished.")
        self._health_check_thread = None

    def _stop_thread(self, announce: bool = True):
        if not self._is_thread_running():
            if announce and self._health_info_view:
                self._health_info_view.console("No health check is running.")
            return
        try:
            self._health_check_thread.kill()
            self._health_check_thread.wait()
            if announce and self._health_info_view:
                self._health_info_view.console("Health check stopped.")
        except Exception as e:
            self._handle_exception(e)
        finally:
            self._health_check_thread = None

    #====================================================================
    # Public methods
    #====================================================================
    def shutdown(self):
        """Call on application exit."""
        self._stop_thread(announce=False)

    @task(schedule=TaskScheduleConfig.HEALTH_PING, heavy=False)
    def periodic_health_ping(self):
        if not self._initialized:
            return
        try:
            # Avoid launching full thread; perform a quick backend check
            alive = False
            try:
                alive = self._lab_api_model.check_backend_alive()
            except Exception:
                pass
            return "Backend alive" if alive else "Backend not responding"
        except Exception as e:
            self._handle_exception(e)

    #====================================================================
    # pyqtSlot methods
    #====================================================================
    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        """Open dialog and start a fresh health check run."""
        self._start_thread(clear_view=True)

    @slot_guard(on_exception=_handle_exception)
    def rerun(self):
        """Explicit rerun requested by user."""
        self._stop_thread(announce=False)
        self._start_thread(clear_view=True)

    @slot_guard(on_exception=_handle_exception)
    def stop(self):
        """Stop current health check (if running)."""
        self._stop_thread()

    @slot_guard(on_exception=_handle_exception)
    def append_session_info(self):
        """
        Append latest session info line (without restarting a full check).
        Useful if UI wants a quick refresh portion.
        """
        if not self._initialized:
            return
        try:
            sess = self.bus_request("get:session_info")
            self._health_info_view.console(f"Session: {sess}")
        except Exception as e:
            self._handle_exception(e)
