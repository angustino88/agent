# Agent architecture and conventions

The Lab Mango agent runs on each lab computer (Windows). It gates logins with a booking code or a
user OTP, times the session, reports live activity, remote sessions and USB devices to the
department backend, and keeps itself updated through the service gateway.

Planned: [bench device and license monitoring](design/bench-device-and-license-monitoring.md).

## Systems it talks to

| System | How | Owner in the agent |
|---|---|---|
| Department backend (lab-mango) | Signed agent API `/agent/...` with the enrolled identity | `BackendModel` |
| Service gateway | JWT login; configuration, OTP delivery, package updates | `GatewayModel` |
| Router (Nginx) | The agent's server URL comes from the service gateway (`prod-server-config` `backend_url`) at enrollment; the web app shows none; requests are signed for `/agent/...` | — |
| Active Directory | User lookup at login (`pyad`) | `LoginCtrl` |
| Windows | Login/logout events, WMI (USB, hardware), RDP client info | controllers / `ComputerModel` |

## Source layout

```
src/
  main.py                 Qt app entry; also routes `enroll | status | unenroll` to agent_cli
  agent_cli.py            Command line (no Qt)
  core/                   Qt-free logic, unit tested on any OS
    agent_api/            Signed backend client, enrollment, identity/key store, session-log outbox
    monitoring/           PnP devices, hardware IDs, the watch list and the snapshot reporter
    licensing/            License checks: configuration, safe probes, extraction, presets, results
    gateway/              Lab Mango endpoints of the service gateway
    otp/                  One-time password generation and delivery
  app/                    The desktop application (MVC on src/mvc)
    model/                State and external systems: BackendModel, GatewayModel, ComputerModel, config, logging
      types/              Domain types (enums and frozen dataclasses)
    view/                 Dialogs; widgets/ holds *Gui.py generated from widgets/ui/*.ui
    controller/<feature>/ One package per feature: <feature>_ctrl.py plus its helpers
  mvc/ utils/ service_gateway/ pkgman/   Shared packages (workspace members, used by other tools)
tools/                    Shared build and release scripts
tests/                    pytest: agent_api, monitoring, app types, shared clients, integration
```

### Features (controllers)

| Package | Controller | Responsibility |
|---|---|---|
| `login` | `LoginCtrl` | Login screen, booking check-in, OTP, OS login/logout events |
| `remote_session` | `RemoteSessionCtrl`, `SessionTimer` | Session from login to logout, countdown, booking follow-up, session logs |
| `activity` | `ActivityCtrl`, `ActivityMonitor` | Live activity status from cursor idle time; reports and local status log |
| `booking_update` | `BookingUpdateCtrl` | Extend or end the running booking |
| `monitoring` | `MonitoringCtrl`, `PnpDeviceCollector`, `LicenseCollector`, `StorageQuotaMonitor` | Expected devices by PnP ID (watch list from the policy), discovery on request; license checks and expiry warnings; local storage quota report |
| `device_scan` | `DeviceScanCtrl` | Expected devices and their state, live plug/unplug log with PnP instance paths, Push = discovery snapshot |
| `health_check`, `server_config`, `settings`, `app_info`, `app_update`, `log_check`, `systray`, `user_manual` | | Support dialogs and updates |

### Event bus

| Event / request | Payload | Emitted by → used by |
|---|---|---|
| `session:start` | `(LoginInfo, Booking or None)` | `LoginCtrl` → `RemoteSessionCtrl` |
| `session:started` | `RemoteSession` | `RemoteSessionCtrl` → `ActivityCtrl` |
| `session:end` | — | `LoginCtrl` → `RemoteSessionCtrl` |
| `session:ended` | — | `RemoteSessionCtrl` → `ActivityCtrl` |
| `booking_update:show` | — | session dialog → `BookingUpdateCtrl` |
| `booking:changed` | — | `BookingUpdateCtrl` → `RemoteSessionCtrl` (re-read booking) |
| `get:remote_session` | → `RemoteSession` or `None` | `RemoteSessionCtrl` |
| `get:inactive_seconds` | → `float` | `ActivityCtrl` |
| `get:device_collector` | → `PnpDeviceCollector` | `MonitoringCtrl` |
| `devices:discover` | — | Device Scan dialog → `MonitoringCtrl` (one discovery snapshot) |
| `get:licenses` | → `list[LicenseObservation]` | `MonitoringCtrl` |
| `get:license_checks` | → `list[CheckState]` | `MonitoringCtrl` |

