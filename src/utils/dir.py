"""Directory utility functions."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from dirsync import sync as _dirsync


class DirUtil:
    """Utility class for common directory operations."""

    @staticmethod
    def exists(dir_path: str) -> bool:
        """Check if a directory exists."""
        return Path(dir_path).exists()

    @staticmethod
    def is_dir(path: str) -> bool:
        """Check whether the given path is a directory."""
        return Path(path).is_dir()

    @staticmethod
    def is_empty(dir_path: str) -> bool:
        """Return ``True`` if the directory exists but contains no entries."""
        p = Path(dir_path)
        return p.is_dir() and not any(p.iterdir())

    @staticmethod
    def rename(src_dir: str, new_name: str) -> None:
        """Rename a directory.  *new_name* may be relative (same parent) or absolute."""
        src = Path(src_dir)
        new_path = Path(new_name)
        if not new_path.is_absolute():
            new_path = src.parent / new_name
        src.rename(new_path)

    @staticmethod
    def remove(dir_path: str) -> None:
        """Remove a directory and all its contents (no-op if missing)."""
        p = Path(dir_path)
        if p.exists():
            shutil.rmtree(p)

    @staticmethod
    def copy(src_dir: str, dest_dir: str) -> None:
        """Recursively copy *src_dir* to *dest_dir*."""
        shutil.copytree(src_dir, dest_dir)

    @staticmethod
    def sync(src_dir: str, dest_dir: str, *, purge: bool = True, content: bool = True, **kwargs) -> None:
        """Synchronize two directories using *dirsync*."""
        _dirsync(src_dir, dest_dir, 'sync', purge=purge, content=content,
                 logger=logging.getLogger('null'), **kwargs)

    @staticmethod
    def make(dir_path: str, exist_ok: bool = False) -> None:
        """Create a directory (and parents if needed)."""
        Path(dir_path).mkdir(parents=True, exist_ok=exist_ok)

    @staticmethod
    def list_dirs(parent_dir: str) -> list[str]:
        """List all immediate subdirectories in *parent_dir*."""
        return sorted(str(p) for p in Path(parent_dir).iterdir() if p.is_dir())

    @staticmethod
    def list_files(dir_path: str, pattern: str = "*", recursive: bool = False) -> list[str]:
        """List files matching *pattern*.  Use ``recursive=True`` for ``**``."""
        p = Path(dir_path)
        glob_fn = p.rglob if recursive else p.glob
        return sorted(str(f) for f in glob_fn(pattern) if f.is_file())

    @staticmethod
    def size(dir_path: str) -> int:
        """Total size of all files in *dir_path* in bytes (recursive)."""
        total = 0
        for dirpath, _, filenames in os.walk(dir_path):
            for f in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, f))
                except OSError:
                    pass
        return total

    @staticmethod
    def tree(dir_path: str, *, max_depth: int = -1) -> list[str]:
        """Return a flat list of all relative paths under *dir_path*.

        *max_depth* limits traversal depth (``-1`` = unlimited).
        """
        base = Path(dir_path)
        result: list[str] = []

        def _walk(current: Path, depth: int) -> None:
            if max_depth != -1 and depth > max_depth:
                return
            try:
                entries = sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            except PermissionError:
                return
            for entry in entries:
                result.append(str(entry.relative_to(base)))
                if entry.is_dir():
                    _walk(entry, depth + 1)

        _walk(base, 0)
        return result