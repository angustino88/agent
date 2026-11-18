"""Background monitoring: USB devices (reported to the backend), tool licenses (local warnings) and
shared-drive storage quota (local report)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.app.controller.monitoring.license_collector import (
    LicenseCollector,
    vector_license_client_source,
    warning_text,
)
from src.app.controller.monitoring.storage_quota_monitor import StorageQuotaMonitor
from src.app.controller.monitoring.usb_device_collector import UsbDeviceCollector
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.core.agent_api import errors as agent_errors
from src.core.monitoring import USB_COLLECTOR_KEY, DeviceObservationReporter
from src.mvc.base_controller import BaseController
from src.mvc.task_schedule import task


class MonitoringCtrl(BaseController):
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._usb_reporter: Optional[DeviceObservationReporter] = None
        self._usb_collector: Optional[UsbDeviceCollector] = None
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

        self._usb_reporter = self._backend_model.device_observation_reporter(USB_COLLECTOR_KEY)
        self._usb_collector = UsbDeviceCollector(self._usb_reporter, TaskScheduleConfig.USB_DEVICE_COLLECTOR)
        self._usb_collector.device_connected.connect(
            lambda name, key: self._logger.info(f"[USB] Connected: {name} ({key})")
        )
        self._usb_collector.device_disconnected.connect(
            lambda name, key: self._logger.info(f"[USB] Disconnected: {name} ({key})")
        )
        self._usb_collector.exception.connect(self._log_exception)
        self._usb_collector.start()
        self._logger.info("[USB] Collector started")

        self._license_collector = LicenseCollector(
            {"Vector License Client": vector_license_client_source(app_settings.vector_license_client)},
            warn_days=app_settings.license_warn_days,
            logger=self._logger,
        )

        self.expose_get("licenses", lambda: self._license_collector.licenses if self._license_collector else [])
        self.expose_get("usb_devices", lambda: self._usb_collector.devices if self._usb_collector else [])
        self._initialized = True
        return self

    def _log_exception(self, e: Exception) -> None:
        self._logger.warning(f"[Monitoring] {e}")

    def shutdown(self):
        """Stop background threads (call on application exit)."""
        try:
            if self._usb_collector and self._usb_collector.isRunning():
                self._usb_collector.kill()
                self._usb_collector.wait()
                self._logger.info("[USB] Collector stopped")
        except Exception as e:
            self._logger.exception(f"[Monitoring] Shutdown error: {e}")

    @task(schedule=TaskScheduleConfig.MONITORING_POLICY_SYNC, heavy=True)
    def sync_monitoring_policy(self):
        """Pick up a new enrollment generation or interface catalog (cheap 304 when unchanged)."""
        if not self._initialized or not self._backend_model.is_enrolled:
            return
        try:
            policy = self._usb_reporter.refresh_policy()
            self._usb_collector.set_interface_catalog(policy.interface_names)
        except agent_errors.AgentApiError as e:
            self._logger.warning(f"[Monitoring] Policy refresh failed: {e}")

    @task(schedule=TaskScheduleConfig.LICENSE_COLLECTOR, heavy=True)
    def collect_licenses(self):
        """Read licenses, log what was found and warn about licenses that expire soon."""
        if not self._initialized:
            return
        licenses = self._license_collector.collect()
        for lic in licenses:
            self._logger.info(f"[Licenses] {lic.describe()}")
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
    def usb_collector(self) -> Optional[UsbDeviceCollector]:
        return self._usb_collector

    @property
    def license_collector(self) -> Optional[LicenseCollector]:
        return self._license_collector

    @property
    def storage_quota_monitor(self) -> Optional[StorageQuotaMonitor]:
        return self._storage_quota_monitor
