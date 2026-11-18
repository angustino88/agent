"""Path utility functions."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath


class PathUtil:
    """Cross-platform path manipulation utilities with Windows-first defaults."""

    @staticmethod
    def join(*paths: str) -> str:
        """Join paths robustly, preserving UNC prefixes, normalizing to backslashes."""
        if not paths:
            return ''
        norm_paths: list[str] = []
        for i, p in enumerate(paths):
            p = str(p).replace('/', '\\')
            if i > 0:
                p = p.lstrip('\\')
            norm_paths.append(p)
        result = '\\'.join(norm_paths)
        if norm_paths[0].startswith('\\\\') and not result.startswith('\\\\'):
            result = '\\\\' + result.lstrip('\\')
        elif norm_paths[0].startswith('\\') and not norm_paths[0].startswith('\\\\') and not result.startswith('\\'):
            result = '\\' + result.lstrip('\\')
        return result

    @staticmethod
    def normalize(path: str) -> str:
        """Normalize a path (resolve ``..``, ``.``, redundant separators)."""
        return os.path.normpath(path)

    @staticmethod
    def absolute(path: str) -> str:
        """Return the absolute path."""
        return os.path.abspath(path)

    @staticmethod
    def exists(path: str) -> bool:
        """Check if *path* exists."""
        return os.path.exists(path)

    @staticmethod
    def is_file(path: str) -> bool:
        """Check if *path* is a file."""
        return os.path.isfile(path)

    @staticmethod
    def is_dir(path: str) -> bool:
        """Check if *path* is a directory."""
        return os.path.isdir(path)

    @staticmethod
    def get_filename(path: str) -> str:
        """Get the file name from *path*."""
        return os.path.basename(path)

    @staticmethod
    def get_dirname(path: str) -> str:
        """Get the directory name from *path*."""
        return os.path.dirname(path)

    @staticmethod
    def splitext(path: str) -> tuple[str, str]:
        """Split *path* into ``(root, extension)``."""
        return os.path.splitext(path)

    @staticmethod
    def relative_to(path: str, base: str) -> str:
        """Return *path* relative to *base* (uses ``os.path.relpath``)."""
        return os.path.relpath(path, base)

    @staticmethod
    def common_prefix(*paths: str) -> str:
        """Return the longest common leading component of *paths*."""
        return os.path.commonpath(paths) if paths else ''

    @staticmethod
    def ensure_suffix(path: str, suffix: str) -> str:
        """Ensure *path* ends with *suffix* (e.g. ``'.log'``).

        If the path already has that suffix it is returned unchanged.
        """
        p = Path(path)
        if p.suffix == suffix:
            return path
        return str(p.with_suffix(suffix))

    @staticmethod
    def with_stem(path: str, new_stem: str) -> str:
        """Return *path* with the stem replaced (keeps extension)."""
        p = Path(path)
        return str(p.with_name(new_stem + p.suffix))

    @staticmethod
    def expanduser(path: str) -> str:
        """Expand ``~`` to the user home directory."""
        return os.path.expanduser(path)

    @staticmethod
    def to_posix(path: str) -> str:
        """Convert a Windows-style path to POSIX (forward slashes)."""
        return PurePosixPath(PureWindowsPath(path)).as_posix()
