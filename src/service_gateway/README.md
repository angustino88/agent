# service_gateway

Reusable service-gateway submodule.  Drop it into any Python project that needs
to communicate with a REST backend that follows the standard LabMango gateway
conventions (JWT auth, token refresh, package management).

---

## Concepts

| Layer | Class | Role |
|---|---|---|
| Transport | `GatewayClient` | Wraps `ClientRequest`; owns HTTPS-first protocol selection and automatic HTTP fallback |
| Base service | `BaseGatewayService` | Holds a `GatewayClient`; exposes `_get/_post/_put/_patch/_delete` helpers that prepend `base_path` |
| Standard service | `StandardGatewayService` | Extends `BaseGatewayService`; adds `login`, `refresh_token`, `get_latest_package`, `check_package_update` |
| App service | *your subclass* | Extends `StandardGatewayService`; sets `base_path` and adds app-specific endpoints |

---

## Quick start

```python
from src.service_gateway import GatewayClient, StandardGatewayService

# 1. Create the client (HTTPS tried first automatically)
client = GatewayClient(
    base_url="http://my-server.example.com:8080",
    auth_scheme="Bearer",
    token_refresh_callback=my_refresh_fn,
)

# 2. Create the service (extend StandardGatewayService for app endpoints)
class MyService(StandardGatewayService):
    base_path = "/api/my-app"

    def get_config(self, timeout=None):
        return self._get("config", timeout=timeout)

service = MyService(client, device_id="PC-001", source="AGENT_PC-001")

# 3. Use it
resp = service.login()
resp = service.get_config(timeout=5)

# 4. Health check (tries HTTPS then HTTP)
is_alive = client.check_alive()
```

---

## Files

| File | Description |
|---|---|
| `gateway.py` | `GatewayClient` — transport layer with protocol fallback |
| `service.py` | `BaseGatewayService` — abstract base for endpoint groups |
| `standard.py` | `StandardGatewayService` — standard endpoints |
| `models.py` | Typed return types (`LoginResult`, `PackageInfo`, …) |
| `exceptions.py` | `GatewayError` hierarchy |
| `__init__.py` | Public API re-exports |

---

## Extending

```python
from src.service_gateway import StandardGatewayService, GatewayClient
from src.utils.http_client import ClientResponse

class LabApiServiceGateway(StandardGatewayService):
    base_path = "/api/lab-mango"

    def __init__(self, client: GatewayClient, computer_sku: str, source: str):
        super().__init__(client, device_id=computer_sku, source=source)

    @property
    def computer_sku(self) -> str:
        return self._device_id

    # App-specific endpoint
    def get_otp_master_code(self, timeout=None) -> ClientResponse:
        return self._get("otp-master-code", timeout=timeout)
```
