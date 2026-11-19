"""The RDP client hostname never falls back to this computer's own name."""

import subprocess

import pytest

pytest.importorskip("win32api")  # src.utils needs pywin32: runs on the Windows CI
subprocess.CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows-only constant

from src.utils.remote_desktop import RemoteDesktop  # noqa: E402


def test_hostname_is_never_this_computer_when_no_client(monkeypatch):
    monkeypatch.setattr(RemoteDesktop, "get_client_ip", staticmethod(lambda: None))
    assert RemoteDesktop.get_client_hostname() is None
