"""Persistent agent identity: non-secret state on disk, private key in a key store.

The identity file never contains the grant or the private key. The private key lives in a
:class:`KeyStore`; the OS keystore (``keyring``: Windows Credential Manager, macOS Keychain,
Secret Service) is preferred and the file store is a software fallback.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Optional, Protocol

from .signing import AgentKey, b64url, b64url_decode

KEYRING_SERVICE = "labmango_agent"


class IdentityState:
    PENDING = "pending"  # key generated and journaled, enrollment not confirmed yet
    ENROLLED = "enrolled"


@dataclass(frozen=True)
class AgentIdentity:
    agent_uid: str
    backend_url: str
    backend_key: str
    key_storage: str
    public_key_sha256: str
    state: str = IdentityState.PENDING
    agent_version: str = ""
    enrolled_at: Optional[str] = None
    extra: dict = field(default_factory=dict)

    @property
    def is_enrolled(self) -> bool:
        return self.state == IdentityState.ENROLLED

    def enrolled(self, enrolled_at: Optional[str]) -> "AgentIdentity":
        return replace(self, state=IdentityState.ENROLLED, enrolled_at=enrolled_at)


# --------------------------------------------------------------------------- key stores


class KeyStore(Protocol):
    storage_tier: str  # backend KeyStorageEnum: "tpm" | "os_keystore" | "software"

    def load(self, agent_uid: str) -> Optional[AgentKey]: ...

    def save(self, agent_uid: str, key: AgentKey) -> None: ...

    def delete(self, agent_uid: str) -> None: ...


class KeyringKeyStore:
    """Private key in the OS credential store via ``keyring``."""

    storage_tier = "os_keystore"

    def __init__(self, service: str = KEYRING_SERVICE):
        import keyring  # imported lazily: optional on non-desktop hosts

        self._keyring = keyring
        self._service = service

    @staticmethod
    def _name(agent_uid: str) -> str:
        return f"agent_key:{agent_uid}"

    def load(self, agent_uid: str) -> Optional[AgentKey]:
        value = self._keyring.get_password(self._service, self._name(agent_uid))
        return AgentKey.from_private_bytes(b64url_decode(value)) if value else None

    def save(self, agent_uid: str, key: AgentKey) -> None:
        self._keyring.set_password(self._service, self._name(agent_uid), b64url(key.private_bytes))

    def delete(self, agent_uid: str) -> None:
        try:
            self._keyring.delete_password(self._service, self._name(agent_uid))
        except Exception:
            pass


class FileKeyStore:
    """Software fallback: one raw key file per identity, owner-only permissions where supported."""

    storage_tier = "software"

    def __init__(self, directory: str | os.PathLike):
        self._dir = Path(directory)

    def _path(self, agent_uid: str) -> Path:
        return self._dir / f"{agent_uid}.key"

    def load(self, agent_uid: str) -> Optional[AgentKey]:
        path = self._path(agent_uid)
        if not path.exists():
            return None
        return AgentKey.from_private_bytes(b64url_decode(path.read_text(encoding="ascii").strip()))

    def save(self, agent_uid: str, key: AgentKey) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            os.chmod(self._dir, 0o700)
        _atomic_write(self._path(agent_uid), b64url(key.private_bytes), private=True)

    def delete(self, agent_uid: str) -> None:
        try:
            self._path(agent_uid).unlink()
        except FileNotFoundError:
            pass


def default_key_store(fallback_dir: str | os.PathLike) -> KeyStore:
    """OS keystore when a usable backend exists, otherwise the file store."""
    try:
        import keyring
        from keyring.backends import fail

        if not isinstance(keyring.get_keyring(), fail.Keyring):
            return KeyringKeyStore()
    except Exception:
        pass
    return FileKeyStore(fallback_dir)


# --------------------------------------------------------------------------- identity store


class IdentityStore:
    """Reads and writes ``identity.json`` atomically and pairs it with a key store."""

    FILE_NAME = "identity.json"

    def __init__(self, directory: str | os.PathLike, key_store: Optional[KeyStore] = None):
        self._dir = Path(directory)
        self._key_store = key_store or default_key_store(self._dir / "keys")

    @property
    def directory(self) -> Path:
        return self._dir

    @property
    def key_store(self) -> KeyStore:
        return self._key_store

    @property
    def path(self) -> Path:
        return self._dir / self.FILE_NAME

    def load(self) -> Optional[AgentIdentity]:
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            known = {f for f in AgentIdentity.__dataclass_fields__}
            return AgentIdentity(**{k: v for k, v in raw.items() if k in known})
        except (OSError, ValueError, TypeError):
            return None

    def save(self, identity: AgentIdentity) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.path, json.dumps(asdict(identity), indent=2, sort_keys=True))

    def load_key(self, identity: AgentIdentity) -> Optional[AgentKey]:
        key = self._key_store.load(identity.agent_uid)
        if key is not None and key.public_key_sha256 != identity.public_key_sha256:
            return None  # key store does not hold this identity's key; never use a mismatched key
        return key

    def save_key(self, agent_uid: str, key: AgentKey) -> None:
        self._key_store.save(agent_uid, key)

    def clear(self) -> None:
        identity = self.load()
        if identity is not None:
            self._key_store.delete(identity.agent_uid)
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def _atomic_write(path: Path, text: str, *, private: bool = False) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        if private and os.name == "posix":
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def default_agent_home(app_name: str = "LabMango") -> Path:
    """Machine-wide agent state folder, shared by the desktop app and the command line.

    ``LABMANGO_AGENT_HOME`` overrides it. Windows: ``%PROGRAMDATA%\\<app>\\agent``; elsewhere
    ``/var/lib/<app>/agent`` when writable, else ``~/.<app>/agent``.
    """
    override = os.environ.get("LABMANGO_AGENT_HOME")
    if override:
        return Path(override)
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / app_name / "agent"
    system = Path("/var/lib") / app_name.lower() / "agent"
    if os.access(system.parent if system.parent.exists() else Path("/var/lib"), os.W_OK):
        return system
    return Path.home() / f".{app_name.lower()}" / "agent"
