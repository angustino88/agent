"""Enrollment: redeem a one-time grant with a locally generated Ed25519 key.

Workflow (backend ``POST /agent/enrollments``):

1. ``GET /agent/info`` gives the ``backend_key`` that the proof binds to.
2. Generate a key, journal it with a *pending* identity *before* sending, so a lost response is
   retried with the same key instead of silently creating another installation.
3. Send grant, public key and proof. On ``201`` mark the identity enrolled.

The grant is never written to disk or logs.
"""

from __future__ import annotations

import uuid
from typing import Callable, Optional

from . import errors
from .client import AgentApiClient
from .identity import AgentIdentity, IdentityState, IdentityStore
from .signing import AgentKey, enrollment_message

GRANT_PREFIX = "eg_"
REQUIRED_CAPABILITIES = ("enrollment", "request_signature_v1")


class AlreadyEnrolled(errors.AgentApiError):
    """This computer already holds an enrolled identity; unenroll first."""


def canonical_agent_uid(value: str) -> str:
    """The backend compares the header to ``str(UUID(...))``: lowercase, hyphenated."""
    try:
        return str(uuid.UUID(str(value).strip()))
    except (ValueError, AttributeError) as error:
        raise ValueError("Agent UID must be a UUID.") from error


def enroll(
    store: IdentityStore,
    *,
    backend_url: str,
    agent_uid: str,
    grant: str,
    agent_version: str,
    fingerprint: str = "",
    verify: bool | str = True,
    client_factory: Callable[..., AgentApiClient] = AgentApiClient,
    logger: Optional[object] = None,
) -> AgentIdentity:
    agent_uid = canonical_agent_uid(agent_uid)
    grant = (grant or "").strip()
    if not grant.startswith(GRANT_PREFIX):
        raise errors.EnrollmentRejected("Enrollment grant is invalid.", status=None, code="invalid_grant")
    if not agent_version.strip():
        raise ValueError("Agent version is required.")

    backend_url = backend_url.rstrip("/")
    client = client_factory(backend_url, verify=verify, logger=logger)
    info = client.get_info()
    missing = [cap for cap in REQUIRED_CAPABILITIES if not info.supports(cap)]
    if missing:
        raise errors.AgentApiError(f"Backend does not support: {', '.join(missing)}", code="unsupported_backend")
    if not info.backend_key:
        raise errors.AgentApiError("Backend did not report its backend_key.", code="unsupported_backend")

    existing = store.load()
    key: Optional[AgentKey] = None
    if existing is not None and existing.is_enrolled:
        if existing.agent_uid == agent_uid and existing.backend_key == info.backend_key:
            raise AlreadyEnrolled("This computer is already enrolled as this agent.", code="already_enrolled")
        raise AlreadyEnrolled(
            f"This computer is enrolled as agent {existing.agent_uid} on {existing.backend_key}; unenroll first.",
            code="already_enrolled",
        )
    if existing is not None and existing.agent_uid == agent_uid and existing.backend_key == info.backend_key:
        key = store.load_key(existing)  # resume an interrupted enrollment with the same key
    elif existing is not None:
        store.clear()  # abandoned pending enrollment for another identity/backend

    if key is None:
        key = AgentKey.generate()
        store.save_key(agent_uid, key)
    identity = AgentIdentity(
        agent_uid=agent_uid,
        backend_url=backend_url,
        backend_key=info.backend_key,
        key_storage=store.key_store.storage_tier,
        public_key_sha256=key.public_key_sha256,
        state=IdentityState.PENDING,
        agent_version=agent_version,
    )
    store.save(identity)

    proof = key.sign(
        enrollment_message(
            backend_id=info.backend_key,
            agent_uid=agent_uid,
            grant=grant,
            public_key_der=key.public_key_der,
        )
    )
    enrolled = client.enroll(
        grant=grant,
        public_key=key.public_key_b64url,
        proof=proof,
        key_storage=identity.key_storage,
        agent_version=agent_version,
        fingerprint=fingerprint,
    )
    if enrolled.agent_uid and enrolled.agent_uid != agent_uid:
        raise errors.AgentApiError("Backend enrolled a different agent UID.", code="identity_mismatch")
    identity = identity.enrolled(enrolled.enrolled_at)
    store.save(identity)
    return identity


def load_credentials(store: IdentityStore) -> tuple[Optional[AgentIdentity], Optional[AgentKey]]:
    """Return the enrolled identity and its key, or ``(identity_or_None, None)`` when unusable."""
    identity = store.load()
    if identity is None or not identity.is_enrolled:
        return identity, None
    return identity, store.load_key(identity)
