"""Configuration file utilities — YAML, JSON, INI parsers with validation and versioning."""
from __future__ import annotations

import copy
import yaml
import json
import shutil
import datetime
import configparser
from enum import IntEnum
from typing import Any, Optional, Callable
from pathlib import Path
from cerberus import Validator
from packaging.version import parse as parse_version


class MergeMode(IntEnum):
    """Strategy for :func:`merge_dicts`.

    ``UPDATE_AND_ADD`` — update existing keys and add new ones (default).
    ``UPDATE_ONLY``    — update existing keys, ignore new ones.
    ``ADD_ONLY``       — add new keys, never overwrite existing ones.
    """
    UPDATE_AND_ADD = 1
    UPDATE_ONLY    = 2
    ADD_ONLY       = 3


def set_nested_value(d: dict, keys: str | list, value: Any) -> None:
    """Set a value in a nested dict, creating intermediate dicts as needed."""
    if isinstance(keys, str):
        keys = keys.split(".")
    current = d
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

def get_nested_value(d: dict, keys: str | list):
    """Get the value of a nested key in a dict."""
    if isinstance(keys, str):
        keys = keys.split(".")
    current = d
    for key in keys:
        current = current[key]
    return current

def merge_dicts(target: dict, src: dict, mode: int = 1) -> None:
    """
    Merge src dict into target dict recursively.

    mode:
        1: update key-value pair and add new key
        2: update key-value pair only (existing keys)
        3: add new key only (do not update existing keys)
    """
    if mode == 1:
        for key, value in src.items():
            if key not in target or not isinstance(target[key], dict) or target[key] == {}:
                target[key] = copy.deepcopy(value)
            else:
                merge_dicts(target[key], value, mode=1)
    elif mode == 2:
        for key in target.keys():
            if key in src:
                if not isinstance(target[key], dict) or target[key] == {}:
                    target[key] = copy.deepcopy(src[key])
                else:
                    merge_dicts(target[key], src[key], mode=2)
    elif mode == 3:
        for key, value in src.items():
            if key not in target:
                target[key] = copy.deepcopy(value)
            elif isinstance(target[key], dict) and isinstance(value, dict):
                merge_dicts(target[key], value, mode=3)

class _YamlDumper(yaml.SafeDumper):
    # Insert blank lines between top-level objects
    # Inspired by https://stackoverflow.com/a/44284819/3786245
    def write_line_break(self, data=None):
        super().write_line_break(data)
        if len(self.indents) == 1:
            super().write_line_break()


class YamlParserUtil:
    """YAML configuration parser utility."""
    @staticmethod
    def read(config_file: str) -> dict:
        with open(config_file, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file) or {}

    @staticmethod
    def write(config_file: str, config_dict: dict, sort_keys: bool = False):
        with open(config_file, 'w', encoding='utf-8') as file:
            yaml.dump(config_dict, file, sort_keys=sort_keys, indent=4, Dumper=_YamlDumper)

    @staticmethod
    def set(config_file: str, keys: str | list, value: Any):
        if isinstance(keys, str):
            keys = keys.split(".")
        config_dict = YamlParserUtil.read(config_file)
        set_nested_value(config_dict, keys, value)
        YamlParserUtil.write(config_file, config_dict)
    
    @staticmethod
    def get(config_file: str, keys: str | list) -> Any:
        if isinstance(keys, str):
            keys = keys.split(".")
        config_dict = YamlParserUtil.read(config_file)
        return get_nested_value(config_dict, keys)

    @staticmethod
    def exists(config_file: str) -> bool:
        """Check whether the YAML config file exists."""
        return Path(config_file).is_file()

class JsonParserUtil:
    """JSON configuration parser utility."""
    @staticmethod
    def read(config_file: str) -> dict:
        with open(config_file, 'r', encoding='utf-8') as file:
            return json.load(file)

    @staticmethod
    def write(config_file: str, config_dict: dict, sort_keys: bool = False):
        with open(config_file, 'w', encoding='utf-8') as file:
            json.dump(config_dict, file, sort_keys=sort_keys, indent=4)

    @staticmethod
    def update(config_file: str, keys: str | list, value: Any) -> None:
        if isinstance(keys, str):
            keys = keys.split(".")
        config_dict = JsonParserUtil.read(config_file)
        set_nested_value(config_dict, keys, value)
        JsonParserUtil.write(config_file, config_dict)

    @staticmethod
    def exists(config_file: str) -> bool:
        """Check whether the JSON config file exists."""
        return Path(config_file).is_file()


