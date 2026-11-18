import os
import sys
import platform
import psutil
import socket
import wmi
from datetime import datetime

from src.mvc.base_model import BaseModel
from src.utils.windows import WindowsUtil

class ComputerModel(BaseModel):
    def __init__(self):
        super().__init__()
        self.c = wmi.WMI()
        self.computer_system = self.c.Win32_ComputerSystem()[0]
        self.bios = self.c.Win32_BIOS()[0]
        self.os = self.c.Win32_OperatingSystem()[0]
        self.processor = self.c.Win32_Processor()[0]
        self.gpus = self.c.Win32_VideoController()

        self._os_name = self.os.Caption
        self._computer_name = WindowsUtil.get_hostname()
        self._computer_ip = WindowsUtil.get_ipv4()
        
    def _parse_wmi_date(self, wmi_date: str):
        if not wmi_date:
            return None
        try:
            dt = datetime.strptime(wmi_date.split('.')[0], '%Y%m%d%H%M%S')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return wmi_date
    
    def init(self):
        self._app_version = self.model.config_model.app_config.APP_VERSION
    
    @property
    def os_name(self):
        return self._os_name

    @property
    def computer_name(self):
        return self._computer_name
    
    @property
    def computer_ip(self):
        return self._computer_ip

    def get_system_info(self):
        try:
            boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            boot_time = None

        def safe_get(obj, attr, default=None):
            try:
                return getattr(obj, attr, default)
            except Exception:
                return default
        
        return {
            "os_name": safe_get(self.os, "Caption", platform.system()),
            "os_version": safe_get(self.os, "Version", platform.version()),
            "os_build": safe_get(self.os, "BuildNumber"),
            "architecture": platform.machine(),
            "hostname": self._computer_name,
            "ip_address": self._computer_ip,
            "boot_time": boot_time,
            "os_manufacturer": safe_get(self.os, "Manufacturer", "Microsoft Corporation"),
            "system_name": safe_get(self.computer_system, "Name", self._computer_name),
            "system_manufacturer": safe_get(self.computer_system, "Manufacturer"),
            "system_model": safe_get(self.computer_system, "Model"),
            "system_type": safe_get(self.computer_system, "SystemType"),
            "system_sku": safe_get(self.computer_system, "SKUNumber"),
            "processor_name": safe_get(self.processor, "Name"),
            "processor_speed_mhz": safe_get(self.processor, "MaxClockSpeed"),
            "processor_cores": safe_get(self.processor, "NumberOfCores"),
            "processor_logical": safe_get(self.processor, "NumberOfLogicalProcessors"),
            "bios_version": safe_get(self.bios, "SMBIOSBIOSVersion"),
            "bios_release_date": self._parse_wmi_date(safe_get(self.bios, "ReleaseDate")),
            "baseboard_manufacturer": safe_get(self.computer_system, "Manufacturer"),
            "baseboard_product": safe_get(self.computer_system, "Product"),
            "baseboard_version": safe_get(self.computer_system, "Version"),
            "platform_role": safe_get(self.computer_system, "Role"),
            "secure_boot_state": safe_get(self.computer_system, "SecureBootState"),
            "agent_version": self._app_version,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_gpu_info(self):
        # GPU info
        gpu_info = []
        for g in self.gpus:
            gpu_info.append({
                "name": getattr(g, "Name", None),
                "driver_version": getattr(g, "DriverVersion", None),
                "video_processor": getattr(g, "VideoProcessor", None),
                "memory_mb": getattr(g, "AdapterRAM", None)
            })
        return gpu_info

    def get_memory_info(self):
        memory = psutil.virtual_memory()
        return {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "percent": memory.percent
        }

    def get_disk_usage(self):
        disk_data = []
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disk_data.append({
                    "name": p.device,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent": usage.percent
                })
            except PermissionError:
                continue
        return disk_data

    def get_network_info(self):
        hostname = socket.gethostname()
        try:
            ip_address = socket.gethostbyname(hostname)
        except Exception:
            ip_address = None
        return {
            "hostname": hostname,
            "ip_address": ip_address
        }

    def get_battery_info(self):
        battery = psutil.sensors_battery()
        if not battery:
            return None
        return {
            "percent": battery.percent,
            "plugged_in": battery.power_plugged,
            "secs_left": battery.secsleft
        }

    def get_full_info(self):
        return {
            "system_info": self.get_system_info(),
            "memory_info": self.get_memory_info(),
            "disk_info": self.get_disk_usage(),
            "network_info": self.get_network_info(),
            "battery_info": self.get_battery_info()
        }