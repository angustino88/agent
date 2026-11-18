# Bench device and license monitoring (agent design)

**Status:** Licenses from the Vector License Client: implemented locally (read, tray warnings, device dialog). Device links, watch list and reporting to the backend: proposed (2026-11-18). Backend contract: lab-mango
`docs/proposals/agent-bench-devices-and-licenses.md` (T2, needs owner approval).
**Builds on:** the USB collector and `DeviceObservationReporter` (`src/core/monitoring/`).

## 1. Goals

1. Monitor only what matters: equipment that belongs on this computer's bench, plus *additional*
   lab equipment plugged in. Mice, keyboards, phones and personal sticks never leave the computer.
2. Identify equipment by what the hardware reports, not by the inventory's `serial_number`, which
   is typed by people (part numbers, USB product IDs, labels) and does not match the device.
3. Read tool licenses held by lab hardware or by the computer (first: Vector), so the backend
   keeps `License.expiry_date` / `max_version` current and warns before expiry.
4. Show both in the tray app: warnings and the device dialog.

## 2. Identity: hardware IDs and device links

The agent reports **hardware IDs**: values read from the device. A coordinator **links** each
physical unit's hardware ID to its inventory record once, in the web app. Matching, the bench
watch list and license carriers all use links; `serial_number` remains a human label.

| Kind | Read from | Value | Notes |
|---|---|---|---|
| `usb_serial` | Windows USB instance ID when the device has a serial descriptor | `VID:PID:serial` | Unique per device, any computer, any port |
| `vector_device` | Vector XL Driver Library | `<article>-<serial>`, e.g. `007113-585343` | Same serial as Vector Hardware Config |
| `usb_port` | Windows instance ID when the device has no serial (Windows adds `&…`) | full instance ID | Changes with the USB port; valid only on this computer |
| model | USB vendor and product ID | `VID:PID` | Not an identity: tells *what* it is, not *which one* |

Rules in `src/core/monitoring/devices.py`: an instance ID whose last segment contains `&` is a
Windows-generated port ID, never a serial; values are upper-case; at most 4 IDs per device.

### Linking flow

1. A CANcase is plugged into the bench computer for the first time. Its model `1248:1073` is a lab
   model, so the agent reports it with its hardware IDs (an *additional*, unlinked device).
2. The backend suggests the bench's unlinked VN1630A units; the coordinator confirms "CANcase 3".
3. The next policy lists CANcase 3 in `watched_devices` with its hardware IDs. From then on it is
   matched wherever it is plugged in, and its licenses attach to it.

## 3. What the agent reports

| Device | Reported | Backend sees |
|---|---|---|
| Hardware ID in `watched_devices` | yes | the bench unit, connected |
| Watched unit not connected | absent from the complete snapshot | the bench unit, disconnected (missing) |
| Lab model (`device_models`), not watched | yes | additional device: linked unit from elsewhere, or unlinked with link suggestions |
| Anything else | no | — |

```mermaid
flowchart LR
    P[Monitoring policy<br/>watched_devices, device_models, license_collectors] --> F[Watch filter]
    U[USB collector WMI] --> F
    V[Vector collector XL driver] --> F
    F -->|complete snapshot| R1[SnapshotReporter usb / vector]
    L[License collector<br/>Vector providers] -->|complete snapshot| R2[SnapshotReporter licenses]
    R1 --> B[(Backend: links, matching)]
    R2 --> B
    F --> UI[Device dialog + tray warnings]
    L --> UI
```

Compatibility: with a backend that sends no watch list yet, the agent keeps today's behaviour.

## 4. Collectors

| Collector | Source | Reports | Needs |
|---|---|---|---|
| `usb` | WMI `Win32_PnPEntity` (exists) | watched / lab-model USB devices with hardware IDs and VID:PID | — |
| `vector` | Vector XL Driver Library (`vxlapi64.dll`, via `ctypes`) | Vector interfaces: hardware type, serial, channels | Vector driver installed |
| licenses `vector` | XL driver (legacy licenses) + Vector License Client (new model) | licenses per carrier | see 4.2 |

### 4.1 Vector devices

`xlOpenDriver` → `xlGetDriverConfig` (channels with hardware type, index and serial) →
`xlCloseDriver`; channels grouped by serial into one device with `vector_device` and, when the
USB entry is found, `usb_serial`. Read-only: no ports opened, no configuration changed.

### 4.2 Vector licenses

| Provider | License model | Read through | Status |
|---|---|---|---|
| Vector License Client | New Vector License Model | `Vector.LicenseClient -listlicenses` (Vector KB0021758) | **Implemented** (`src/core/vendors/vector/license_client.py`) |
| Vector hardware licenses | Legacy, hardware-based (shown in Vector Hardware Config) | XL Driver Library `xlGetLicenseInfo` | Planned; signature to be checked against the installed `vxlapi.h` |