class IniParserUtil:
    """INI configuration parser utility."""
    @staticmethod
    def read(config_file: str) -> dict:
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        config_dict = {}
        for section in config.sections():
            item_dict = {key.lower(): value for key, value in config.items(section)}
            config_dict[section] = item_dict
        return config_dict

    @staticmethod
    def write(config_file: str, config_dict: dict, sort_keys: bool = False):
        config = configparser.ConfigParser()
        if sort_keys:
            sorted_dict = {
                section: dict(sorted(items.items()))
                for section, items in sorted(config_dict.items())
            }
            config.read_dict(sorted_dict)
        else:
            config.read_dict(config_dict)
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    @staticmethod
    def update(config_file: str, keys: str | list, value: Any):
        if isinstance(keys, str):
            keys = keys.split(".")
        if len(keys) != 2:
            raise ValueError("INI config only supports [section, key] for update.")
        section, key = keys
        config = configparser.ConfigParser()
        config.read(config_file, encoding='utf-8')
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, key.lower(), str(value))
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

class ConfigValidator:
    """
    Collects and merges multiple Cerberus schemas, and builds a Validator.
    """
    def __init__(
        self,
        require_all: bool = True,
        allow_unknown: bool = True,
        **kwargs
    ):
        """
        :param require_all: If True, all fields are required by default.
        :param allow_unknown: If True, unknown fields are allowed in validation.
        :param kwargs: Any additional Cerberus Validator options.
        """
        self._schemas: list[dict] = []
        self._require_all = require_all
        self._allow_unknown = allow_unknown
        self._validator_kwargs = kwargs  # Store any extra attributes

    def add_schema(self, schema: dict):
        """
        Add a Cerberus schema to the collection.
        """
        self._schemas.append(copy.deepcopy(schema))

    def clear(self):
        """
        Remove all registered schemas.
        """
        self._schemas.clear()

    def build(self) -> Validator:
        """
        Merge all schemas and return a Cerberus Validator.
        """
        merged = {}
        for schema in self._schemas:
            merge_dicts(merged, schema, mode=1)  # Deep merge
        return Validator(
            merged,
            require_all=self._require_all,
            allow_unknown=self._allow_unknown,
            **self._validator_kwargs  # Pass all extra options to Cerberus Validator
        )
        
class ConfigDefault:
    """
    Defines a config file structure with a header and multiple default sections.
    Useful for modular config assembly.
    """
    def __init__(
        self,
        version_path: str = "version",
    ):
        self._version_path: str = version_path
        self._header: dict = {}
        self._sections: list[dict] = []

    def add_section(self, section: dict):
        """
        Add a default config section from a module or plugin.
        """
        self._sections.append(copy.deepcopy(section))

    def set_header(self, header: dict):
        """Set the config header (e.g., file_info block)."""
        self._header = copy.deepcopy(header)
        self._validate_version_path()

    def _validate_version_path(self):
        """Ensure the version_path exists in the header."""
        parts = self._version_path.split(".")
        data = self._header
        for part in parts:
            if not isinstance(data, dict) or part not in data:
                raise ValueError(
                    f"Version path '{self._version_path}' not found in header: {self._header}"
                )
            data = data[part]

    @property
    def version(self) -> Any:
        """Extract version value from the header using version_path."""
        parts = self._version_path.split(".")
        data = self._header
        for part in parts:
            if not isinstance(data, dict) or part not in data:
                return None
            data = data[part]
        return data

    @property
    def content(self) -> dict:
        """Return the merged result of header + all registered sections."""
        result = copy.deepcopy(self._header)
        for section in self._sections:
            merge_dicts(result, section, mode=1)
        return result

