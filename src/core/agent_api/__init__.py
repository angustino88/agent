"""Client for the Lab Mango backend's signed agent device API (``/agent/...``).

Contract source: lab-mango ``openapi/agents.yml`` and ``core/agents``. Qt-free so it can be used by
the desktop app, the ``enroll``/``status`` command line and tests alike.
"""

from . import errors
from .client import AgentApiClient
from .enrollment import AlreadyEnrolled, canonical_agent_uid, enroll, load_credentials
from .identity import (
    AgentIdentity,
    FileKeyStore,
    IdentityStore,
    KeyringKeyStore,
    default_agent_home,
    default_key_store,
)
from .models import ActivityReport, AgentInfo, BookingResult, MonitoringPolicy
from .outbox import SessionLogOutbox
from .signing import AgentKey

__all__ = [
    "ActivityReport",
    "AgentApiClient",
    "AgentIdentity",
    "AgentInfo",
    "AgentKey",
    "AlreadyEnrolled",
    "BookingResult",
    "FileKeyStore",
    "IdentityStore",
    "KeyringKeyStore",
    "MonitoringPolicy",
    "SessionLogOutbox",
    "canonical_agent_uid",
    "default_agent_home",
    "default_key_store",
    "enroll",
    "errors",
    "load_credentials",
]
