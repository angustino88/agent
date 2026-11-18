# service_gateway — AGENTS.md

Standalone service-gateway submodule.  Used as a git submodule across multiple
projects.  This file guides agents working **inside** this submodule.

> **If you are working in a consumer project** (not this repo), import from
> `src.service_gateway` and extend `StandardGatewayService` in your own service file.
> Do **not** edit this submodule for app-specific concerns.

---

## What this module is

A reusable, protocol-aware HTTP service gateway framework providing:

- `GatewayClient` — wraps `ClientRequest`; builds HTTPS/HTTP candidate URLs;
  retries once on transport failure using the alternate protocol; health-checks
  all candidates.
- `BaseGatewayService` — base class for endpoint groups; prepends `base_path`
  to all relative paths via `_get/_post/_put/_patch/_delete`.
- `StandardGatewayService` — adds the standard endpoints every app exposes:
  `login`, `refresh_token`, `get_latest_package`, `check_package_update`.
- Typed return models: `LoginResult`, `TokenRefreshResult`, `PackageInfo`,
  `PackageUpdateResult`.
- Exception hierarchy: `GatewayError` → `GatewayAuthError`,
  `GatewayConnectionError` → `GatewayProtocolExhaustedError`.

---

## Rules for modifying this module

- **No project-specific imports** — this module must remain generic.
- **No circular imports** — use `TYPE_CHECKING` guards for forward refs.
- **Backward compatibility** — this is a shared submodule; breaking the public
  API breaks all consumer projects.
- `GatewayClient` must **never** depend on PySide6 or any GUI toolkit.
- New standard endpoints must be genuinely cross-application; app-specific
  endpoints belong in the consumer project's subclass.
- All public methods must have docstrings.

---

## Extension pattern (consumer project)

```python
# src/core/api/my_gateway_service.py
from src.service_gateway import StandardGatewayService, GatewayClient
from src.utils.http_client import ClientResponse

class MyGatewayService(StandardGatewayService):
    base_path = "/api/my-app"

    def __init__(self, client: GatewayClient, device_id: str, source: str):
        super().__init__(client, device_id=device_id, source=source)

    def get_config(self, timeout=None) -> ClientResponse:
        return self._get("config", timeout=timeout)
```

```python
# Usage (e.g. in a model's init())
from src.service_gateway import GatewayClient

client = GatewayClient(
    base_url=app_config.MY_BACKEND_URL,
    auth_scheme="Bearer",
    token_refresh_callback=self.refresh_token,
)
service = MyGatewayService(client, device_id=computer_sku, source=source)
```
