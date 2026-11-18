import traceback
from datetime import datetime
from src.mvc.slot_guard import slot_guard
from src.mvc.base_controller import BaseController
from src.app.controller.device_scan.device_scan_thread import DeviceScanThread


class DeviceScanCtrl(BaseController):
    # ====================================================================
    # Initial methods
    # ====================================================================
    def __init__(self):
        """
        Initializes class instance
        """
        super().__init__()

    def init(self):
        """
        Additional initialization after the class instance has been initialized
        """
        self._logger = self.model.logging_model.system_logger
        self._device_scan_view = self.view.device_scan_view
        self._message_box = self.view.message_box
        self._device_scan_view.ui.refresh_btn.clicked.connect(self.refresh)
        self._device_scan_view.ui.scan_btn.toggled.connect(self.scan)
        self.view.main_window_view.ui.device_monitor_btn.clicked.connect(self.show_dialog)

    # ====================================================================
    # Private methods
    # ====================================================================
    def _handle_exception(self, e):
        """Shows error message to user."""
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        self._logger.exception(tb_str)
        self._message_box.exception(e)

    def _handle_scan_error(self, e):
        """Shows error message to user."""
        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        self._logger.exception(tb_str)
        self._device_scan_view.console(f"Error: {str(e)}")

    def _handle_device_insert(self, dev_name, dev_id):
        self._device_scan_view.console("🆕 Device Inserted:")
        self._device_scan_view.console(dev_id)
        self._device_scan_view.console(dev_name)
        self._device_scan_view.console("-" * 40)

    def _handle_device_removed(self, dev_name, dev_id):
        self._device_scan_view.console("🗑️ Device Removed:")
        self._device_scan_view.console(dev_id)
        self._device_scan_view.console(dev_name)
        self._device_scan_view.console("-" * 40)

    def _load_device_table(self):
        """Devices the USB collector currently reports to the backend (name, serial or instance key)."""
        devices = self.bus_request("get:usb_devices") or []
        self._device_scan_view.update_device_table(
            [(device.name, device.serial_number or device.observation_key, True) for device in devices]
        )

    def _start_scan(self):
        if hasattr(self, "_scan_thread") and self._scan_thread and self._scan_thread.isRunning():
            self._device_scan_view.console("⚠️ Scan already running.")
            return

        self._device_scan_view.clear_console_log()
        self._device_scan_view.set_scan_active()
        self._scan_thread = DeviceScanThread()
        self._scan_thread.device_inserted.connect(self._handle_device_insert)
        self._scan_thread.device_removed.connect(self._handle_device_removed)
        self._scan_thread.exception.connect(self._handle_exception)
        self._scan_thread.start()
        self._device_scan_view.console("🟢 Device scan started.")

    def _stop_scan(self):
        if hasattr(self, "_scan_thread") and self._scan_thread:
            if self._scan_thread.isRunning():
                self._scan_thread.kill()
                self._scan_thread.wait()
                self._device_scan_view.console("🔴 Device scan stopped.")
            else:
                self._device_scan_view.console("⚠️ No scan is running.")
            self._scan_thread = None
        self._device_scan_view.set_scan_inactive()

    # ====================================================================
    # Public methods
    # ====================================================================

    # ====================================================================
    # pyqtSlot method - which connected to UI signal
    # ====================================================================\
    def _print_licenses(self):
        """License checks and the licenses they found (configured in Lab Mango, or built in)."""
        view = self._device_scan_view
        now = datetime.now()
        states = self.bus_request("get:license_checks") or []
        view.console(f"License checks ({len(states)}):" if states else "License checks: none configured")
        for state in states:
            result = state.last_result
            status = "not run yet" if result is None else result.status
            if result is not None and result.error_message:
                status += f" - {result.error_message}"
            view.console(f"  {state.check.name} [{state.source}]: {status}")
            for lic in state.last_licenses:
                days = lic.days_left(now)
                view.console(f"    {lic.describe()}" + ("" if days is None else f", {days} days left"))
        view.console("-" * 40)

    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        self._load_device_table()
        self._device_scan_view.clear_console_log()
        self._print_licenses()
        self._device_scan_view.exec()

    @slot_guard(on_exception=_handle_exception)
    def refresh(self):
        self._load_device_table()

    @slot_guard(on_exception=_handle_scan_error)
    def scan(self, checked):
        if checked:
            self._start_scan()
        else:
            self._stop_scan()
