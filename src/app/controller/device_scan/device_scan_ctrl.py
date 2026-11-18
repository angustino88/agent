"""Device Scan dialog: expected devices of this computer, a live device log, and discovery.

* The table lists the equipment expected on this computer (from the monitoring policy) with its
  registered PnP ID and whether it is connected now.
* *Scan* logs devices as they are plugged in or removed, with their PnP instance path, the value a
  coordinator registers on the inventory unit.
* *Push* sends the connected USB devices once as a discovery snapshot; they then appear in Lab
  Monitoring, where a coordinator can register a device with *Link*.
"""

import traceback

from PySide6.QtCore import QTimer

from src.mvc.base_controller import BaseController
from src.mvc.slot_guard import slot_guard

LIVE_REFRESH_MS = 1000


class DeviceScanCtrl(BaseController):
    def __init__(self):
        super().__init__()
        self._live_timer = None
        self._last_seen: dict[str, str] = {}

    def init(self):
        self._logger = self.model.logging_model.system_logger
        self._device_scan_view = self.view.device_scan_view
        self._message_box = self.view.message_box
        ui = self._device_scan_view.ui
        ui.refresh_btn.clicked.connect(self.refresh)
        ui.scan_btn.toggled.connect(self.scan)
        ui.push_btn.clicked.connect(self.push_discovery)
        ui.push_btn.setToolTip("Send the connected USB devices once, so they can be registered in Lab Mango")
        self.view.main_window_view.ui.device_monitor_btn.clicked.connect(self.show_dialog)
        self._live_timer = QTimer(self._device_scan_view)
        self._live_timer.setInterval(LIVE_REFRESH_MS)
        self._live_timer.timeout.connect(self._log_changes)

    # ------------------------------------------------------------------ helpers

    def _handle_exception(self, e):
        self._logger.exception("".join(traceback.format_exception(type(e), e, e.__traceback__)))
        self._message_box.exception(e)

    def _collector(self):
        collector = self.bus_request("get:device_collector")
        if collector is None:
            raise RuntimeError("Device monitoring is not running.")
        return collector

    def _load_device_table(self):
        collector = self._collector()
        watch_list = collector.watch_list
        connected = {d.pnp_id for d in collector.watched_devices}
        rows = []
        for expected in watch_list.expected if watch_list else ():
            pnp_ids = [h.value for h in expected.hardware_ids if h.kind == "pnp_id"]
            if not pnp_ids:
                rows.append((expected.name, "(no PnP ID registered)", False))
            for pnp_id in pnp_ids:
                rows.append((expected.name, pnp_id, pnp_id in connected))
        self._device_scan_view.update_device_table(rows)
        if watch_list is None:
            self._device_scan_view.console("Waiting for the monitoring policy from Lab Mango…")

    def _present(self) -> dict[str, str]:
        return {d.pnp_id: d.name for d in self._collector().present_devices}

    def _log_changes(self):
        try:
            now = self._present()
        except RuntimeError:
            return
        view = self._device_scan_view
        for pnp_id in sorted(now.keys() - self._last_seen.keys()):
            view.console(f"Plugged in: {now[pnp_id]}")
            view.console(f"  {pnp_id}")
        for pnp_id in sorted(self._last_seen.keys() - now.keys()):
            view.console(f"Removed: {self._last_seen[pnp_id]}")
            view.console(f"  {pnp_id}")
        self._last_seen = now

    # ------------------------------------------------------------------ slots

    @slot_guard(on_exception=_handle_exception)
    def show_dialog(self):
        self._load_device_table()
        self._device_scan_view.clear_console_log()
        self._device_scan_view.exec()

    @slot_guard(on_exception=_handle_exception)
    def refresh(self):
        self._load_device_table()

    @slot_guard(on_exception=_handle_exception)
    def scan(self, checked):
        view = self._device_scan_view
        if checked:
            view.clear_console_log()
            self._last_seen = self._present()
            view.console(f"Live scan started: {len(self._last_seen)} devices connected.")
            view.console("Plug the device in or out; its PnP instance path is shown below.")
            view.set_scan_active()
            self._live_timer.start()
        else:
            self._live_timer.stop()
            view.set_scan_inactive()
            view.console("Live scan stopped.")

    @slot_guard(on_exception=_handle_exception)
    def push_discovery(self):
        self._collector()
        self.bus_emit("devices:discover")
        self._device_scan_view.console(
            "Discovery requested: the connected USB devices are sent with the next scan. "
            "Register a device in Lab Monitoring with Link."
        )
