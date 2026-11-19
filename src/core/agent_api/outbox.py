"""Bounded on-disk outbox for session logs.

A session log is persisted before transmission and removed only after the backend acknowledged it
(``201`` created or ``200`` same event already stored). Retries reuse the same ``event_key``, which the
backend uses for idempotency. Terminal rejections (``409``/``422``) are dropped and counted, not retried
forever. The outbox never stores grants, keys or booking-code secrets beyond the session record itself.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

from . import errors
from .client import AgentApiClient
from .identity import atomic_write


class SessionLogOutbox:
    def __init__(self, path: str | os.PathLike, *, max_entries: int = 500, logger: Any = None):
        self._path = Path(path)
        self._max = max_entries
        self._logger = logger
        self._lock = threading.Lock()
        self.dropped = 0

    def _read(self) -> list[dict]:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return [e for e in data if isinstance(e, dict) and e.get("event_key")] if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def _write(self, entries: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(self._path, json.dumps(entries))

    def _log(self, level: str, message: str) -> None:
        if self._logger is not None:
            getattr(self._logger, level, self._logger.info)(message)

    def pending(self) -> list[dict]:
        with self._lock:
            return self._read()

    def add(self, entry: dict) -> None:
        with self._lock:
            entries = [e for e in self._read() if e.get("event_key") != entry.get("event_key")]
            entries.append(entry)
            overflow = len(entries) - self._max
            if overflow > 0:
                self.dropped += overflow
                self._log("warning", f"[SessionLogOutbox] full; dropped {overflow} oldest session log(s)")
                entries = entries[overflow:]
            self._write(entries)

    def _remove(self, event_key: str) -> None:
        with self._lock:
            self._write([e for e in self._read() if e.get("event_key") != event_key])

    def flush(self, client: AgentApiClient, *, limit: Optional[int] = None) -> int:
        """Send pending logs oldest first; stop at the first transient failure. Returns sent count."""
        sent = 0
        for entry in self.pending()[: limit or None]:
            key = str(entry.get("event_key"))
            try:
                client.record_session_log(entry)
            except (errors.Conflict, errors.ValidationFailed) as error:
                self.dropped += 1
                self._log("warning", f"[SessionLogOutbox] rejected event_key={key}: {error}")
                self._remove(key)
                continue
            except errors.AgentApiError as error:
                self._log("info", f"[SessionLogOutbox] deferred ({len(self.pending())} pending): {error}")
                break
            self._remove(key)
            sent += 1
        return sent
