# Agent ↔ Backend Integration (signed agent API)

Status: implemented for every agent route the backend serves today.
Contract source: lab-mango `openapi/agents.yml`, `core/agents/` and `docs/agent-platform/`.

The backend no longer serves the legacy agent routes (`/api/labs/lab-status/sku/...`,
`/api/labs/lab-sessions/log`, `/api/labs/lab-bookings/code/...`, `/api/labs/lab-computers/...`,
`/api/labs/lab-monitoring`, `/api/labs/analytics/storage-quota`, `/api/labs/lab-audit/...`) and no
longer accepts a shared API key for agents. Each computer now enrolls once and signs every request
with its own Ed25519 key.

## Enrollment (once per computer)

An operator creates the agent in Lab Mango (computing inventory → Agent → Set up) and gets an
agent UID and a one-time grant (`eg_…`, at most 60 minutes). On the computer, as the account
that runs the agent:

```
LabMango enroll --url https://<backend>[/api/<dept>] --agent-uid <uuid> [--grant eg_...] [--unattended]
LabMango status [--json]
LabMango unenroll [--yes]
```

From source: `python src/main.py enroll ...` or `python src/agent_cli.py enroll ...`.
The grant can also come from `LABMANGO_AGENT_GRANT` or a hidden prompt; it is never written to
disk or logs. Exit codes follow lab-mango `docs/agent-platform/agent-cli.md`
(0 ok, 2 grant, 3 proof, 4 conflict/already enrolled, 5 unreachable).
`--ca-bundle` sets a custom CA; `--insecure` allows `http://` and skips TLS checks (testing only).

State lives in `%PROGRAMDATA%\LabMango\agent\` (override with `LABMANGO_AGENT_HOME`):
`identity.json` (agent UID, backend URL and key, no secrets) and the private key in the Windows
Credential Manager via `keyring` (`os_keystore`); a `keys\` file is the `software` fallback.
The key is per Windows user when it is in Credential Manager, so enroll as the user that runs
the agent.

## TLS

Off by default because the gateway does not have a certificate yet. One switch in the per-user
`app_settings.yml` turns it on for the gateway, the legacy client and the agent API together:

```yaml
tls:
  verify: true          # check certificates
  ca_bundle: ""         # optional path to an internal CA bundle
```

With `verify: true` the gateway client also stops falling back to plain HTTP. The command line
does not read this file: `enroll` refuses `http://` URLs and checks certificates unless
`--insecure` is given, and `--ca-bundle` points it at an internal CA.

## Request signing

`X-Agent-Id`, `X-Agent-Timestamp` (unix seconds, ±300 s), `X-Agent-Nonce` (16 random bytes,
single use) and `X-Agent-Signature`: Ed25519 over the NUL-joined
`labmango-agent-request-v1, backend_key, agent_uid, METHOD, path, timestamp, nonce, sha256_hex(body)`.
The signed path is the backend path (`/agent/...`) without the Router prefix, which Nginx strips.
Redirects are never followed. Implementation: `src/core/agent_api/signing.py`, `client.py`.

## Feature mapping

| Agent feature | Before | Now (owner) |
|---|---|---|
| Liveness | — | `POST /agent/heartbeat` every 60 s (`BackendModel.send_heartbeat`) |
| Live activity | `PUT /api/labs/lab-status/sku/{sku}` | `PATCH /agent/equipment/activity` on change and every 5 min (`ActivityCtrl`) |
| Remote session log | `POST /api/labs/lab-sessions/log` | `POST /agent/session-logs` through a bounded on-disk outbox, retried with the same `event_key` (`RemoteSessionCtrl`) |
| Booking login | `GET /api/labs/lab-bookings/code/{code}` + local checks | `validate` (read-only) → AD lookup → `check-in`, booking becomes `in_progress` (`LoginCtrl`) |
| Booking follow-up | same GET every 5 min | `validate`; not eligible means the booking ended (`SessionTimer`) |
| Extend booking | `PATCH /api/labs/lab-bookings/{id}` | `POST /agent/bookings/actions/extend` with readable refusal reasons (`BookingUpdateCtrl`) |
| End booking | `PATCH ... status=done` | `POST /agent/bookings/actions/complete` |
| USB devices | filter list from `/api/labs/lab-computers`, events to `/api/labs/lab-monitoring` | every USB device with its serial, as complete snapshots to `POST /agent/device-observations/actions/report`; the backend matches serials to equipment (`UsbDeviceCollector`, `DeviceObservationReporter`) |
| Monitoring policy | — | `GET /agent/monitoring-policy` every 10 min with ETag (`MonitoringCtrl`) |
| Backend available | `GET <backend root>` | `GET /agent/info` |

