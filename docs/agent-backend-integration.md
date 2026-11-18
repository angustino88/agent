# Agent ↔ Backend Integration (signed agent API)

Status: phase 1 implemented on branch `claude/beautiful-heisenberg-ut8780`.
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

## Request signing

`X-Agent-Id`, `X-Agent-Timestamp` (unix seconds, ±300 s), `X-Agent-Nonce` (16 random bytes,
single use) and `X-Agent-Signature`: Ed25519 over the NUL-joined
`labmango-agent-request-v1, backend_key, agent_uid, METHOD, path, timestamp, nonce, sha256_hex(body)`.
The signed path is the backend path (`/agent/...`) without the Router prefix, which Nginx strips.
Redirects are never followed. Implementation: `src/core/agent_api/signing.py`, `client.py`.

## Feature mapping

| Agent feature | Before | Now |
|---|---|---|
| Liveness | — | `POST /agent/heartbeat` every 60 s (`LabApiModel.send_agent_heartbeat`) |
| Lab status | `PUT /api/labs/lab-status/sku/{sku}` | `PATCH /agent/equipment/activity` (`LabStatusCtrl`) |
| Session log | `POST /api/labs/lab-sessions/log` | `POST /agent/session-logs` via a bounded on-disk outbox, retried with the same `event_key` |
| Booking login | `GET /api/labs/lab-bookings/code/{code}` + local checks | `validate` (read-only) → AD lookup → `check-in` (booking becomes in progress) |
| Booking recheck | same GET every 5 min | `validate`; not eligible = booking ended |
| Extend booking | `PATCH /api/labs/lab-bookings/{id}` | `POST /agent/bookings/actions/extend` with readable refusal reasons |
| End booking | `PATCH ... status=done` | `POST /agent/bookings/actions/complete` |
| Backend alive | `GET <backend root>` | `GET /agent/info` |
| Device monitoring | `/api/labs/lab-computers` + `/api/labs/lab-monitoring` | client ready (`get_monitoring_policy`, `report_device_observations`); collector not migrated yet |

The backend now decides booking eligibility (approval, this computer's bench, time window) and
answers every refusal identically, so the login dialog can no longer say *why* a code was refused.
Bookings are identified by code only; `SessionInfo.booking_id` was removed.

## Not migrated yet (no agent route on the backend, or follow-up work)

- **Device observations collector**: `PhysicalDeviceMonitor` still reads filters from the removed
  `/api/labs/lab-computers`. Next step: drive it from `GET /agent/monitoring-policy` and report
  `collector_key` / `generation_key` / `sequence` batches with a durable `Idempotency-Key`.
- **Computer info snapshot** (`ComputerInfoMonitor`): backend `PATCH /agent/equipment/state` is
  proposed only.
- **Storage quota, audit events, device scan**: no agent route exists.
- **Admin list and OTP for temporary logins** (`/api/user-groups`, `/api/send-otp`): user-authenticated
  backend routes; the service-gateway path still works for OTP.
- **Booking "maintenance" mode**: the agent API no longer returns the project, so maintenance
  bookings are not detected.
- **Packaged CLI output**: the PyInstaller build has no console (`WINDOW = 'FALSE'`), so
  `LabMango.exe enroll` works and returns exit codes but prints nothing. A separate console entry
  point (e.g. `labmango-agent.exe`) is needed for operators.
- **Service install** (`labmango-agent service install`): not implemented; the agent remains the
  per-user tray application.

## Tests

```
pytest -q                       # unit tests (no network)
LABMANGO_E2E_URL=... LABMANGO_E2E_AGENT_UID=... LABMANGO_E2E_GRANT=eg_... \
LABMANGO_E2E_BOOKING_CODE=... pytest tests/integration -q   # against a running backend
```

The end-to-end test enrolls, heartbeats, reports activity, validates / checks in / extends /
completes a booking, sends an idempotent session log, reads the monitoring policy with ETag and
replays an observation batch, then checks that a wrong key gets `401`.
