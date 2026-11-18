"""Remote Desktop (RDP) session utilities for Windows."""
from __future__ import annotations

import os
import re
import socket
from subprocess import CREATE_NO_WINDOW, STDOUT, check_output

class RemoteDesktop:
    @staticmethod
    def get_client_hostname() -> str | None:
        """
        Get the FQDN (fully qualified domain name) of the remote desktop client computer.
        """
        try:
            return socket.getfqdn(RemoteDesktop.get_client_ip())
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
