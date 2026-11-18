"""Service gateway: agent login, synced configuration, OTP delivery and package updates.

The gateway is the control plane shared by Lab Mango tools. It is separate from the department
backend (see :mod:`backend_model`), which the agent reaches with its own signed identity.
"""

from __future__ import annotations

from typing import Optional

from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.model.update_checker import PackageUpdate, UpdateChecker
from src.core.gateway import LabMangoGatewayService
from src.mvc.base_model import BaseModel
from src.mvc.task_schedule import task
from src.service_gateway import GatewayClient


class GatewayModel(BaseModel):
    def __init__(self):
        super().__init__()
        self._client: Optional[GatewayClient] = None
        self._service: Optional[LabMangoGatewayService] = None
        self._update_checker: Optional[UpdateChecker] = None

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._app_settings = self.model.config_model.app_settings
        self._credential_config = self.model.config_model.credential_config
        self._logger = self.model.logging_model.system_logger
        debug = self.model.config_model.app_config_dynamic.app_debug_enabled
        computer_name = self.model.computer_model.computer_name

        self._client = GatewayClient(
            base_url=self._app_config.SERVICE_GATEWAY_URL,
            auth_scheme="Bearer",
            logger=self._logger if debug else None,
            printer=print if self._app_config.IS_DEVELOPMENT else None,
            token_refresh_callback=self.refresh_token,
            verify=self._app_settings.tls_verify,
            # Plain-HTTP fallback only while TLS checks are off (gateway without a certificate).
            allow_http_fallback=not self._app_settings.tls_verify_enabled,
        )
        self._service = LabMangoGatewayService(self._client, computer_name, f"AGENT_{computer_name}")
        self._update_checker = UpdateChecker(self._service, self._logger)
        self.login()

    # ------------------------------------------------------------------ accessors

    @property
    def client(self) -> GatewayClient:
        return self._client

    @property
    def service(self) -> LabMangoGatewayService:
        return self._service

    @property
    def url(self) -> str:
        return self._client.base_url if self._client else self._app_config.SERVICE_GATEWAY_URL

    @property
    def otp_master_code(self) -> Optional[str]:
        return self._credential_config.otp_master_code

    def check_alive(self) -> bool:
        return self._client.check_alive(timeout=3) if self._client else False

    def check_package_update(self, current_version: str) -> PackageUpdate:
        return self._update_checker.check(current_version)

    # ------------------------------------------------------------------ authentication

    def _apply_tokens(self, data: dict, action: str) -> bool:
        access, refresh = data.get("access"), data.get("refresh")
        if access:
            self._client.auth_value = access.strip()
        if refresh:
            self._client.refresh_token = refresh.strip()
        self._logger.info(f"[Gateway] {action}: access token {'set' if access else 'missing'}")
        return bool(access)

    def login(self) -> bool:
        try:
            response = self._service.login()
            if not response.success or not response.data:
                self._logger.warning("[Gateway] Login failed.")
                return False
            return self._apply_tokens(response.data, "login")
        except Exception as e:
            self._logger.error(f"[Gateway] Login error: {e}")
            return False

    @task(schedule=TaskScheduleConfig.GATEWAY_TOKEN_REFRESH, heavy=True)
    def refresh_token(self) -> bool:
        try:
            refresh_token = self._client.refresh_token
            if not refresh_token:
                return self.login()
            response = self._service.refresh_token(refresh_token)
            if not response.success or not response.data:
                self._logger.warning("[Gateway] Token refresh failed; logging in again.")
                return self.login()
            return self._apply_tokens(response.data, "token refresh")
        except Exception as e:
            self._logger.error(f"[Gateway] Token refresh error: {e}")
            return self.login()

    # ------------------------------------------------------------------ configuration sync

    @task(schedule=TaskScheduleConfig.GATEWAY_CONFIG_SYNC, heavy=True)
    def sync_config(self, raise_on_error: bool = False) -> None:
        """Pull safe mode, OTP master code and the web app URL from the gateway."""
        for step in (self._sync_safe_mode, self._sync_otp_master_code, self._sync_frontend_url):
            try:
                step()
            except Exception as e:
                self._logger.warning(f"[Gateway] {step.__name__.lstrip('_')} failed: {e}")
                if raise_on_error:
                    raise RuntimeError(f"Gateway configuration sync failed: {e}") from e

    def _fetch(self, call, what: str) -> dict:
        response = call(timeout=3)
        if not response or not response.success or not isinstance(response.data, dict):
            raise RuntimeError(f"could not fetch {what}")
        return response.data

    def _sync_safe_mode(self) -> None:
        enabled = bool(self._fetch(self._service.get_safe_mode_status, "safe mode").get("safe_mode_enabled", False))
        if enabled != self._app_settings.safe_mode:
            self._app_settings.set_safe_mode(enabled)
            self._logger.info(f"[Gateway] Safe mode {'enabled' if enabled else 'disabled'}.")

    def _sync_otp_master_code(self) -> None:
        code = (self._fetch(self._service.get_otp_master_code, "OTP master code").get("otp_code") or "").strip()
        if code and code != self._credential_config.otp_master_code:
            self._credential_config.set_otp_master_code(code)
            self._logger.info("[Gateway] OTP master code updated.")

    def _sync_frontend_url(self) -> None:
        url = (
            self._fetch(self._service.get_prod_server_config, "server configuration").get("frontend_url") or ""
        ).strip()
        if url and url != self._app_settings.frontend_url:
            self._app_settings.set_frontend_url(url)
            self._logger.info("[Gateway] Web app URL updated.")
