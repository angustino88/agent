"""Windows single-instance process guard using a named mutex."""
from __future__ import annotations

import getpass
import sys
from enum import Enum

import win32api
import win32event
import win32security
import winerror

class InstanceScope(str, Enum):
    PER_USER = "per-user"
    ALL_USER = "all-user"

class SingleInstance:
    """
    Windows single-instance guard using a named mutex.

    Keep this object alive for the lifetime of the process.
    """

    def __init__(self, app_name: str, scope: InstanceScope = InstanceScope.PER_USER):
        self._app_name = app_name
        self._scope = scope
        self._mutex = None

    def _mutex_name(self) -> str:
        app = self._app_name
        if self._scope == InstanceScope.ALL_USER:
            # Global\ => across sessions/users (may be restricted by policy in some environments)
            return f"Global\\{app}_SingleInstance"
        try:
            user = getpass.getuser()
            sid = win32security.LookupAccountName(None, user)[0]
            user_identity = win32security.ConvertSidToStringSid(sid)
        except Exception:
            user_identity = getpass.getuser()
        return f"{app}_SingleInstance_{user_identity}"

    def acquire_or_exit(self, enable: bool = True, exit_code: int = 0, on_already_exists=None) -> bool:
        if not enable:
            return True

        self._mutex = win32event.CreateMutex(None, False, self._mutex_name())
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            if callable(on_already_exists):
                on_already_exists()
            sys.exit(exit_code)
        return True