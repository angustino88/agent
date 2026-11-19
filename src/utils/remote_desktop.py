"""Remote Desktop (RDP) session utilities for Windows."""
from __future__ import annotations

import ipaddress
import os
import re
import socket
from dataclasses import dataclass
from subprocess import CREATE_NO_WINDOW, STDOUT, check_output

_AF_INET = 2
_AF_INET6 = 23


@dataclass(frozen=True)
class RdpClient:
    """The computer the current Remote Desktop session comes from (empty values when unknown)."""

    name: str = ""
    ip: str = ""


def client_ip_from_wts_address(family: int, address) -> str:
    """IP of a ``WTS_CLIENT_ADDRESS``: IPv4 is bytes 2..5, IPv6 bytes 2..17 of ``Address``."""
    raw = bytes(address or b"")
    try:
        if family == _AF_INET and len(raw) >= 6:
            ip = ipaddress.IPv4Address(raw[2:6])
        elif family == _AF_INET6 and len(raw) >= 18:
            ip = ipaddress.IPv6Address(raw[2:18])
        else:
            return ""
    except ValueError:
        return ""
    return "" if ip.is_unspecified else str(ip)

class RemoteDesktop:
    @staticmethod
    def get_session_client() -> RdpClient:
        """Client name and IP of *this* process's Remote Desktop session (Windows WTS API).

        Unlike ``netstat``, this works for UDP transport, RD Gateway, other ports and IPv6, and
        never confuses another session's client with ours. Empty on the console or on error.
        """
        try:
            import win32ts

            server, session = win32ts.WTS_CURRENT_SERVER_HANDLE, win32ts.WTS_CURRENT_SESSION
            if win32ts.WTSQuerySessionInformation(server, session, win32ts.WTSClientProtocolType) == 0:
                return RdpClient()  # console session: nobody is connected remotely
            name = win32ts.WTSQuerySessionInformation(server, session, win32ts.WTSClientName) or ""
            address = win32ts.WTSQuerySessionInformation(server, session, win32ts.WTSClientAddress) or {}
            ip = client_ip_from_wts_address(address.get("AddressFamily", 0), address.get("Address"))
            return RdpClient(name=str(name).strip(), ip=ip)
        except Exception:
            return RdpClient()

    @staticmethod
    def get_client_hostname() -> str | None:
        """
        Get the FQDN (fully qualified domain name) of the remote desktop client computer.
        """
        ip = RemoteDesktop.get_client_ip()
        if not ip:
            return None  # socket.getfqdn(None) would return this computer's own name
        try:
            return socket.getfqdn(ip)
        except Exception:
            return None

    @staticmethod
    def get_host_hostnames() -> list[str]:
        """
        Get a list of FQDNs for all host computers with active RDP sessions.
        """
        return [socket.getfqdn(ip) for ip in RemoteDesktop.get_host_ips()]

    @staticmethod
    def get_client_ip() -> str | None:
        """
        Get the IP address of the remote desktop client.
        Returns None if not found.
        """
        for resp in os.popen('netstat -n | find ":3389"'):
            parts = re.sub(r'\s+', ';', resp.strip()).split(';')
            if len(parts) == 4 and ':3389' in parts[1] and parts[3] == 'ESTABLISHED':
                return parts[2].split(':')[0].strip()
        return None

    @staticmethod
    def get_host_ips() -> list[str]:
        """
        Get a list of IP addresses for all hosts with active RDP sessions.
        """
        ips = []
        for resp in os.popen('netstat -n | find ":3389"'):
            parts = re.sub(r'\s+', ';', resp.strip()).split(';')
            if len(parts) == 4 and ':3389' in parts[2] and parts[3] == 'ESTABLISHED':
                ips.append(parts[2].split(':')[0].strip())
        return ips

    @staticmethod
    def is_connected() -> bool:
        """
        Check if there is an active RDP session.
        Returns True if connected, False otherwise.
        """
        output = check_output('qwinsta', stderr=STDOUT, creationflags=CREATE_NO_WINDOW).decode('latin1')
        return any('rdp-tcp#' in line and 'Active' in line for line in output.split('\r\n'))

    @staticmethod
    def disconnect() -> None:
        """
        Disconnect the current RDP session.
        """
        os.system('tsdiscon')
