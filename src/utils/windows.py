"""Windows system utility functions (network, process, disk, environment)."""
from __future__ import annotations

import os
import socket
import getpass
import psutil


class WindowsUtil:
    """
    Windows utility functions for networking and process management.
    """

    @staticmethod
    def get_ipv4() -> str | None:
        """Get the primary IPv4 address of the computer."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return None
        finally:
            s.close()

    @staticmethod
    def get_hostname() -> str:
        """Get the host name."""
        return socket.gethostname()

    @staticmethod
    def get_username() -> str:
        """Get the current user name."""
        try:
            return os.getlogin()
        except Exception:
            return getpass.getuser()

    @staticmethod
    def get_fqdn(ip: str = '') -> str:
        """Get the fully qualified domain name for an IP or local host."""
        return socket.getfqdn(ip)

    @staticmethod
    def proc_exists(name: str) -> bool:
        """Check if a process with the given name is running."""
        for proc in psutil.process_iter(['name']):
            try:
                if name.lower() in proc.info['name'].lower():
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def get_proc_pids(name: str) -> list[int]:
        """Get a list of PIDs for all running processes matching the given name."""
        pids = []
        for proc in psutil.process_iter(['name']):
            try:
                if name.lower() in proc.info['name'].lower():
                    pids.append(proc.pid)
            except Exception:
                continue
        return pids

    @staticmethod
    def get_proc_names() -> list[str]:
        """Get a list of all running process names."""
        names = []
        for proc in psutil.process_iter(['name']):
            try:
                names.append(proc.info['name'])
            except Exception:
                continue
        return names

    @staticmethod
    def get_mac() -> str | None:
        """Get the MAC address of the first network interface."""
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    return addr.address
        return None

    @staticmethod
    def get_cpu_usage(interval: float = 1.0) -> float:
        """Get the CPU usage percentage."""
        return psutil.cpu_percent(interval=interval)

    @staticmethod
    def get_memory_usage() -> float:
        """Get the memory usage percentage."""
        return psutil.virtual_memory().percent

    @staticmethod
    def get_disk_usage(path: str = "C:\\") -> dict:
        """
        Get the disk usage for the given path in gigabytes.
        """
        usage = psutil.disk_usage(path)
        gb = 1024 ** 3
        return {
            "total_gb": round(usage.total / gb, 2),
            "used_gb": round(usage.used / gb, 2),
            "free_gb": round(usage.free / gb, 2),
            "percent": usage.percent
        }

    @staticmethod
    def get_physical_disks() -> list[str]:
        """Return a list of physical disk device paths."""
        disks = []
        for part in psutil.disk_partitions(all=False):
            if not part.device.lower().startswith('tmpfs') and not part.mountpoint.startswith('/snap'):
                disks.append(part.device)
        return disks

    @staticmethod
    def get_folders(root_path: str, all_levels: bool = True) -> list[str]:
        """
        Get folders under the given path.
        """
        folders = []

        if all_levels:
            # Recursively get all folders
            for dirpath, dirnames, _ in os.walk(root_path):
                for dirname in dirnames:
                    folders.append(os.path.join(dirpath, dirname))
        else:
            # Get only top-level folders
            with os.scandir(root_path) as entries:
                for entry in entries:
                    if entry.is_dir():
                        folders.append(entry.path)

        return folders

    @staticmethod
    def get_folder_size(path: str, unit: str = "GB") -> float:
        """
        Returns folder size in a chosen unit (Bytes, KB, MB, GB).
        """
        def _folder_size(p: str) -> int:
            total = 0
            try:
                with os.scandir(p) as entries:
                    for entry in entries:
                        try:
                            if entry.is_file(follow_symlinks=False):
                                total += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                total += _folder_size(entry.path)
                        except FileNotFoundError:
                            pass
            except PermissionError:
                pass
            return total

        size_bytes = _folder_size(path)

        unit = unit.upper()
        if unit == "BYTES":
            size = size_bytes
        elif unit == "KB":
            size = size_bytes / 1024
        elif unit == "MB":
            size = size_bytes / (1024 ** 2)
        elif unit == "GB":
            size = size_bytes / (1024 ** 3)
        else:
            raise ValueError("Unit must be one of: 'Bytes', 'KB', 'MB', 'GB'")

        return size

    @staticmethod
    def get_disk_io_counters() -> dict:
        """
        Get system-wide disk I/O statistics.
        """
        counters = psutil.disk_io_counters()
        return counters._asdict() if counters else {}

    @staticmethod
    def get_net_io_counters() -> dict:
        """
        Get system-wide network I/O statistics.
        """
        counters = psutil.net_io_counters()
        return counters._asdict() if counters else {}

    @staticmethod
    def get_boot_time() -> float:
        """
        Get the system boot time as a timestamp.
        """
        return psutil.boot_time()

    @staticmethod
    def get_uptime() -> float:
        """
        Get the system uptime in seconds.
        """
        return psutil.time.time() - psutil.boot_time()

    @staticmethod
    def get_env(var: str, default: str | None = None) -> str | None:
        """
        Get an environment variable value.
        """
        return os.environ.get(var, default)

    @staticmethod
    def get_temp_dir() -> str:
        """
        Get the path to the system temporary directory.
        """
        return os.getenv('TEMP') or os.getenv('TMP') or '/tmp'

    @staticmethod
    def get_user_home() -> str:
        """
        Get the path to the current user's home directory.
        """
        return os.path.expanduser("~")