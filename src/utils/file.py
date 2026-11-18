"""File utility functions."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


class FileUtil:
    """Advanced file manipulation utilities."""

    @staticmethod
    def filename(path: str, with_path: bool = False) -> str:
        """Get file name from *path*, optionally with full path (without extension)."""
        p = Path(path)
        return str(p.with_suffix('')) if with_path else p.stem

    @staticmethod
    def file_extension(path: str) -> str:
        """Get file extension (e.g. ``'.txt'``)."""
        return Path(path).suffix

    @staticmethod
    def is_writable(path: str) -> bool:
        """Check whether a file is writable (or can be created at the location)."""
        p = Path(path)
        if p.exists():
            return FileUtil.has_permission(path, os.W_OK) and not FileUtil.is_locked(path)
        return p.parent.exists()

    @staticmethod
    def is_locked(path: str) -> bool:
        """Check whether a file is open / locked by another process."""
        p = Path(path)
        if not p.exists():
            return False
        try:
            FileUtil.rename(path, path)
            return False
        except Exception:
            return True

    @staticmethod
    def has_permission(path: str, mode: int) -> bool:
        """Check file permission (``os.R_OK``, ``os.W_OK``, ``os.X_OK``, ``os.F_OK``)."""
        return os.access(path, mode)

    @staticmethod
    def remove(path: str) -> None:
        """Remove a file if it exists."""
        p = Path(path)
        if p.exists():
            p.unlink()

    @staticmethod
    def rename(src: str, dst: str) -> None:
        """Rename / move a file.  *dst* may be relative (same dir) or absolute."""
        p = Path(src)
        new_path = Path(dst)
        if not new_path.is_absolute():
            new_path = p.parent / new_path
        p.rename(new_path)

    @staticmethod
    def move(src: str, dst: str) -> str:
        """Move a file to *dst* (file or directory) and return the new path."""
        return shutil.move(src, dst)

    @staticmethod
    def exists(path: str) -> bool:
        """Check if file or directory exists."""
        return Path(path).exists()

    @staticmethod
    def is_file(path: str) -> bool:
        """Check whether path is a file."""
        return Path(path).is_file()

    @staticmethod
    def copy(src: str, dst_dir: str) -> None:
        """Copy file to target directory."""
        shutil.copy(src, dst_dir)

    @staticmethod
    def touch(path: str) -> None:
        """Create an empty file (or update mtime if it already exists)."""
        Path(path).touch()

    @staticmethod
    def read_lines(path: str, mode: str = 'r', errors: str | None = None) -> list[str]:
        """Read file contents as a list of lines."""
        with open(path, mode, errors=errors, encoding='utf-8') as f:
            return f.readlines()

    @staticmethod
    def write_lines(
        path: str,
        lines: list[str] | str,
        mode: str = 'w',
        newline: bool = True,
    ) -> None:
        """Write lines to a file.  If *newline*, join list items with ``\\n``."""
        with open(path, mode, encoding='utf-8') as f:
            if isinstance(lines, list):
                for idx, line in enumerate(lines):
                    if newline and idx < len(lines) - 1:
                        f.write(str(line) + '\n')
                    else:
                        f.write(str(line))
            else:
                f.write(str(lines))

    @staticmethod
    def list_files(directory: str, pattern: str = "*") -> list[str]:
        """List all files in *directory* matching *pattern*."""
        return sorted(str(p) for p in Path(directory).glob(pattern) if p.is_file())

    @staticmethod
    def file_size(path: str) -> int:
        """Get the size of a file in bytes."""
        return os.path.getsize(path)

    @staticmethod
    def read_text(path: str, encoding: str = 'utf-8') -> str:
        """Read the entire file as a string."""
        return Path(path).read_text(encoding=encoding)

    @staticmethod
    def write_text(path: str, text: str, encoding: str = 'utf-8') -> None:
        """Write a string to a file (overwrites)."""
        Path(path).write_text(text, encoding=encoding)

    @staticmethod
    def read_json(path: str, encoding: str = 'utf-8') -> Any:
        """Read and parse a JSON file."""
        with open(path, 'r', encoding=encoding) as f:
            return json.load(f)

    @staticmethod
    def write_json(path: str, data: Any, *, indent: int = 2, encoding: str = 'utf-8') -> None:
        """Write *data* to a JSON file."""
        with open(path, 'w', encoding=encoding) as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)

    @staticmethod
    def atomic_write(path: str, text: str, encoding: str = 'utf-8') -> None:
        """Write text atomically by writing to a temp file and renaming."""
        p = Path(path)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding=encoding) as f:
                f.write(text)
            os.replace(tmp, path)
        except BaseException:
            os.unlink(tmp)
            raise
