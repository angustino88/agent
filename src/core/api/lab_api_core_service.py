from typing import Optional
from datetime import datetime
from ...utils.datetime import iso_datetime
from ...utils.http_client import ClientRequest, ClientResponse

class LabApiCoreService:
    def __init__(
        self,
        client: ClientRequest,
        computer_sku: str,
        source: str
    ):
        self.client = client
        self._computer_sku = computer_sku
        self._source = source
    
    @property
    def computer_sku(self) -> str:
        return self._computer_sku
    
    @property
    def source(self) -> str:
        return self._source

    def send_lab_status(
        self,
        status: str,
        inactive_time: int,
        remote_user: str,
        remote_user_displayname: str,
        remote_computer: str,
        remote_ip: str,
        booking_code: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        body = {
            "source": self.source,
            "status": status,
            "inactive_time": inactive_time,
            "remote_user": remote_user.lower(),
            "remote_user_displayname": remote_user_displayname,
            "remote_computer": remote_computer,
            "remote_ip": remote_ip,
        }
        if booking_code:
            body["booking_code"] = booking_code
        return self.client.put(
            f"/api/labs/lab-status/sku/{self.computer_sku}",
            body=body,
            expected_status=(200,),
            timeout=timeout
        )

    def send_session_log(
        self,
        login_time: str,
        logout_time: str,
        active_time: int,
        remote_user: str,
        remote_user_displayname: str,
        remote_computer: str,
        remote_ip: str,
        booking_code: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        body = {
            "source": self.source,
            "computer_sku": self.computer_sku,
            "login_time": login_time,
            "logout_time": logout_time,
            "active_time": active_time,
            "remote_user": remote_user,
            "remote_user_displayname": remote_user_displayname,
            "remote_computer": remote_computer,
            "remote_ip": remote_ip,
        }
        if booking_code:
            body["booking_code"] = booking_code
        return self.client.post(
            "/api/labs/lab-sessions/log",
            body=body,
            expected_status=(201,),
            timeout=timeout
        )

    def update_booking(
        self,
        booking_id: int,
        status: Optional[str] = None,
        lab_id: Optional[int] = None,
        project_id: Optional[int] = None,
        from_datetime: Optional[str] = None,
        to_datetime: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        body = {"id": booking_id}

        if status:
            body["status"] = status
        if lab_id:
            body["lab_id"] = lab_id
        if project_id:
            body["project_id"] = project_id
        if from_datetime:
            body["from_date_time"] = (
                iso_datetime(from_datetime, add_timezone=False) if isinstance(from_datetime, datetime) else from_datetime
            )
        if to_datetime:
            body["to_date_time"] = (
                iso_datetime(to_datetime, add_timezone=False) if isinstance(to_datetime, datetime) else to_datetime
            )

        return self.client.patch(
            f"/api/labs/lab-bookings/{booking_id}",
            body=body,
            expected_status=(200, 204),
            timeout=timeout
        )

    def get_booking_by_code(self, booking_code: str, timeout: Optional[int] = None) -> ClientResponse:
        return self.client.get(
            f"/api/labs/lab-bookings/code/{booking_code}",
            expected_status=(200,),
            timeout=timeout
        )

    def send_storage_quota(
        self,
        username: str,
        used: float,
        quota: float,
        user_displayname: str,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        body = {
            "source": self.source,
            "computer_sku": self.computer_sku,
            "username": username,
            "user_displayname": user_displayname,
            "used": used,
            "quota": quota,
        }
        return self.client.post(
            "/api/labs/analytics/storage-quota",
            body=body,
            expected_status=(201,),
            timeout=timeout
        )

    def send_lab_monitoring_event(
        self,
        event_type: str,
        category: str,
        object_name: str,
        object_id: str,
        technical_user: Optional[str] = None,
        remote_user: Optional[str] = None,
        details: Optional[list] = None,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        body = {
            "source": self.source,
            "computer_sku": self.computer_sku,
            "event_type": event_type,
            "category": category,
            "object_name": object_name,
            "object_id": object_id
        }
        if technical_user:
            body["technical_user"] = technical_user
        if remote_user:
            body["remote_user"] = remote_user
        if details:
            body["details"] = details
        return self.client.post(
            "/api/labs/lab-monitoring",
            body=body,
            expected_status=(201,),
            timeout=timeout
        )

    def update_computer_info(
        self,
        computer_info: dict,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        return self.client.patch(
            f"/api/labs/lab-computers/sku/{self._computer_sku}",
            body=computer_info,
            expected_status=(200,),
            timeout=timeout
        )

    def update_computer_monitoring(
        self,
        monitoring: dict | list,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        return self.update_computer_info({"monitoring": monitoring}, timeout=timeout)
        
    def send_lab_audit_event(
        self,
        device_sku: str,
        auditor: str,
        audit_status: str,
        audit_id: int,
        remarks: str,
        audited_at: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        body = {
            "auditor": auditor,
            "audit_status": audit_status,
            "audit_id": audit_id,
            "remarks": remarks,
        }
        if audited_at:
            body["audited_at"] = audited_at
        return self.client.post(
            f"/api/labs/lab-audit/sku/{device_sku}",
            body=body,
            expected_status=(201,),
            timeout=timeout
        )

    def send_otp_event(
        self,
        username: str,
        otp: str,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        body = {
            "username": username,
            "otp": otp,
        }
        return self.client.post(
            "/api/send-otp",
            body=body,
            expected_status=(200,),
            timeout=timeout
        )

    def get_computer_by_sku(
        self,
        computer_sku: str,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        resp = self.client.get(
            "/api/labs/lab-computers",
            expected_status=(200,),
            timeout=timeout
        )
        if resp.success and resp.data:
            resp.data = next(
                (item for item in resp.data if str(item.get("sku")) == str(computer_sku)),
                None
            )
        return resp
    
    def get_computer_monitoring(
        self,
        computer_sku: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        sku = computer_sku or self._computer_sku
        resp = self.get_computer_by_sku(sku, timeout=timeout)
        if not resp.success or not resp.data:
            resp.data = []
            return resp
        monitoring = resp.data.get("monitoring") if isinstance(resp.data, dict) else None
        resp.data = monitoring or []
        return resp

    def get_lab_equipments(
        self,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        return self.client.get(
            "/api/labs/lab-equipments/sku-list",
            expected_status=(200,),
            timeout=timeout
        )
        
    def get_user_groups(
        self,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        return self.client.get(
            "/api/user-groups",
            expected_status=(200,),
            timeout=timeout
        )

    def get_admin_usernames(
        self,
        timeout: Optional[int] = None
    ) -> ClientResponse:
        resp = self.get_user_groups(timeout=timeout)
        if not resp.success or not resp.data:
            return resp
        data = resp.data
        admins = []
        if isinstance(data, dict):
            admins.extend(data.get("admin", []) or [])
            admins.extend(data.get("lab-coordinator", []) or [])
        resp.data = sorted({u.lower() for u in admins if isinstance(u, str)})
        return resp