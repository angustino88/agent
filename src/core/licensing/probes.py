"""Read-only probes, and the local safety rules the backend configuration cannot override.

The web app decides *which* checks a computer runs. This computer decides *what is allowed*:

* commands run without a shell, with a fixed argument list, a timeout and an output limit;
* executables and files must be under an allowed root (Program Files, ProgramData, plus roots in
  the local settings) and exist; registry probes read HKLM only;
* when the connection to the backend is not TLS-verified, configured paths are ignored unless they
  are one of this computer's trusted defaults (presets): an attacker in the middle cannot make the
  agent run or read something new.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import PureWindowsPath
from typing import Iterable

from .checks import Probe, ProbeType

MAX_OUTPUT_BYTES = 4 * 1024 * 1024


class ProbeRejected(Exception):
    """The probe breaks a local safety rule (``error_code`` says which)."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


class ProbeUnavailable(Exception):
    """The tool, file or registry key is not on this computer."""


class ProbeFailed(Exception):
    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code


def default_allowed_roots() -> tuple[str, ...]:
    names = ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "ProgramData")
    return tuple(dict.fromkeys(os.environ[n] for n in names if os.environ.get(n)))


@dataclass(frozen=True)
class SafetyPolicy:
    allowed_roots: tuple[str, ...] = field(default_factory=default_allowed_roots)
    trusted_paths: frozenset[str] = frozenset()  # preset defaults and locally configured tool paths
    allow_configured_paths: bool = False  # True only when the backend connection is TLS-verified

    @staticmethod
    def _norm(path: str) -> str:
        return os.path.normcase(os.path.normpath(path))

    def check_path(self, path: str) -> str:
        if not path or "\x00" in path:
            raise ProbeRejected("path_not_allowed", "empty path")
        is_absolute = os.path.isabs(path) or PureWindowsPath(path).is_absolute()
        if not is_absolute:
            raise ProbeRejected("path_not_allowed", "path must be absolute")
        normalized = self._norm(path)
        if normalized in {self._norm(p) for p in self.trusted_paths}:
            return path
        if not self.allow_configured_paths:
            raise ProbeRejected("untrusted_connection", "configured paths need a TLS-verified backend connection")
        roots = [self._norm(r) for r in self.allowed_roots if r]
        if not any(normalized == r or normalized.startswith(r.rstrip("\\/") + os.sep) for r in roots):
            raise ProbeRejected("path_not_allowed", "path is outside the allowed folders")
        return path


def run_command(probe: Probe, policy: SafetyPolicy) -> bytes:
    executable = policy.check_path(probe.executable)
    if not os.path.isfile(executable):
        raise ProbeUnavailable(f"{os.path.basename(executable)} is not installed")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    try:
        completed = subprocess.run(
            [executable, *probe.args],
            capture_output=True,
            timeout=probe.timeout_s,
            cwd=os.path.dirname(executable) or None,
            creationflags=flags,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise ProbeFailed("timeout", f"no answer within {probe.timeout_s} s") from None
    except OSError as error:
        raise ProbeFailed("start_failed", type(error).__name__) from None
    if completed.returncode != 0:
        raise ProbeFailed("exit_code", f"exited with code {completed.returncode}")
    if len(completed.stdout) > MAX_OUTPUT_BYTES:
        raise ProbeFailed("output_too_large", "output exceeds 4 MiB")
    return completed.stdout


def read_file(probe: Probe, policy: SafetyPolicy) -> bytes:
    path = policy.check_path(probe.path)
    if not os.path.isfile(path):
        raise ProbeUnavailable(f"{os.path.basename(path)} not found")
    if os.path.getsize(path) > MAX_OUTPUT_BYTES:
        raise ProbeFailed("output_too_large", "file exceeds 4 MiB")
    with open(path, "rb") as handle:
        return handle.read(MAX_OUTPUT_BYTES + 1)


def read_registry(probe: Probe, _policy: SafetyPolicy) -> dict[str, str]:
    try:
        import winreg  # Windows only
    except ImportError:
        raise ProbeUnavailable("the Windows registry is not available") from None
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, probe.key, 0, winreg.KEY_READ) as key:
            values = {}
            for name in probe.values:
                try:
                    values[name] = str(winreg.QueryValueEx(key, name)[0])
                except FileNotFoundError:
                    values[name] = ""
            return values
    except FileNotFoundError:
        raise ProbeUnavailable("registry key not found") from None
    except OSError as error:
        raise ProbeFailed("registry_error", type(error).__name__) from None


_READERS = {ProbeType.COMMAND: run_command, ProbeType.FILE: read_file, ProbeType.REGISTRY: read_registry}


def read(probe: Probe, policy: SafetyPolicy):
    return _READERS[probe.type](probe, policy)


def trusted(paths: Iterable[str]) -> frozenset[str]:
    return frozenset(p for p in paths if p)
