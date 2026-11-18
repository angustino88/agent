import copy
import subprocess

import pytest

from src.core.licensing import VECTOR_LICENSE_CLIENT, CheckStatus, SafetyPolicy, parse_check, run_check
from src.core.licensing import probes
from src.core.licensing.checks import Probe


def command_probe(path):
    return Probe(type="command", executable=str(path), args=("-listlicenses",), timeout_s=5)


def test_untrusted_connection_only_runs_trusted_paths(tmp_path):
    exe = tmp_path / "tool.exe"
    exe.write_text("")
    policy = SafetyPolicy(allowed_roots=(str(tmp_path),), allow_configured_paths=False)
    with pytest.raises(probes.ProbeRejected) as caught:
        probes.run_command(command_probe(exe), policy)
    assert caught.value.error_code == "untrusted_connection"


def test_paths_outside_allowed_roots_are_rejected(tmp_path):
    policy = SafetyPolicy(allowed_roots=(str(tmp_path / "allowed"),), allow_configured_paths=True)
    for path in (str(tmp_path / "other" / "tool.exe"), "relative.exe", str(tmp_path / "allowed" / ".." / "x.exe")):
        with pytest.raises(probes.ProbeRejected):
            policy.check_path(path)


def test_trusted_command_runs_without_shell(monkeypatch, tmp_path):
    exe = tmp_path / "Vector.LicenseClient.exe"
    exe.write_text("")
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout=b"<Containers/>", stderr=b"")

    monkeypatch.setattr(probes.subprocess, "run", fake_run)
    policy = SafetyPolicy(allowed_roots=(), trusted_paths=frozenset({str(exe)}))
    assert probes.run_command(command_probe(exe), policy) == b"<Containers/>"
    args, kwargs = calls[0]
    assert args == [str(exe), "-listlicenses"] and "shell" not in kwargs and kwargs["timeout"] == 5


def check_for(exe):
    data = copy.deepcopy(VECTOR_LICENSE_CLIENT)
    data["probe"]["executable"] = str(exe)
    return parse_check(data)


@pytest.mark.parametrize(
    "error, status, code",
    [
        (probes.ProbeUnavailable("missing"), CheckStatus.NOT_INSTALLED, "not_installed"),
        (probes.ProbeFailed("timeout", "slow"), CheckStatus.FAILED, "timeout"),
        (probes.ProbeRejected("path_not_allowed", "no"), CheckStatus.REJECTED, "path_not_allowed"),
        (RuntimeError("boom"), CheckStatus.FAILED, "internal_error"),
    ],
)
def test_runner_classifies_failures(tmp_path, error, status, code):
    def reader(probe, policy):
        raise error

    result = run_check(check_for(tmp_path / "x.exe"), SafetyPolicy(), reader=reader)
    assert (result.status, result.error_code, result.licenses) == (status, code, ())


def test_runner_ok_and_parse_error(tmp_path):
    ok = run_check(check_for(tmp_path / "x.exe"), SafetyPolicy(), reader=lambda p, s: b"<Containers/>")
    assert ok.status == CheckStatus.OK and ok.is_complete and ok.licenses == ()
    bad = run_check(check_for(tmp_path / "x.exe"), SafetyPolicy(), reader=lambda p, s: b"garbage")
    assert (bad.status, bad.error_code) == (CheckStatus.FAILED, "parse_error")
