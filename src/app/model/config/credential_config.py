from typing import Optional

import keyring

KEYRING_SERVICE = "labmango_agent"


class CredentialConfig:
    """Secrets kept in the OS credential store. The agent's signing key is managed separately
    by :mod:`src.core.agent_api.identity`."""

    @property
    def otp_master_code(self) -> Optional[str]:
        return keyring.get_password(KEYRING_SERVICE, "otp_master_code")

    def set_otp_master_code(self, otp_master_code: str) -> None:
        keyring.set_password(KEYRING_SERVICE, "otp_master_code", otp_master_code)
