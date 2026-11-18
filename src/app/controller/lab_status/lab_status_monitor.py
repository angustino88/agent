import time
import pyautogui
from PySide6.QtCore import QObject, Signal
from datetime import datetime, timezone
from src.app.model.types.lab_status import LabStatus
from src.app.model.types.session_status import SessionStatus
from src.app.model.types.session_info import SessionInfo

class LabStatusMonitor(QObject):
    """
    Monitors lab session status based on user activity and booking reason.
    """

    status = Signal(tuple)
    exception = Signal(Exception)

    # Thresholds (in seconds)
    CURSOR_MOVE_THRESHOLD = 100  # pixels
    INACTIVE_THRESHOLD = 60      # seconds
    SYNC_STATUS_INTERVAL = 5 * 60  # seconds

    def __init__(self):
        super().__init__()
        self._last_cursor_pos = pyautogui.position()
        self._last_time = self._now_ms()
        self._lab_status = LabStatus.OFFLINE
        self._session_started = False
        self._is_maintenance = False
        self._inactive_time = 0
        self._sync_status_cnt = 0
        self._trigger_status_update = False
        self._inactive_start_ms: int | None = None
        self._inactive_since_ms: int | None = None

    def on_session_start(self, session_info: SessionInfo | None):
        self._session_started = True
        self._is_maintenance = session_info.is_maintenance if session_info else False
    
    def on_session_end(self):
        self._session_started = False

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def _check_cursor_active(self, cur_pos, last_pos) -> bool:
        delta_x = abs(last_pos[0] - cur_pos[0])
        delta_y = abs(last_pos[1] - cur_pos[1])
        return delta_x > self.CURSOR_MOVE_THRESHOLD or delta_y > self.CURSOR_MOVE_THRESHOLD

    def _calc_inactive_time(self):
        cur_cursor_pos = pyautogui.position()
        if not self._check_cursor_active(cur_cursor_pos, self._last_cursor_pos):
            cur_time = self._now_ms()
            if self._inactive_start_ms is None:
                self._inactive_start_ms = self._last_time
            delta_time = (cur_time - self._last_time) / 1000
            self._inactive_time = round(self._inactive_time + delta_time, 2)
            self._last_time = cur_time
        else:
            self._inactive_time = 0
            self._inactive_start_ms = None
            self._inactive_since_ms = None
            self._last_time = self._now_ms()
            self._last_cursor_pos = cur_cursor_pos

    def _eval_lab_status(self):
        if self._session_started:
            if self._is_maintenance:
                lab_status = LabStatus.MAINTAINING
                self._inactive_time = 0
                self._inactive_start_ms = None
                self._inactive_since_ms = None
            else:
                lab_status = LabStatus.ACTIVE
                self._calc_inactive_time()
                if self._inactive_time > self.INACTIVE_THRESHOLD:
                    lab_status = LabStatus.INACTIVE
                    if self._lab_status != LabStatus.INACTIVE and self._inactive_since_ms is None:
                        if self._inactive_start_ms is not None:
                            self._inactive_since_ms = int(self._inactive_start_ms + self.INACTIVE_THRESHOLD * 1000)
                        else:
                            self._inactive_since_ms = self._now_ms()
        else:
            lab_status = LabStatus.FREE
            self._inactive_time = 0
            self._inactive_start_ms = None
            self._inactive_since_ms = None

        if lab_status != self._lab_status:
            self._lab_status = lab_status
            self._trigger_status_update = True

    def _eval_sync_status(self):
        if self._sync_status_cnt > self.SYNC_STATUS_INTERVAL:
            self._trigger_status_update = True
            self._sync_status_cnt = 0
        else:
            self._sync_status_cnt += 1

    def _monitor(self):
        self._trigger_status_update = False
        self._eval_lab_status()
        self._eval_sync_status()
        if self._trigger_status_update:
            inactive_time_mins = int(self._inactive_time / 60)
            inactive_since_dt = (
                datetime.fromtimestamp(self._inactive_since_ms / 1000.0)
                if self._inactive_since_ms else None
            )
            self.status.emit((self._lab_status, inactive_time_mins, inactive_since_dt))
            self._trigger_status_update = False

    def run(self):
        try:
            self._monitor()
        except Exception as e:
            self.exception.emit(e)