The backend decides booking eligibility (approval, this computer's bench, time window) and answers
every refusal identically, so the login screen cannot say *why* a code was refused. Bookings are
identified by code only.

### Device observations

Each report is a complete snapshot of the connected top-level USB devices (`collector_key = "usb"`).
The backend disconnects devices a complete snapshot omits, and complete snapshots may skip sequence
numbers. Therefore:

- a snapshot is sent when the device set changes (after 3 matching scans, 5 s apart), and otherwise
  every half `freshness_seconds` (60 s with today's policy) to keep connections fresh;
- the sequence is the wall clock in milliseconds, never below the last one sent, so it keeps
  increasing after a reinstall;
- each batch (`Idempotency-Key` + body) is stored in `agent\observations_usb.json` before sending and
  resent byte-identical until acknowledged; `409` or `422` drops it and the next cycle sends a new
  snapshot;
- `observation_key` is `usb:` + the Windows instance id; Windows-generated instance ids (containing
  `&`) are not serial numbers and are reported with an empty serial.

## Removed, because the backend has no agent route

| Feature | What happens now |
|---|---|
| Computer information (OS, IP, disks, system info) | Not reported. Backend `PATCH /agent/equipment/state` is proposed only; re-add when it ships |
| Storage quota upload | Still measured; written to `<sharing root>\.system\quota\quota_report.json` only |
| USB filter list, audit events | Replaced by device observations |
| Admin list from `/api/user-groups` | `login.admin_usernames` in `app_settings.yml` |
| OTP via the backend's `/api/send-otp` | OTP is sent through the service gateway only |
| Shared API key | Removed; the backend URL comes from the enrolled identity |

## Behaviour changes

- An administrator login without a booking reports activity `maintaining` (it used to come from a
  booking project named "maintenance", which the agent API no longer returns).
- Booking codes: only the `BOOKING-` prefix is normalised; the rest is matched exactly by the backend.
- The packaged `LabMango.exe` attaches to the terminal it was started from for `enroll`, `status`
  and `unenroll`, so output and prompts are visible.

## Not done yet

- **Service install** (`labmango-agent service install`): the agent remains a per-user tray
  application; the backend's device design expects a privileged service for enforcement.

## Dependencies

`pyproject.toml` (root plus the workspace members `tools`, `src/pkgman`, `src/utils`, `src/mvc`,
`src/service_gateway`) and `uv.lock` are the single source; `setup_venv.py` runs
`uv sync --all-packages --frozen`. The old `requirements.txt` had drifted and was removed.

## Tests

```
uv run pytest -q                # unit tests (no network); CI runs them on Windows
LABMANGO_E2E_URL=... LABMANGO_E2E_AGENT_UID=... LABMANGO_E2E_GRANT=eg_... \
LABMANGO_E2E_BOOKING_CODE=... pytest tests/integration -q   # against a running backend
```

The end-to-end test enrolls, heartbeats, reports activity, validates / checks in / extends /
completes a booking, sends an idempotent session log, reads the monitoring policy with ETag and
replays an observation batch, then checks that a wrong key gets `401`.