What `-listlicenses` gives (fixture: `tests/vendors/vector/fixtures/listlicenses_device_perpetual.xml`):

| Element | Used as |
|---|---|
| `DeviceName` (`007113-585343`) | carrier hardware ID `vector_device` for `BindingType` `DEVICE`/`DONGLE` |
| `BindingType` | carrier type: `DEVICE` → device, `DONGLE` → dongle, `PC` → this computer |
| `ProductText`, `MaterialNumber` | product name and Vector product (material) number |
| `MaxVersion` | highest licensed version |
| `ExpirationDateString` | **`expires_at`**: when the license stops working unless reactivated (here a perpetual license that must be reactivated every `ReactivationPeriod` = 12 months) |
| `FinalExpirationDateString` | `final_expires_at`; `9999-12-31` means perpetual |
| `IsReactivatable`, `IsPerpetual`, `LicenseType` | shown to the user, sent to the backend |
| `VectorLicenseId` | matches `License.identifier` in Lab Mango; never logged or shown |
| `ContractId`, `LicenseId`, user and name-list fields | not kept |

Warnings and the backend's `License.expiry_date` follow `expires_at`: that is the day the user loses
the tool. The output declares `encoding="Codepage - 437"`, not a valid XML encoding; the reader
decodes the bytes itself. The CLI runs read-only (`-listlicenses` only), without a window, with a
20 s timeout and a 4 MiB output limit.

Open: the device name format looks like `<article number>-<serial>`; the Vector device collector
(4.1) should produce the same string so device and license links are one link. To verify on a lab
computer against Vector Hardware Config.

### 4.3 License observation

`src/core/monitoring/licenses.py`: `LicenseObservation(observation_key, vendor, product_code,
product_name, carrier_type, carrier_hardware_id, expires_at, final_expires_at, max_version,
is_reactivatable, vendor_license_id)`, with `state(now)`, `days_left(now)` and `describe()` (safe
for logs: no license ID). Observation key: `vector:<carrier type>:<device name or "computer">:<material number>`.

## 5. Code layout

```
src/core/monitoring/
  devices.py               HardwareId, ObservedDevice(hardware_ids, vendor_id, product_id)
  watch_list.py            WatchList.from_policy(), accepts(device), is_watched(device)
  snapshot_reporter.py     SnapshotReporter (generalised from reporter.py: devices and licenses)
  licenses.py              LicenseObservation, LicenseProvider protocol
src/core/vendors/vector/
  xl_driver.py             ctypes binding (Windows only, loaded lazily)
  devices.py               XL channel list -> ObservedDevice
  license_client.py        runs the License Client CLI, parses its output
  licenses.py              both providers -> LicenseObservation
src/app/controller/monitoring/
  vector_device_collector.py
  license_collector.py
tests/vendors/vector/fixtures/   captured outputs (4.2)
```

## 6. User interface (tray app)

- **Device dialog**: each device shows its link: "CANcase 3 (this bench)", "CANcase 7 (bench B7,
  additional)" or "Not linked — link it in Lab Mango" with a button that opens the unit's page.
  Hardware IDs are shown so an admin can tell the coordinator which device it is.
- **Licenses in the device dialog** (implemented as a list in the dialog's log; a table needs a
  `.ui` change): license, carrier, expiry, version, days left.
- **Tray warning** (implemented) when a license on this computer or a connected device expires
  within `licenses.warn_days` (30) days, at most once a day per license, for example
  "CANalyzer PRO on 007113-585343 expires in 10 days (09 Apr 2027). Reactivate it in the Vector
  License Client."

Linking itself stays in the web app: the agent is authenticated as a device, not as a coordinator.

## 7. Failure behaviour

| Situation | Behaviour |
|---|---|
| Vector driver or License Client not installed | That source reports nothing, logged once; others continue |
| CLI timeout (> 10 s) or unparsable output | No snapshot sent (never a partial "complete" one); retried next cycle |
| Backend without the new fields or route | Previous behaviour for devices; license collector off |
| Device moved to another USB port | `usb_serial` / `vector_device` still match; a `usb_port`-only device needs a new link (shown in the dialog) |

## 8. Delivery

| Phase | Agent | Backend | Done when |
|---|---|---|---|
| 1 | Hardware IDs; watch filter; Vector device collector; link status in the dialog | Links, suggestions, link matching, `usb_ids`, watch list | Bench units show connected/missing by link; additional devices get suggestions |
| 2 | License providers (after 4.2 captures), license reporter | License route, projection, matching | A CANcase's licenses show on its license records |
| 3 | Tray warnings, license table | Expiry/version updates (D1), notifications | Lab Mango expiry dates follow the hardware |
