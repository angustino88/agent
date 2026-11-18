"""Reads tool licenses from every installed source and decides which expiry warnings to show."""

from __future__ import annotations

import threading
from datetime import date, datetime
from typing import Any, Callable, Iterable

from src.core.monitoring import LicenseObservation, expiring
from src.core.vendors.vector import LicenseClientError, list_licenses

LicenseSource = Callable[[], Iterable[LicenseObservation]]


def vector_license_client_source(executable: str) -> LicenseSource:
    """Licenses of the New Vector License Model (``Vector.LicenseClient -listlicenses``)."""

    def read() -> list[LicenseObservation]:
        return [lic.to_observation() for lic in list_licenses(executable)]

    return read


class LicenseCollector:
    """Keeps the latest license list; warns at most once a day per license.

    A source that is not installed or fails is skipped and logged once per distinct error; the
    licenses it reported last time are dropped, since they can no longer be confirmed.
    """

    def __init__(self, sources: dict[str, LicenseSource], warn_days: int = 30, logger: Any = None):
        self._sources = sources
        self._warn_days = warn_days
        self._logger = logger
        self._lock = threading.Lock()
        self._licenses: list[LicenseObservation] = []
        self._last_errors: dict[str, str] = {}
        self._warned: dict[str, date] = {}

    @property
    def licenses(self) -> list[LicenseObservation]:
        with self._lock:
            return list(self._licenses)

    def collect(self) -> list[LicenseObservation]:
        found: list[LicenseObservation] = []
        for name, source in self._sources.items():
            try:
                found.extend(source())
                self._last_errors.pop(name, None)
            except LicenseClientError as error:
                self._log_once(name, str(error))
            except Exception as error:  # a vendor tool must never stop the agent
                self._log_once(name, f"{type(error).__name__}: {error}")
        found.sort(key=lambda lic: (lic.carrier_label, lic.product_name))
        with self._lock:
            self._licenses = found
        return found

    def due_warnings(self, now: datetime | None = None) -> list[LicenseObservation]:
        """Licenses expiring within the window that have not been warned about today."""
        now = now or datetime.now()
        today = now.date()
        due = []
        for lic in expiring(self.licenses, now, self._warn_days):
            if self._warned.get(lic.observation_key) != today:
                self._warned[lic.observation_key] = today
                due.append(lic)
        return due

    def _log_once(self, source: str, message: str) -> None:
        if self._last_errors.get(source) == message:
            return
        self._last_errors[source] = message
        if self._logger is not None:
            self._logger.info(f"[Licenses] {source}: {message}")


def warning_text(lic: LicenseObservation, now: datetime) -> str:
    days = lic.days_left(now)
    if days == 0:
        when = "has expired" if lic.expires_at and lic.expires_at <= now else "expires today"
    else:
        when = f"expires in {days} day{'s' if days != 1 else ''} ({lic.expires_at:%d %b %Y})"
    action = "Reactivate it in the Vector License Client." if lic.is_reactivatable else "Renew it in time."
    return f"{lic.product_name} on {lic.carrier_label} {when}. {action}"
