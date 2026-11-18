from src.mvc.task_schedule import Schedule

class TaskScheduleConfig:
    HEALTH_PING           = Schedule(type="interval", every=10, unit='minutes')
    AUTO_UPDATE           = Schedule(type="interval", every=60, unit='minutes', run_at_start=True)
    USER_STORAGE_MONITOR  = Schedule(type="interval", every=12, unit='hours',   run_at_start=True)
    COMPUTER_INFO_MONITOR = Schedule(type="interval", every=4,  unit='hours',   run_at_start=True)
    DEVICE_STATE_REFRESH  = Schedule(type="interval", every=60, unit='seconds', run_at_start=True)
    LAB_SESSION_MONITOR   = Schedule(type="interval", every=1,  unit='seconds')
    LAB_STATUS_MONITOR    = Schedule(type="interval", every=1,  unit='seconds')
    LOGIN_STATE_MONITOR   = Schedule(type="interval", every=1,  unit='seconds')
    REFRESH_SERVICE_GATEWAY_TOKEN  = Schedule(type="interval", every=30, unit='minutes')
    SYNC_SERVICE_GATEWAY           = Schedule(type="interval", every=10, unit='minutes', run_at_start=True)
    PHYSICAL_DEVICE_MONITOR = 5 # seconds