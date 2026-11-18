"""Ed25519 key handling and the exact byte strings the backend verifies.

The backend (``core/agents/application.py`` in lab-mango) defines two signed messages:

* Enrollment proof, NUL-joined::

    b"labmango-enroll-v1", backend_id, agent_uid, sha256_hex(grant), public_key_der

* Request signature, NUL-joined::

    b"labmango-agent-request-v1", backend_id, agent_uid, METHOD, path, timestamp, nonce,
    sha256_hex(raw_body)

Public keys travel as base64url (unpadded) DER SubjectPublicKeyInfo. Signatures and nonces are
base64url, unpadded. Any change here must be mirrored byte-for-byte on the backend.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ENROLLMENT_CONTEXT = b"labmango-enroll-v1"
REQUEST_SIGNATURE_CONTEXT = b"labmango-agent-request-v1"
NONCE_BYTES = 16


def b64url(data: bytes) -> str:
    """Unpadded base64url, as the backend expects."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_nonce() -> str:
    return b64url(secrets.token_bytes(NONCE_BYTES))


def enrollment_message(*, backend_id: str, agent_uid: str, grant: str, public_key_der: bytes) -> bytes:
    return b"\0".join(
        (
            ENROLLMENT_CONTEXT,
            backend_id.encode("ascii"),
            agent_uid.encode("ascii"),
            sha256_hex(grant.encode("utf-8")).encode("ascii"),
            public_key_der,
        )
    )


def request_message(
    *,
    backend_id: str,
    agent_uid: str,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> bytes:
    return b"\0".join(
        (
            REQUEST_SIGNATURE_CONTEXT,
            backend_id.encode("ascii"),
            agent_uid.encode("ascii"),
            method.upper().encode("ascii"),
            path.encode("utf-8"),
            timestamp.encode("ascii"),
            nonce.encode("ascii"),
            sha256_hex(body).encode("ascii"),
        )
    )


@dataclass(frozen=True)
class AgentKey:
    """A device-held Ed25519 private key. Never log, queue or transmit :pyattr:`private_bytes`."""

    _private: Ed25519PrivateKey

    @classmethod
    def generate(cls) -> "AgentKey":
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_private_bytes(cls, raw: bytes) -> "AgentKey":
        return cls(Ed25519PrivateKey.from_private_bytes(raw))

    @property
    def private_bytes(self) -> bytes:
        return self._private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

    @property
    def public_key_der(self) -> bytes:
        return self._private.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @property
    def public_key_b64url(self) -> str:
        return b64url(self.public_key_der)

    @property
    def public_key_sha256(self) -> str:
        return sha256_hex(self.public_key_der)

    def sign(self, message: bytes) -> str:
        return b64url(self._private.sign(message))

    def __repr__(self) -> str:  # never expose key material
        return f"AgentKey(public_sha256={self.public_key_sha256[:16]}...)"