class ConfigFileManager:
    """
    General configuration manager for YAML/JSON/INI files with versioning, merging, and validation.
    """
    def __init__(
        self,
        file_path: str,
        default: dict,
        parser,
        version_cls=parse_version,
        version_path: str = "version",
        backup: bool = True,
        validator: Optional[Any] = None,
        upgrade_hook: Optional[Callable[[dict, dict], dict]] = None
    ):
        """
        :param file_path: Path to the config file
        :param default: Default config dict (with version info)
        :param parser: Parser class/module with `read(path)` and `write(path, data)` methods
        :param version_cls: Callable/class to parse and compare version strings (e.g., parse_version or a custom Version class)
        :param version_path: Dot-separated path to version string in config
        :param backup: Whether to backup old config before overwriting
        :param validator: Optional validator with `.validate(dict)` method
        :param upgrade_hook: Optional function called when the config version changes
        """
        self._file_path: Path = Path(file_path)
        self._default: dict = copy.deepcopy(default)
        self._parser = parser
        self._backup_enabled: bool = backup
        self._validator = validator
        self._upgrade_hook = upgrade_hook
        self._version_path: str = version_path
        self._version_cls = version_cls
        self._config: dict = {}
        if self._validator:
            if not self._validator.validate(self._default):
                raise ValueError(f"Default config validation failed: {self._validator.errors}")

    def load(self, force_defaults: Optional[dict] = None) -> dict:
        """
        Load the config file, applying defaults and merging as needed.
        Optionally force some defaults.
        """
        if not self._file_path.exists():
            self._config = copy.deepcopy(self._default)
            self._apply_force_defaults(force_defaults)
            self._write(self._config)
        else:
            self._config = self._read()
            before = copy.deepcopy(self._config)
            self._sync()
            self._apply_force_defaults(force_defaults)
            if self._config != before:
                self._write(self._config)
        self.validate()
        return self._config

    def reload(self) -> dict:
        """
        Reload the config from disk, discarding in-memory changes.
        """
        self._config = self._read()
        self.validate()
        return self._config

    def _read(self) -> dict:
        """Read the config file using the parser."""
        return self._parser.read(self._file_path)

    def _write(self, config: dict):
        """Write the config dict to file using the parser."""
        try:
            parent = self._file_path.parent
            if parent and not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self._parser.write(self._file_path, config)

    def _backup(self):
        """Backup the current config file if backup is enabled."""
        if self._backup_enabled and self._file_path.exists():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self._file_path.with_name(
                f"{self._file_path.stem}.bak.{timestamp}{self._file_path.suffix}"
            )
            shutil.copy(self._file_path, backup_path)

    def _get_version(self, data: dict) -> Optional[Any]:
        """Extract the version from a config dict using the version path."""
        try:
            keys = self._version_path.split(".")
            for key in keys:
                if not isinstance(data, dict):
                    return None
                data = data.get(key)
                if data is None:
                    return None
            return self._version_cls(data)
        except Exception:
            return None

    def _sync(self):
        """
        Sync the loaded config with the default config if versions differ.
        """
        config_version = self.config_version
        default_version = self.default_version

        if default_version is None:
            raise ValueError("Default config must have a version defined.")

        # version mismatch → upgrade
        if config_version != default_version:
            self._backup()
            user = copy.deepcopy(self._config)
            top_key = self._version_path.split(".")[0]
            user.pop(top_key, None)
            if self._upgrade_hook:
                updated = self._upgrade_hook(copy.deepcopy(self._default), user)
            else:
                updated = copy.deepcopy(self._default)
                merge_dicts(updated, user, mode=2)
            self._config = updated
            self._write(updated)
        else:
            # version matches → still ensure missing defaults are added
            updated = copy.deepcopy(self._default)
            merge_dicts(updated, self._config, mode=2)  # user values override defaults
            self._config = updated

    def _apply_force_defaults(self, force_defaults: Optional[dict]):
        """Merge force_defaults into the config if provided."""
        if force_defaults:
            merge_dicts(self._config, force_defaults, mode=1)

    def validate(self) -> bool:
        """
        Validate the current config using the validator, if provided.
        :return: True if valid, raises ValueError if not.
        """
        if self._validator:
            if not self._validator.validate(self._config):
                raise ValueError(f"Config validation failed: {self._validator.errors}")
        return True

    @property
    def default_version(self) -> Optional[Any]:
        """Return the version from the default config."""
        return self._get_version(self._default)

    @property
    def config_version(self) -> Optional[Any]:
        """Return the version from the loaded config."""
        return self._get_version(self._config)

    @property
    def file_path(self) -> Path:
        """Return the config file path."""
        return self._file_path

    @property
    def default(self) -> dict:
        """Return a copy of the default config."""
        return copy.deepcopy(self._default)

    @property
    def config(self) -> dict:
        """Return the current config dict."""
        return self._config

    def save(self):
        """
        Validate (if validator is set) and write the current config to file.
        """
        self.validate()
        self._write(self._config)

    def get(self, key: str, default=None) -> Any:
        """
        Get a value from the config using dot notation for nested keys.
        """
        keys = key.split(".")
        val = self._config
        for k in keys:
            if not isinstance(val, dict):
                return default
            val = val.get(k)
            if val is None:
                return default
        return val

    def set(self, key: str, value: Any):
        """
        Set a value in the config using dot notation for nested keys.
        Validate before updating the real config.
        """
        temp_config = copy.deepcopy(self._config)
        keys = key.split(".")
        d = temp_config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

        # Validate the temp config
        if self._validator and not self._validator.validate(temp_config):
            raise ValueError(f"Config validation failed: {self._validator.errors}")

        # Only update if valid
        self._config = temp_config

    def reset_to_default(self):
        """
        Reset the config to the default values and write to file.
        """
        self._config = copy.deepcopy(self._default)
        self.validate()
        self._write(self._config)