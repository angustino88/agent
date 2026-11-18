"""Runs the license checks configured for this computer and keeps the results.

Where checks come from:

* the backend (``GET /agent/license-checks``), when it advertises ``license_checks``: the web app
  configures checks and which computers run them;
* otherwise the built-in presets enabled in the local settings (``licenses.builtin_checks``).

Each check runs on its own interval. Results are reported to the backend when it supports it, and
kept for the device dialog and the tray warnings either way.
"""

from __future__ import annotations

import copy
import threading
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Optional

from src.core.agent_api import errors as agent_errors
from src.core.agent_api.client import CAPABILITY_LICENSE_CHECKS
from src.core.licensing import (
    PRESETS,
    CheckResult,
    CheckStatus,
    LicenseCheck,
    LicenseObservation,
    SafetyPolicy,
    expiring,
    parse_check,
    parse_checks,
    preset_executables,
    run_check,
)
from src.core.licensing.probes import default_allowed_roots

Runner = Callable[[LicenseCheck, SafetyPolicy], CheckResult]


@dataclass(frozen=True)
class CheckState:
    check: LicenseCheck
    source: str  # "backend" | "builtin"
    last_result: Optional[CheckResult] = None
    last_licenses: tuple = ()  # from the last successful run


class LicenseCollector:
    def __init__(self, backend_model: Any, app_settings: Any, logger: Any = None, runner: Runner = run_check):
        self._backend = backend_model
        self._settings = app_settings
        self._logger = logger
        self._runner = runner
        self._lock = threading.Lock()
        self._states: dict[str, CheckState] = {}
        self._warned: dict[str, date] = {}

    # ------------------------------------------------------------------ configuration

    def safety_policy(self) -> SafetyPolicy:
        trusted = {*preset_executables(), self._settings.vector_license_client, *self._settings.license_trusted_paths}
        return SafetyPolicy(
            allowed_roots=(*default_allowed_roots(), *self._settings.license_allowed_roots),
            trusted_paths=frozenset(p for p in trusted if p),
            allow_configured_paths=self._settings.tls_verify_enabled,
        )

    def _builtin_checks(self) -> list[LicenseCheck]:
        checks = []
        for key in self._settings.license_builtin_checks:
            preset = PRESETS.get(key)
            if preset is None:
                self._log("warning", f"unknown built-in check '{key}'")
                continue
            data = copy.deepcopy(preset)
            if key == "vector-license-client" and self._settings.vector_license_client:
                data["probe"]["executable"] = self._settings.vector_license_client
            checks.append(parse_check(data))
        return checks

    def sync_checks(self) -> None:
        """Load the checks to run: from the backend when it serves them, else the built-in presets."""
        backend_checks = None
        if self._backend.is_enrolled and self._backend.supports(CAPABILITY_LICENSE_CHECKS):
            try:
                items = self._backend.fetch_license_checks()
            except agent_errors.AgentApiError as e:
                self._log("info", f"could not fetch checks, keeping the current ones: {e}")
                return
            if items is None:
                return  # unchanged (304)
            backend_checks, rejected = parse_checks(items)
            for key, reason in rejected.items():
                self._log("warning", f"check '{key}' rejected: {reason}")
                self._report(self._rejected_result(key, reason))
        checks, source = (
            (backend_checks, "backend") if backend_checks is not None else (self._builtin_checks(), "builtin")
        )
        with self._lock:
            previous = self._states
            self._states = {c.key: CheckState(c, source, *self._carry_over(previous.get(c.key), c)) for c in checks}

    @staticmethod
    def _carry_over(state: Optional[CheckState], check: LicenseCheck) -> tuple:
        if state is None or state.check.revision != check.revision:
            return (None, ())  # a changed check runs again at once
        return (state.last_result, state.last_licenses)

    # ------------------------------------------------------------------ running

    def run_due(self, now: Optional[datetime] = None) -> list[CheckResult]:
        now = now or datetime.now()
        policy = self.safety_policy()
        results = []
        for state in self.states:
            last = state.last_result
            if last and now - last.started_at < timedelta(minutes=state.check.interval_minutes):
                continue
            result = self._runner(state.check, policy)
            results.append(result)
            self._store(result)
            self._log_result(state.check, result)
            if state.source == "backend":
                self._report(result)
        return results

    def _store(self, result: CheckResult) -> None:
        with self._lock:
            state = self._states.get(result.check_key)
            if state is None:
                return
            licenses = result.licenses if result.status == CheckStatus.OK else state.last_licenses
            self._states[result.check_key] = CheckState(state.check, state.source, result, licenses)

    def _report(self, result: CheckResult) -> None:
        try:
            self._backend.report_license_check(result)
        except Exception as e:
            self._log("info", f"report deferred: {e}")

    @staticmethod
    def _rejected_result(key: str, reason: str) -> CheckResult:
        return CheckResult(key, 0, CheckStatus.REJECTED, datetime.now(), 0, (), "invalid_check", reason)

    # ------------------------------------------------------------------ results

    @property
    def states(self) -> list[CheckState]:
        with self._lock:
            return list(self._states.values())

    @property
    def licenses(self) -> list[LicenseObservation]:
        found = [lic for state in self.states for lic in state.last_licenses]
        return sorted(found, key=lambda lic: (lic.carrier_label, lic.product_name))

    def due_warnings(
        self, now: Optional[datetime] = None, within_days: Optional[int] = None
    ) -> list[LicenseObservation]:
        """Licenses expiring within the window that have not been warned about today."""
        now = now or datetime.now()
        days = within_days if within_days is not None else self._settings.license_warn_days
        due = []
        for lic in expiring(self.licenses, now, days):
            if self._warned.get(lic.observation_key) != now.date():
                self._warned[lic.observation_key] = now.date()
                due.append(lic)
        return due

    # ------------------------------------------------------------------ logging

    def _log(self, level: str, message: str) -> None:
        if self._logger is not None:
            getattr(self._logger, level, self._logger.info)(f"[Licenses] {message}")

    def _log_result(self, check: LicenseCheck, result: CheckResult) -> None:
        if result.status == CheckStatus.OK:
            self._log("info", f"{check.name}: {len(result.licenses)} license(s) in {result.duration_ms} ms")
            for lic in result.licenses:
                self._log("info", f"  {lic.describe()}")
        else:
            self._log("warning", f"{check.name}: {result.status} ({result.error_code}) {result.error_message}")


def warning_text(lic: LicenseObservation, now: datetime) -> str:
    days = lic.days_left(now)
    if days == 0:
        when = "has expired" if lic.expires_at and lic.expires_at <= now else "expires today"
    else:
        when = f"expires in {days} day{'s' if days != 1 else ''} ({lic.expires_at:%d %b %Y})"
    action = "Reactivate it in the vendor's license tool." if lic.is_reactivatable else "Renew it in time."
    return f"{lic.product_name} on {lic.carrier_label} {when}. {action}"
