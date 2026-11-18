import requests
from datetime import datetime
from src.mvc.base_model import BaseModel
from src.mvc.task_schedule import task, Schedule
from src.utils.http_client import ClientRequest
from src.utils.datetime import iso_datetime
from src.service_gateway import GatewayClient
from src.core.api.lab_api_core_service import LabApiCoreService
from src.core.api.lab_api_service_gateway import LabApiServiceGateway
from src.app.model.types.booking_info import BookingInfo
from src.app.model.types.booking_status import BookingStatus
from src.app.model.types.approval_status import ApprovalStatus
from src.app.model.update_checker import UpdateChecker, PackageUpdate
from src.app.model.config.task_schedule_config import TaskScheduleConfig

class LabApiModel(BaseModel):
    """Orchestrates core and service-gateway API interactions."""

    def __init__(self):
        super().__init__()
        self._client_core = None
        self._client_service_gateway = None
        self._service_core = None
        self._service_gateway = None

    def init(self):
        """Initialize services and clients."""
        # Load dependencies
        self._app_config = self.model.config_model.app_config
        self._app_settings = self.model.config_model.app_settings
        self._app_config_dynamic = self.model.config_model.app_config_dynamic
        self._credential_config = self.model.config_model.credential_config
        self._logger = self.model.logging_model.system_logger
        self._computer_sku = self.model.computer_model.computer_name
        self._source = f"AGENT_{self._computer_sku}"

        # Initialize service-gateway client and service (GatewayClient handles HTTPS→HTTP fallback)
        self._client_service_gateway = GatewayClient(
            base_url=self._app_config.SERVICE_GATEWAY_URL,
            auth_scheme='Bearer',
            logger=self._logger if self._app_config_dynamic.app_debug_enabled else None,
            printer=print if self._app_config.IS_DEVELOPMENT else None,
            token_refresh_callback=self.refresh_service_gateway_token)

        self._service_gateway = LabApiServiceGateway(
            self._client_service_gateway,
            self._computer_sku,
            self._source
        )

        self.login_service_gateway()

        # Initialize core client and service
        self._client_core = ClientRequest(
            base_url=self._app_settings.prod_backend_url,
            auth_value=self._credential_config.prod_api_key,
            logger=self._logger if self._app_config_dynamic.app_debug_enabled else None,
            printer=print if self._app_config.IS_DEVELOPMENT else None
        )
        self._service_core = LabApiCoreService(
            self._client_core,
            self._computer_sku,
            self._source
        )

        # Update checker (needs service gateway & logger)
        self._update_checker = UpdateChecker(self._service_gateway, self._logger)

    @property
    def client(self) -> ClientRequest:
        return self._client_core

    @property
    def service(self) -> LabApiCoreService:
        return self._service_core

    @property
    def service_gateway_client(self) -> GatewayClient:
        return self._client_service_gateway

    @property
    def service_gateway(self) -> LabApiServiceGateway:
        return self._service_gateway

    @property
    def backend_url(self) -> str:
        return self._app_settings.prod_backend_url

    @property
    def frontend_url(self) -> str:
        return self._app_settings.prod_frontend_url

    @property
    def service_gateway_url(self) -> str:
        if self._client_service_gateway:
            return self._client_service_gateway.base_url
        return self._app_config.SERVICE_GATEWAY_URL

    @property
    def otp_master_code(self) -> str:
        return self._credential_config.otp_master_code

    def login_service_gateway(self):
        """Login to service gateway and set tokens."""
        try:
            response = self._service_gateway.login()
            if not response.success or not response.data:
                self._logger.warning("Failed to login to service gateway.")
                return False
            token = response.data.get("access")
            refresh = response.data.get("refresh")
            if token:
                self._client_service_gateway.auth_value = token.strip()
                self._logger.info("Service gateway access token set.")
            if refresh:
                self._client_service_gateway.refresh_token = refresh.strip()
                self._logger.info("Service gateway refresh token set.")
            return True
        except Exception as e:
            self._logger.error(f"Exception in login_service_gateway: {e}")
            return False

    @task(schedule=TaskScheduleConfig.REFRESH_SERVICE_GATEWAY_TOKEN, heavy=True)
    def refresh_service_gateway_token(self):
        """Refresh service-gateway token using the refresh endpoint."""
        try:
            refresh_token = self._client_service_gateway.refresh_token
            if not refresh_token:
                self._logger.warning("No refresh token available, need to login again.")
                return self.login_service_gateway()
            response = self._service_gateway.refresh_token(refresh_token)
            if not response.success or not response.data:
                self._logger.warning("Failed to refresh service gateway token, need to login again.")
                return self.login_service_gateway()
            token = response.data.get("access")
            new_refresh = response.data.get("refresh")
            if token:
                self._client_service_gateway.auth_value = token.strip()
                self._logger.info("Service gateway access token refreshed.")
            if new_refresh:
                self._client_service_gateway.refresh_token = new_refresh.strip()
                self._logger.info("Service gateway refresh token updated.")
            return True
        except Exception as e:
            self._logger.error(f"Exception in refresh_service_gateway_token: {e}")
            return self.login_service_gateway()
    
    @task(schedule=TaskScheduleConfig.SYNC_SERVICE_GATEWAY, heavy=True)
    def sync_service_gateway(self):
        """Sync OTP master code and prod config from service gateway."""
        self.sync_safe_mode()
        self.sync_otp_master_code()
        self.sync_prod_config()

    def sync_otp_master_code(self, raise_on_error: bool = False):
        """Fetch OTP master code from service gateway (with token retry)."""
        try:
            response = self._service_gateway.get_otp_master_code(timeout=3)
            if not response or not response.success or not response.data:
                msg = "Failed to fetch OTP master code from service gateway."
                self._logger.warning(msg)
                if raise_on_error:
                    raise RuntimeError(msg)
                return
            otp_code = response.data.get("otp_code")
            if otp_code and otp_code != self._credential_config.otp_master_code:
                self._credential_config.set_otp_master_code(otp_code.strip())
                self._logger.info("OTP master code updated from service gateway.")
        except Exception as e:
            msg = f"Exception in sync_otp_master_code: {e}"
            self._logger.error(msg)
            if raise_on_error:
                raise RuntimeError(msg) from e

    def sync_prod_config(self, raise_on_error: bool = False):
        """Fetch production server config from service gateway (with token retry)."""
        try:
            response = self._service_gateway.get_prod_server_config(timeout=3)
            if not response or not response.success or not response.data:
                msg = "Failed to fetch production config from service gateway."
                self._logger.warning(msg)
                if raise_on_error:
                    raise RuntimeError(msg)
                return
            data = response.data

            api_key = data.get("api_key")
            if api_key and api_key != self._credential_config.prod_api_key:
                self._credential_config.set_prod_api_key(api_key.strip())
                if self._client_core:
                    self._client_core.auth_value = api_key.strip()
                self._logger.info("API key updated from service gateway.")

            backend_url = data.get("backend_url")
            if backend_url and backend_url != self._app_settings.prod_backend_url:
                self._app_settings.set_prod_backend_url(backend_url.strip())
                if self._client_core:
                    self._client_core.base_url = backend_url.strip()
                self._logger.info("Backend URL updated from service gateway.")

            frontend_url = data.get("frontend_url")
            if frontend_url and frontend_url != self._app_settings.prod_frontend_url:
                self._app_settings.set_prod_frontend_url(frontend_url.strip())
                self._logger.info("Frontend URL updated from service gateway.")
        except Exception as e:
            msg = f"Exception in sync_prod_config: {e}"
            self._logger.error(msg)
            if raise_on_error:
                raise RuntimeError(msg) from e
    
    def sync_safe_mode(self, raise_on_error: bool = False) -> bool:
        """Fetch safe mode status from service gateway (with token retry) and update app settings."""
        try:
            response = self._service_gateway.get_safe_mode_status(timeout=3)
            if not response or not response.success or not response.data:
                msg = "Failed to fetch safe mode status from service gateway."
                self._logger.warning(msg)
                if raise_on_error:
                    raise RuntimeError(msg)
                return
            is_safe_mode = response.data.get("safe_mode_enabled", False)
            if is_safe_mode != self._app_settings.safe_mode:
                self._app_settings.set_safe_mode(bool(is_safe_mode))

        except Exception as e:
            msg = f"Exception in sync_safe_mode: {e}"
            self._logger.error(msg)
            if raise_on_error:
                raise RuntimeError(msg) from e
            return

    def check_package_update(self, current_version: str) -> PackageUpdate:
        return self._update_checker.check(current_version)

    def check_backend_alive(self) -> bool:
        try:
            requests.get(self.backend_url, verify=False, timeout=3)
            return True
        except requests.RequestException:
            return False

    def check_frontend_alive(self) -> bool:
        try:
            requests.get(self.frontend_url, verify=False, timeout=3)
            return True
        except requests.RequestException:
            return False

    def check_service_gateway_alive(self) -> bool:
        return self._client_service_gateway.check_alive(timeout=3) if self._client_service_gateway else False

    def get_booking_info(self, booking_code: str) -> BookingInfo:
        response = self.service.get_booking_by_code(booking_code, timeout=3)
        if not response.success or not response.data:
            if response.status_code == 404:
                raise LookupError(f"Booking does not exist")
            else:
                raise ValueError(f"Failed to get booking info")

        data = response.data

        def parse_datetime(key: str):
            value = data.get(key)
            if not value:
                return None
            dt = datetime.fromisoformat(value).astimezone()
            return dt.replace(tzinfo=None, second=0)

        try:
            return BookingInfo(
                lab_id=data["lab_information"]["id"],
                booking_id=data["id"],
                booking_code=data["booking_code"],
                booking_creator=data["creator"]["username"].lower(),
                booking_project=data["lab_project"]['project_name'],
                booking_computer=data["computer"]["sku"],
                booking_status=BookingStatus(data["status"]),
                from_datetime=parse_datetime("from_date_time"),
                to_datetime=parse_datetime("to_date_time"),
                approval_status=ApprovalStatus(data["approval_status"])
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError("Failed to parse booking info")