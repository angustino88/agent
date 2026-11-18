from ...utils.otp import OTPService

class OTPManager:
    def __init__(
        self,
        primary_sender,
        secondary_sender=None,
        length=6,
        validity_seconds=300
    ):
        self._primary_sender = primary_sender
        self._secondary_sender = secondary_sender
        self._otp_service = OTPService(length=length, validity_seconds=validity_seconds)

    def generate_otp(self, username: str) -> str:
        """Generate and store a new OTP for the user."""
        return self._otp_service.generate_otp(username)

    def send_otp(self, username: str) -> str:
        """
        Generate, store, and send a new OTP for the user.
        Returns the OTP.
        """
        otp = self.generate_otp(username)
        last_exception = None
        try:
            response = self._primary_sender.send_otp_event(username, otp)
            if not getattr(response, "success", True):
                raise Exception("Primary API service failed")
            return otp
        except Exception as e:
            last_exception = e
            if self._secondary_sender:
                try:
                    response = self._secondary_sender.send_otp_event(username, otp)
                    if not getattr(response, "success", True):
                        raise Exception("Secondary API service failed")
                    return otp
                except Exception as e2:
                    last_exception = e2
        raise Exception(f"Failed to send OTP for {username}: {last_exception}")

    def validate_otp(self, username: str, otp: str) -> bool:
        """Validate the OTP for the user."""
        return self._otp_service.validate_otp(username, otp)

    def cleanup_expired(self):
        """Remove expired OTPs from storage."""
        self._otp_service.cleanup_expired()

    def get_otp_expiry(self, username: str) -> int:
        """Return seconds left until OTP expires for the user, or -1 if not found."""
        if hasattr(self._otp_service, "get_otp_expiry"):
            return self._otp_service.get_otp_expiry(username)
        return -1