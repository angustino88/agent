from src.mvc.task_schedule import Schedule


class TaskScheduleConfig:
    # Backend
    AGENT_HEARTBEAT = Schedule(
        type="interval", every=60, unit="seconds", run_at_start=True
    )  # also delivers queued session logs
    ACTIVITY_MONITOR = Schedule(type="interval", every=1, unit="seconds")
    SESSION_TIMER = Schedule(type="interval", every=1, unit="seconds")
    LOGIN_EVENT_MONITOR = Schedule(type="interval", every=1, unit="seconds")
    MONITORING_POLICY_SYNC = Schedule(type="interval", every=10, unit="minutes", run_at_start=True)
    USB_DEVICE_COLLECTOR = 5  # seconds between USB scans (collector thread)
    LICENSE_CHECKS = Schedule(
        type="interval", every=15, unit="minutes", run_at_start=True
    )  # each check has its own interval

    # Service gateway
    GATEWAY_TOKEN_REFRESH = Schedule(type="interval", every=30, unit="minutes")
    GATEWAY_CONFIG_SYNC = Schedule(type="interval", every=10, unit="minutes", run_at_start=True)

    # Local
    STORAGE_QUOTA_MONITOR = Schedule(type="interval", every=12, unit="hours", run_at_start=True)
    HEALTH_PING = Schedule(type="interval", every=10, unit="minutes")
    AUTO_UPDATE = Schedule(type="interval", every=60, unit="minutes", run_at_start=True)