## Glossary (agent term → backend term)

| Agent | Backend | Notes |
|---|---|---|
| `ActivityStatus` (`offline, free, active, inactive, maintaining`) | `ComputingActivityStatus` | Live activity; separate from booking status |
| `BookingStatus` (`reserved, in_progress, completed, cancelled, expired`) | `BookingStatus` | |
| `Booking.booking_code`, `booked_for`, `starts_at`, `ends_at` | same names in `/agent/bookings/actions/*` | |
| `RemoteSession` | remote session (`AgentSessionLogReport`) | One login, login → logout |
| `remote_user_display_name`, `remote_computer`, `remote_ip` | same names in activity reports | Session logs call the client host `remote_host` |
| agent UID, agent identity | `AgentIdentity.agent_uid` | Not a credential; the Ed25519 key is |
| `ObservedDevice`, collector, snapshot | `DeviceObservation`, `collector_key`, `is_complete` | Collectors `pnp` (watch list) and `discovery` |
| PnP ID, hardware ID | `EquipmentHardwareId` (`pnp_id`, `vector_device`) | Registered on the unit by a coordinator; `Equipment.serial_number` is a label only |
| watch list | `expected_devices` in the monitoring policy (`ExpectedDevice`) | |
| computer name | Windows host name | The old term "SKU" is no longer used by the agent |
| web app (`frontend_url`) | Lab Mango frontend | |

## Conventions

- **Files and packages** are `snake_case`; one class per controller file named after the package
  (`remote_session/remote_session_ctrl.py` → `RemoteSessionCtrl`). Generated widget modules keep the
  build tools' `PascalCaseGui.py` names and are never edited by hand (except retranslated labels
  kept in sync with the `.ui` file).
- **Classes** `PascalCase` with role suffixes: `*Ctrl`, `*View`, `*Model`, `*Monitor` (polls state),
  `*Collector` (gathers and reports), `*Timer`.
- **Domain types** live in `app/model/types/`: enums subclass `str, Enum` with backend values;
  data classes are frozen. Times are naive local time inside the app and timezone-aware ISO 8601
  on the wire.
- **Backend calls** go through `BackendModel` only; controllers never build URLs. Writes that must
  not be lost (session logs, observations) are persisted before sending and retried idempotently.
- **Core vs app**: `src/core` has no Qt or Windows imports, so it is unit tested on CI; Windows and
  Qt specifics stay in `src/app`.
- **Shared packages** (`mvc`, `utils`, `service_gateway`, `pkgman`, `tools`) stay generic and
  backward compatible; app-specific code goes in `src/app` or `src/core`.
- **Logging** uses `[Area] message` prefixes (`[Backend]`, `[RemoteSession]`, `[USB]`, ...); grants,
  keys, OTPs and tokens are never logged.
- **Formatting**: ruff (`line-length = 120`) for `src/core`, `src/agent_cli.py` and `tests`.

## Persisted data

| Path (Windows) | Content | Compatibility |
|---|---|---|
| `%PROGRAMDATA%\LabMango\agent\identity.json` | Agent UID, server URL, backend key, key store tier | Written by `enroll` |
| Credential Manager `labmango_agent` / `keys\` | Ed25519 private key | Never leaves the computer |
| `%PROGRAMDATA%\LabMango\agent\session_log_outbox.json` | Session logs not yet acknowledged | |
| `%PROGRAMDATA%\LabMango\agent\observations_pnp.json`, `observations_discovery.json` | Last sequence and the pending observation batch per collector | |
| `%LOCALAPPDATA%\LabMango\settings\app_settings.yml` | Web app URL, TLS, AD, admins, safe mode | Older files stay valid |
| `%LOCALAPPDATA%\LabMango\logs\logs.db` | Local session and status log (SQLite) | Column names kept from earlier versions |
