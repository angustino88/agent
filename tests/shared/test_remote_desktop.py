"""RDP client address decoding (``WTS_CLIENT_ADDRESS``) and the hostname fallback."""

import subprocess

import pytest

pytest.importorskip("win32api")  # src.utils needs pywin32: runs on the Windows CI

subprocess.CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows-only constant

from src.utils.remote_desktop import RemoteDesktop, client_ip_from_wts_address  # noqa: E402


def test_ipv4_and_ipv6_client_addresses():
    assert client_ip_from_wts_address(2, [0, 0, 10, 20, 4, 17] + [0] * 14) == "10.20.4.17"
    ipv6 = bytes(2) + bytes.fromhex("fe800000000000000000000000000001") + bytes(2)
    assert client_ip_from_wts_address(23, ipv6) == "fe80::1"


def test_unknown_or_empty_addresses_are_blank():
    assert client_ip_from_wts_address(0, [0] * 20) == ""
    assert client_ip_from_wts_address(2, [0] * 20) == ""  # 0.0.0.0
    assert client_ip_from_wts_address(2, None) == ""


def test_hostname_is_never_this_computer_when_no_client(monkeypatch):
    monkeypatch.setattr(RemoteDesktop, "get_client_ip", staticmethod(lambda: None))
    assert RemoteDesktop.get_client_hostname() is None
