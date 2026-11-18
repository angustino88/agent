import keyring
from typing import Optional

class CredentialConfig:
    def __init__(self):
        pass

    @property
    def prod_api_key(self) -> Optional[str]:
        return keyring.get_password("labmango_agent", "prod_api_key")
    
    def set_prod_api_key(self, api_key: str):
        keyring.set_password("labmango_agent", "prod_api_key", api_key)

    @property
    def otp_master_code(self) -> Optional[str]:
        return keyring.get_password("labmango_agent", "otp_master_code")

    def set_otp_master_code(self, otp_master_code: str):
        keyring.set_password("labmango_agent", "otp_master_code", otp_master_code)