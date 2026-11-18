import subprocess
from enum import Enum
from src.app.model.types.login_event import LoginEvent
from src.utils.remote_desktop import RemoteDesktop
from PySide6.QtCore import Signal
from PySide6.QtCore import QObject

class LoginEventMonitor(QObject):
    event = Signal(Enum)

    def __init__(self):
        super().__init__()
        self._last_remote_connected = False
        self._last_screen_locked = True
        self._event = LoginEvent.SCREEN_LOGOUT
        self._last_event = LoginEvent.SCREEN_LOGOUT

    @staticmethod
    def _screen_locked():
        process_name = 'LogonUI.exe'
        try:
            output = subprocess.check_output('TASKLIST', shell=True, text=True)
        except Exception as e:
            print(f"[LoginEventMonitor] Error checking screen lock: {e}")
            return False
        return process_name in output

    def run(self):
        remote_connected = RemoteDesktop.is_connected()
        screen_locked = self._screen_locked()

        if not self._last_remote_connected and remote_connected:
            self._event = LoginEvent.REMOTE_LOGIN
            self._last_remote_connected = True
        elif self._last_remote_connected and not remote_connected:
            self._event = LoginEvent.REMOTE_LOGOUT
            self._last_remote_connected = False
        elif not remote_connected and self._last_screen_locked and not screen_locked:
            self._event = LoginEvent.SCREEN_LOGIN
            self._last_screen_locked = False
        elif not remote_connected and not self._last_screen_locked and screen_locked:
            self._event = LoginEvent.SCREEN_LOGOUT
            self._last_screen_locked = True

        if self._event != self._last_event:
            self.event.emit(self._event)
            self._last_event = self._event