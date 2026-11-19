from datetime import datetime, timedelta
from types import SimpleNamespace

from src.app.controller.monitoring.license_collector import LicenseCollector, warning_text
from src.core.licensing import VECTOR_LICENSE_CLIENT, CheckResult, CheckStatus, LicenseObservation
from src.core.monitoring import HardwareId


def settings(**over):
    base = dict(
        vector_license_client=r"C:\Program Files\Vector License Client\Vector.LicenseClient.exe",
        license_trusted_paths=[],
        license_allowed_roots=[],
        license_builtin_checks=["vector-license-client"],
        license_warn_days=30,
        tls_verify_enabled=False,
    )
    base.update(over)
    return SimpleNamespace(**base)


class Backend:
    def __init__(self, supported=False, items=None):
        self.is_enrolled = True
        self.supported = supported
        self.items = items
        self.reports = []

    def supports(self, capability):
        return self.supported

    def fetch_license_checks(self):
        return self.items

    def report_license_check(self, result):
        self.reports.append(result)


def lic(check_key="vector-license-client", expires=datetime(2027, 4, 9, 23, 59, 59)):
    return LicenseObservation(
        check_key=check_key,
        observation_key=f"{check_key}:device:007113-585343:55100",
        vendor="Vector",
        product_code="55100",
        product_name="CANalyzer PRO",
        carrier_type="device",
        carrier_hardware_id=HardwareId("vector_device", "007113-585343"),
        expires_at=expires,
        final_expires_at=None,
        max_version="15.0",
        is_reactivatable=True,
    )


class Runner:
    def __init__(self, status=CheckStatus.OK, licenses=(lic(),)):
        self.calls = []
        self.status, self.licenses = status, licenses

    def __call__(self, check, policy):
        self.calls.append((check, policy))
        return CheckResult(
            check.key,
            check.revision,
            self.status,
            datetime.now(),
            5,
            self.licenses if self.status == CheckStatus.OK else (),
            "",
            "",
        )


def test_builtin_preset_runs_when_the_backend_serves_no_checks():
    runner = Runner()
    collector = LicenseCollector(Backend(supported=False), settings(), runner=runner)
    collector.sync_checks()
    collector.run_due()
    assert [c.key for c, _ in runner.calls] == ["vector-license-client"]
    assert collector.licenses == [lic()]
    policy = runner.calls[0][1]
    assert not policy.allow_configured_paths  # TLS not verified: only trusted paths
    assert settings().vector_license_client in policy.trusted_paths


def test_backend_checks_replace_builtins_and_are_reported():
    item = dict(VECTOR_LICENSE_CLIENT, key="vector-lab", revision=2)
    broken = {"key": "broken", "revision": 4, "probe": {"type": "shell"}}
    unknown = {"key": "nameless", "probe": {"type": "shell"}}  # no revision: the backend could not place it
    backend = Backend(supported=True, items=[item, broken, unknown])
    runner = Runner()
    collector = LicenseCollector(backend, settings(), runner=runner)
    collector.sync_checks()
    collector.run_due()
    assert [c.key for c, _ in runner.calls] == ["vector-lab"]
    assert [(r.check_key, r.revision, r.status) for r in backend.reports] == [
        ("broken", 4, "rejected"),
        ("vector-lab", 2, "ok"),
    ]


def test_each_check_runs_on_its_interval_and_a_new_revision_runs_at_once():
    item = dict(VECTOR_LICENSE_CLIENT, revision=1)
    backend = Backend(supported=True, items=[item])
    runner = Runner()
    collector = LicenseCollector(backend, settings(), runner=runner)
    collector.sync_checks()
    collector.run_due()
    collector.run_due(datetime.now() + timedelta(minutes=30))
    assert len(runner.calls) == 1  # 360-minute interval
    backend.items = None  # 304: unchanged
    collector.sync_checks()
    collector.run_due(datetime.now() + timedelta(hours=7))
    assert len(runner.calls) == 2
    backend.items = [dict(item, revision=2)]
    collector.sync_checks()
    collector.run_due()
    assert len(runner.calls) == 3


def test_failed_run_keeps_the_last_known_licenses():
    runner = Runner()
    collector = LicenseCollector(Backend(), settings(), runner=runner)
    collector.sync_checks()
    collector.run_due()
    runner.status = CheckStatus.FAILED
    collector.run_due(datetime.now() + timedelta(hours=7))
    (state,) = collector.states
    assert state.last_result.status == CheckStatus.FAILED and state.last_licenses == (lic(),)


def test_warns_once_a_day_inside_the_window():
    collector = LicenseCollector(Backend(), settings(), runner=Runner())
    collector.sync_checks()
    collector.run_due()
    assert collector.due_warnings(datetime(2027, 3, 1)) == []
    assert collector.due_warnings(datetime(2027, 3, 15, 9)) == [lic()]
    assert collector.due_warnings(datetime(2027, 3, 15, 15)) == []
    assert collector.due_warnings(datetime(2027, 3, 16, 9)) == [lic()]


def test_warning_text():
    assert warning_text(lic(), datetime(2027, 3, 30, 12)) == (
        "CANalyzer PRO on 007113-585343 expires in 10 days (09 Apr 2027). Reactivate it in the vendor's license tool."
    )
