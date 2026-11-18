"""One-Time Password (OTP) generation and validation."""
from __future__ import annotations

import time
import hmac
import secrets


class OTPService:
    """In-memory OTP generation, storage and validation."""

    def __init__(self, length: int = 6, validity_seconds: int = 300):
        self.length = length
        self.validity_seconds = validity_seconds
        self._store: dict[str, dict[str, str | float]] = {}

    def generate_otp(self, username: str) -> str:
        """Generate and store a new OTP for *username*."""
        otp = ''.join(str(secrets.randbelow(10)) for _ in range(self.length))
        expires_at = time.time() + self.validity_seconds
        self._store[username] = {"otp": otp, "expires": expires_at}
        return otp

    def validate_otp(self, username: str, otp: str) -> bool:
        """Validate OTP for *username*.  Removes it on success."""
        entry = self._store.get(username)
        if not entry:
            return False
        if time.time() > entry["expires"]:
            del self._store[username]
            return False
        if not hmac.compare_digest(str(entry["otp"]), otp):
            return False
        del self._store[username]
        return True

    def revoke(self, username: str) -> bool:
        """Manually revoke an OTP for *username*.  Returns ``True`` if it existed."""
        return self._store.pop(username, None) is not None

    def cleanup_expired(self) -> int:
        """Remove expired OTPs from storage.  Returns the number removed."""
        now = time.time()
        expired = [u for u, v in self._store.items() if v["expires"] < now]
        for u in expired:
            del self._store[u]
        return len(expired)