"""Dictionary utility functions."""
from __future__ import annotations

import copy
from typing import Any, Callable


class DictUtil:
    """Advanced dictionary manipulation utilities with dot-notation traversal."""

    @staticmethod
    def merge(target: dict, src: dict, mode: int = 1) -> None:
        """Merge *src* into *target* recursively (in-place).

        mode:
            1: update existing keys **and** add new ones.
            2: update existing keys only (ignore new keys).
            3: add new keys only (never overwrite existing).
        """
        if mode == 1:
            for key, value in src.items():
                if key not in target or not isinstance(target[key], dict) or target[key] == {}:
                    target[key] = copy.deepcopy(value)
                else:
                    DictUtil.merge(target[key], value, mode=1)
        elif mode == 2:
            for key in target.keys():
                if key in src:
                    if not isinstance(target[key], dict) or target[key] == {}:
                        target[key] = copy.deepcopy(src[key])
                    else:
                        DictUtil.merge(target[key], src[key], mode=2)
        elif mode == 3:
            for key, value in src.items():
                if key not in target:
                    target[key] = copy.deepcopy(value)
                elif isinstance(target[key], dict) and isinstance(value, dict):
                    DictUtil.merge(target[key], value, mode=3)

    # Legacy alias
    merge_dicts = merge

    @staticmethod
    def add(d: dict, keys: str | list, value: Any) -> None:
        """Set a nested value, creating intermediate dicts as needed."""
        if isinstance(keys, str):
            keys = keys.split(".")
        current = d
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    @staticmethod
    def set(d: dict, keys: str | list, value: Any) -> None:
        """Set the value of an **existing** nested key (raises on missing path)."""
        if isinstance(keys, str):
            keys = keys.split(".")
        current = d
        for key in keys[:-1]:
            current = current[key]
        current[keys[-1]] = value

    @staticmethod
    def get(d: dict, keys: str | list, default: Any = KeyError) -> Any:
        """Get a nested value using dot-notation.

        Returns *default* when the path is missing.  Raises ``KeyError``
        if *default* is not given and the key does not exist.
        """
        if isinstance(keys, str):
            keys = keys.split(".")
        current = d
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif default is KeyError:
                raise KeyError(f"Key path not found: {'.'.join(keys)}")
            else:
                return default
        return current

    @staticmethod
    def pop(d: dict, keys: str | list, default: Any = KeyError) -> Any:
        """Remove and return a nested value.  Raises ``KeyError`` when missing (unless *default* given)."""
        if isinstance(keys, str):
            keys = keys.split(".")
        current = d
        for key in keys[:-1]:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif default is KeyError:
                raise KeyError(f"Key path not found: {'.'.join(keys)}")
            else:
                return default
        if default is KeyError:
            return current.pop(keys[-1])
        return current.pop(keys[-1], default)

    @staticmethod
    def deep_copy(d: dict) -> dict:
        """Return a deep copy of *d*."""
        return copy.deepcopy(d)

    @staticmethod
    def keys_exist(d: dict, keys: str | list) -> bool:
        """Check if a nested key path exists in *d*."""
        if isinstance(keys, str):
            keys = keys.split(".")
        current = d
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        return True

    @staticmethod
    def flatten(d: dict, sep: str = ".", prefix: str = "") -> dict[str, Any]:
        """Flatten a nested dict into a single-level dict with compound keys.

        Example::

            flatten({"a": {"b": 1, "c": 2}}) → {"a.b": 1, "a.c": 2}
        """
        items: dict[str, Any] = {}
        for key, value in d.items():
            full_key = f"{prefix}{sep}{key}" if prefix else key
            if isinstance(value, dict):
                items.update(DictUtil.flatten(value, sep=sep, prefix=full_key))
            else:
                items[full_key] = value
        return items

    @staticmethod
    def unflatten(d: dict[str, Any], sep: str = ".") -> dict:
        """Unflatten a single-level dict back into a nested dict.

        Example::

            unflatten({"a.b": 1, "a.c": 2}) → {"a": {"b": 1, "c": 2}}
        """
        result: dict = {}
        for compound_key, value in d.items():
            DictUtil.add(result, compound_key.split(sep), value)
        return result

    @staticmethod
    def diff(a: dict, b: dict) -> dict[str, tuple[Any, Any]]:
        """Return a dict of keys where *a* and *b* differ.

        Only compares flat (top-level) keys.  Each entry is
        ``{key: (value_in_a, value_in_b)}``; missing keys use ``KeyError``.
        """
        all_keys = set(a) | set(b)
        diffs: dict[str, tuple[Any, Any]] = {}
        for key in all_keys:
            va = a.get(key, KeyError)
            vb = b.get(key, KeyError)
            if va != vb:
                diffs[key] = (va, vb)
        return diffs

    @staticmethod
    def walk(d: dict, visitor: Callable[[str, Any], None], prefix: str = "") -> None:
        """Depth-first walk over every leaf value, calling ``visitor(key_path, value)``."""
        for key, value in d.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                DictUtil.walk(value, visitor, prefix=full)
            else:
                visitor(full, value)
