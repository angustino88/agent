"""Utility library — clean public API.

Import the most commonly used classes and functions at the package level
so consumers can write::

    from src.utils import FileUtil, DictUtil, HashUtil
"""
from __future__ import annotations

from .class_property import classproperty, classproperty_support
from .config import (
    ConfigDefault,
    ConfigFileManager,
    ConfigValidator,
    IniParserUtil,
    JsonParserUtil,
    YamlParserUtil,
)
from .conversion import ConversionUtil
from .datetime import (
    elapsed_str,
    iso_datetime,
    local_now,
    parse_iso,
    timestamp_ms,
    utc_now,
)
from .dict import DictUtil
from .dir import DirUtil
from .email import EmailHandler, EmailHandlerError
from .excel import ExcelUtil
from .file import FileUtil
from .hash import HashUtil
from .http_client import ClientRequest, ClientResponse
from .list import ListUtil
from .mdf import MDFReader
from .metaclass import metaclass_factory
from .otp import OTPService
from .path import PathUtil
from .single_instance import InstanceScope, SingleInstance
from .systray import SystemTray
from .timer import Timer
from .windows import WindowsUtil
from .zip import ZipUtil

__all__ = [
    # class_property
    "classproperty",
    "classproperty_support",
    # config
    "ConfigDefault",
    "ConfigFileManager",
    "ConfigValidator",
    "IniParserUtil",
    "JsonParserUtil",
    "YamlParserUtil",
    # conversion
    "ConversionUtil",
    # datetime
    "elapsed_str",
    "iso_datetime",
    "local_now",
    "parse_iso",
    "timestamp_ms",
    "utc_now",
    # dict
    "DictUtil",
    # dir
    "DirUtil",
    # email
    "EmailHandler",
    "EmailHandlerError",
    # excel
    "ExcelUtil",
    # file
    "FileUtil",
    # hash
    "HashUtil",
    # http_client
    "ClientRequest",
    "ClientResponse",
    # list
    "ListUtil",
    # mdf
    "MDFReader",
    # metaclass
    "metaclass_factory",
    # otp
    "OTPService",
    # path
    "PathUtil",
    # single_instance
    "InstanceScope",
    "SingleInstance",
    # systray
    "SystemTray",
    # timer
    "Timer",
    # windows
    "WindowsUtil",
    # zip
    "ZipUtil",
]
