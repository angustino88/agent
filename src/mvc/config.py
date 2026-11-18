"""MVC config annotation markers.

Provides typed field markers that can be attached to Pydantic model fields via
``Annotated``.  The companion ``MarkedConfig`` base class introspects these
markers at runtime so that cross-cutting concerns (e.g. directory creation,
env-var resolution) are driven by field declarations rather than manually
maintained lists.

Usage
-----
::

    from src.mvc.config import MarkedConfig, RuntimeDir, EnvOverride

    class AppConfig(MarkedConfig):
        LOG_DIR:  RuntimeDir  = "/var/log/myapp"
        DATA_DIR: RuntimeDir  = "/var/data/myapp"
        API_URL:  EnvOverride = "http://localhost:8080"

    cfg = AppConfig()
    cfg.runtime_dirs   # → ("/var/log/myapp", "/var/data/myapp")

Adding a new marker type
------------------------
1. Subclass ``_FieldMarker`` with a docstring describing its purpose.
2. Define a ``TypeAlias`` using ``Annotated[str, YourMarker()]``.
3. Add it to ``__all__``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, get_type_hints

from pydantic import BaseModel


__all__ = [
    # Base
    "_FieldMarker",
    "MarkedConfig",
    # Marker types
    "RuntimeDir",
    "BundledPath",
    "LogFile",
    "ConfigFile",
    "SecretField",
    "ServiceUrl",
    "EnvOverride",
]


# ---------------------------------------------------------------------------
# Marker base
# ---------------------------------------------------------------------------

class _FieldMarker:
    """Abstract sentinel base for all field annotation markers.

    Subclass to create a new marker kind — no methods required::

        class MyMarker(_FieldMarker):
            '''Fields that should be ... '''

    Then expose a type alias::

        MyKind = Annotated[str, MyMarker()]
    """


# ---------------------------------------------------------------------------
# Concrete markers
# ---------------------------------------------------------------------------

class _RuntimeDirMarker(_FieldMarker):
    """The annotated field is a directory path that must be created before the
    application runs.  Discovered and created by ``BaseMainModel._make_runtime_dirs``
    via ``MarkedConfig.runtime_dirs``."""


class _EnvOverrideMarker(_FieldMarker):
    """The annotated field may be overridden at runtime via an environment
    variable whose name matches the field name (upper-cased).
    Consumed by ``MarkedConfig.apply_env_overrides()``."""


class _BundledPathMarker(_FieldMarker):
    """The annotated field is a path to a read-only resource bundled inside
    the executable (``_internal/`` in a PyInstaller one-dir build).
    Rooted at BUNDLE_DIR, not ROOT_DIR.
    Use ``MarkedConfig.validate_bundle()`` to assert all bundled paths exist."""


class _LogFileMarker(_FieldMarker):
    """The annotated field is a log file path.
    Its parent directory is included in ``runtime_dirs`` automatically.
    Use ``MarkedConfig.log_files`` to enumerate for handler setup or rotation."""


class _ConfigFileMarker(_FieldMarker):
    """The annotated field is a configuration file path.
    Use ``MarkedConfig.config_files`` to enumerate for default-copy-if-missing logic."""


class _SecretFieldMarker(_FieldMarker):
    """The annotated field holds sensitive data (token, password, key path).
    ``MarkedConfig.__repr__`` masks these fields automatically.
    Enumerate with ``MarkedConfig.secret_fields``."""


class _ServiceUrlMarker(_FieldMarker):
    """The annotated field is a base URL for an external service.
    Enumerate with ``MarkedConfig.service_urls`` for health-check / connectivity probes."""


# ---------------------------------------------------------------------------
# Type aliases  (use these on field declarations)
# ---------------------------------------------------------------------------

RuntimeDir  = Annotated[str, _RuntimeDirMarker()]
"""A directory path that must exist before the app runs (mkdir on startup)."""

BundledPath = Annotated[str, _BundledPathMarker()]
"""A read-only path inside the PyInstaller bundle (_internal/)."""

LogFile     = Annotated[str, _LogFileMarker()]
"""A log file path — parent dir is auto-created with RuntimeDir dirs."""

ConfigFile  = Annotated[str, _ConfigFileMarker()]
"""A configuration file path — copy default if missing at startup."""

SecretField = Annotated[str, _SecretFieldMarker()]
"""A sensitive field — masked in __repr__ and log output."""

ServiceUrl  = Annotated[str, _ServiceUrlMarker()]
"""A base URL for an external service — enumerate for health-check probes."""

EnvOverride = Annotated[str, _EnvOverrideMarker()]
"""A string field whose value may be overridden by a same-named env var."""


# ---------------------------------------------------------------------------
# MarkedConfig  (Pydantic base class)
# ---------------------------------------------------------------------------

class MarkedConfig(BaseModel):
    """Pydantic ``BaseModel`` subclass that understands field markers.

    Provides:

    * ``fields_marked_as(marker)`` — generic introspection for any ``_FieldMarker`` subclass.
    * ``runtime_dirs``             — all ``RuntimeDir``-annotated field values (mkdir on startup).
    * ``bundled_paths``            — all ``BundledPath``-annotated field values.
    * ``log_files``                — all ``LogFile``-annotated field values.
    * ``config_files``             — all ``ConfigFile``-annotated field values.
    * ``secret_fields``            — names (not values) of ``SecretField`` fields.
    * ``service_urls``             — all ``ServiceUrl``-annotated field values.
    * ``validate_bundle()``        — assert all BundledPath fields exist on disk (frozen builds).
    * ``apply_env_overrides()``    — apply env-var values to ``EnvOverride`` fields.
    * ``__repr__``                 — masks ``SecretField`` values automatically.
    """

    # ---- generic introspection ---------------------------------------------

    def fields_marked_as(self, marker: type[_FieldMarker]) -> tuple[str, ...]:
        """Return the values of all fields annotated with *marker*.

        Example::

            cfg.fields_marked_as(_RuntimeDirMarker)   # same as cfg.runtime_dirs
        """
        hints = get_type_hints(type(self), include_extras=True)
        return tuple(
            getattr(self, name)
            for name, hint in hints.items()
            if any(
                isinstance(m, marker)
                for m in getattr(hint, "__metadata__", ())
            )
        )

    # ---- convenience properties / methods ----------------------------------

    @property
    def runtime_dirs(self) -> tuple[str, ...]:
        """All ``RuntimeDir``-annotated field values.
        Passed to ``BaseMainModel._make_runtime_dirs(*cfg.runtime_dirs)``."""
        return self.fields_marked_as(_RuntimeDirMarker)

    @property
    def bundled_paths(self) -> tuple[str, ...]:
        """All ``BundledPath``-annotated field values (read-only, inside _internal/)."""
        return self.fields_marked_as(_BundledPathMarker)

    @property
    def log_files(self) -> tuple[str, ...]:
        """All ``LogFile``-annotated field values."""
        return self.fields_marked_as(_LogFileMarker)

    @property
    def config_files(self) -> tuple[str, ...]:
        """All ``ConfigFile``-annotated field values."""
        return self.fields_marked_as(_ConfigFileMarker)

    @property
    def secret_fields(self) -> tuple[str, ...]:
        """Names (not values) of all ``SecretField``-annotated fields."""
        hints = get_type_hints(type(self), include_extras=True)
        return tuple(
            name for name, hint in hints.items()
            if any(isinstance(m, _SecretFieldMarker) for m in getattr(hint, "__metadata__", ()))
        )

    @property
    def service_urls(self) -> tuple[str, ...]:
        """All ``ServiceUrl``-annotated field values."""
        return self.fields_marked_as(_ServiceUrlMarker)

    def validate_bundle(self) -> None:
        """Assert every ``BundledPath`` field exists on disk.
        Call at startup in frozen (PyInstaller) builds to catch missing resources early.
        """
        import sys
        if not getattr(sys, 'frozen', False):
            return
        missing = [p for p in self.bundled_paths if not Path(p).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing bundled resources: {missing}. "
                "Check --add-data entries in build_config.py."
            )

    def __repr__(self) -> str:
        secrets = set(self.secret_fields)
        fields = ", ".join(
            f"{k}={'***' if k in secrets else repr(v)}"
            for k, v in self.__dict__.items()
        )
        return f"{type(self).__name__}({fields})"

    def apply_env_overrides(self) -> None:
        """Override ``EnvOverride``-annotated fields from environment variables.

        The env-var name is the field name uppercased.  Skipped when the model
        is frozen (``Config.frozen = True``).
        """
        if getattr(self.model_config, "frozen", False) or getattr(
            getattr(self, "Config", None), "frozen", False
        ):
            return
        hints = get_type_hints(type(self), include_extras=True)
        for name, hint in hints.items():
            if any(isinstance(m, _EnvOverrideMarker) for m in getattr(hint, "__metadata__", ())):
                env_val = os.environ.get(name.upper())
                if env_val is not None:
                    object.__setattr__(self, name, env_val)
