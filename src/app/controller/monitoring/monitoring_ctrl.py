"""Background monitoring: expected devices by PnP ID (reported to the backend), license checks and
shared-drive storage quota (local report)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.app.controller.monitoring.license_collector import LicenseCollector, warning_text
from src.app.controller.monitoring.storage_quota_monitor import StorageQuotaMonitor
from src.app.controller.monitoring.pnp_device_collector import PnpDeviceCollector
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.core.agent_api import errors as agent_errors
from src.core.monitoring import DISCOVERY_COLLECTOR_KEY, PNP_COLLECTOR_KEY, DeviceObservationReporter, WatchList
from src.mvc.base_controller import BaseController
from src.mvc.task_schedule import task


class MonitoringCtrl(BaseController):
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._device_reporter: Optional[DeviceObservationReporter] = None
        self._device_collector: Optional[PnpDeviceCollector] = None
        self._storage_quota_monitor: Optional[StorageQuotaMonitor] = None
        self._license_collector: Optional[LicenseCollector] = None

    def init(self):
        if self._initialized:
            return self
        app_config = self.model.config_model.app_config
        app_settings = self.model.config_model.app_settings
        user_quota_config = self.model.config_model.user_quota_config
        self._logger = self.model.logging_model.system_logger
        self._backend_model = self.model.backend_model

        self._storage_quota_monitor = StorageQuotaMonitor(
            app_settings.sharing_root_dir,
            app_config.USER_STORAGE_INFO_FILE,
            default_quota_gb=user_quota_config.default_quota,
            user_quotas_gb=user_quota_config.user_quotas,
        )
        self._storage_quota_monitor.exception.connect(self._log_exception)

        self._device_reporter = self._backend_model.device_observation_reporter(PNP_COLLECTOR_KEY)
        self._device_collector = PnpDeviceCollector(
            self._device_reporter,
            self._backend_model.device_observation_reporter(DISCOVERY_COLLECTOR_KEY),
            TaskScheduleConfig.PNP_DEVICE_SCAN,
        )
        self._device_collector.watched_connected.connect(
            lambda name, pnp_id: self._logger.info(f"[Devices] Connected: {name} ({pnp_id})")
        )
        self._device_collector.watched_disconnected.connect(
            lambda name, pnp_id: self._logger.info(f"[Devices] Disconnected: {name} ({pnp_id})")
        )
        self._device_collector.exception.connect(self._log_exception)
        self._device_collector.start()
        self._logger.info("[Devices] Collector started")

        self._license_collector = LicenseCollector(self._backend_model, app_settings, logger=self._logger)

        self.expose_get("licenses", lambda: self._license_collector.licenses if self._license_collector else [])
        self.expose_get("license_checks", lambda: self._license_collector.states if self._license_collector else [])
        self.expose_get("device_collector", lambda: self._device_collector)
        self.bus_subscribe("devices:discover", lambda _: self.request_discovery())
        self._initialized = True
        return self

    def _log_exception(self, e: Exception) -> None:
        self._logger.warning(f"[Monitoring] {e}")

    def shutdown(self):
        """Stop background threads (call on application exit)."""
        try:
            if self._device_collector and self._device_collector.isRunning():
                self._device_collector.kill()
                self._device_collector.wait()
                self._logger.info("[Devices] Collector stopped")
        except Exception as e:
            self._logger.exception(f"[Monitoring] Shutdown error: {e}")

    @task(schedule=TaskScheduleConfig.MONITORING_POLICY_SYNC, heavy=True)
    def sync_monitoring_policy(self):
        """Pick up the watch list (expected devices) and a new enrollment generation; 304 when unchanged."""
        if not self._initialized or not self._backend_model.is_enrolled:
            return
        try:
            policy = self._device_reporter.refresh_policy()
        except agent_errors.AgentApiError as e:
            self._logger.warning(f"[Monitoring] Policy refresh failed: {e}")
            return
        watch_list = WatchList.from_policy(policy.expected_devices)
        if watch_list != self._device_collector.watch_list:
            self._logger.info(
                f"[Devices] Watching {len(watch_list.expected)} expected device(s)"
                + (f", {len(watch_list.unregistered)} without a registered PnP ID" if watch_list.unregistered else "")
            )
        self._device_collector.set_watch_list(watch_list)

    def request_discovery(self) -> None:
        """Admin action: send the connected USB devices once so a coordinator can register them."""
        if self._device_collector is not None:
            self._device_collector.request_discovery()
            self._logger.info("[Devices] Discovery snapshot requested")

    @task(schedule=TaskScheduleConfig.LICENSE_CHECKS, heavy=True)
    def run_license_checks(self):
        """Refresh the configured checks, run the due ones and warn about licenses that expire soon.

        Runs every 15 minutes; each check has its own interval (6 hours for the Vector preset).
        """
        if not self._initialized:
            return
        self._license_collector.sync_checks()
        self._license_collector.run_due()
        self._backend_model.flush_license_reports()
        now = datetime.now()
        for lic in self._license_collector.due_warnings(now):
            text = warning_text(lic, now)
            self._logger.warning(f"[Licenses] {text}")
            self.view.show_notification(text, duration="long")

    @task(schedule=TaskScheduleConfig.STORAGE_QUOTA_MONITOR, heavy=True)
    def measure_storage_quota(self):
        if self._initialized:
            self._storage_quota_monitor.run()

    @property
    def device_collector(self) -> Optional[PnpDeviceCollector]:
        return self._device_collector

    @property
    def license_collector(self) -> Optional[LicenseCollector]:
        return self._license_collector

    @property
    def storage_quota_monitor(self) -> Optional[StorageQuotaMonitor]:
        return self._storage_quota_monitor
