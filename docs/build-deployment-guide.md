# Build & Deployment Parameter Guide

This guide describes every parameter you may need to change when building,
packaging, and deploying an application. All configuration files
live under `prj/config/` and are plain Python or batch files — no build
system knowledge is required to edit them.

---

## Table of Contents

1. [Quick-start Checklist](#1-quick-start-checklist)
2. [Version Configuration](#2-version-configuration)
3. [Build Configuration](#3-build-configuration)
4. [Server / Download URL Configuration](#4-server--download-url-configuration)
5. [Builder Environment (Tool Paths & Artifactory)](#5-builder-environment-tool-paths--artifactory)
6. [Signing Keys](#6-signing-keys)
7. [Running the Build Scripts](#7-running-the-build-scripts)
8. [Running the Deployment Script](#8-running-the-deployment-script)
9. [Post-build Artefacts Reference](#9-post-build-artefacts-reference)

---

## 1. Quick-start Checklist

Before every release, work through this checklist in order:

| # | File | What to update |
|---|------|----------------|
| 1 | `prj/config/version/version_config.py` | Bump `APP_VERSION`, update `CHANGELOG` |
| 2 | `prj/config/builder/build_config.py` | Adjust build flags if needed |
| 3 | `prj/config/server/server_config.py` | Update `BASE_PACKAGE_URL` if the repo path changes |
| 4 | `prj/config/builder/builder_env.bat` | Update Artifactory repo paths if they change |
| 5 | `prj/config/keys/` | Replace key pair for a new signing identity |

---

## 2. Version Configuration

**File:** `prj/config/version/version_config.py`

```python
class VersionConfig:
    APP_VERSION = '1.0.0'      # ← change this for every release

    CHANGELOG = [              # ← human-readable release notes
        "Short description of what changed in this release",
    ]

    REQUIRES = {               # ← platform constraints embedded in meta.json
        "os":   ["windows"],
        "arch": ["x86_64", "AMD64"],
    }
```

### Versioning scheme

```
<major>.<minor>.<patch>
```

| Segment | When to increment |
|---------|-------------------|
| `major` | New UI / architecture, many new features |
| `minor` | A few new features or functionalities |
| `patch` | Bug-fix only release |

### What the version controls

- The PyInstaller output folder is named `<APP_NAME>-<APP_VERSION>/`.
- The zip archive is named `<APP_NAME>-<APP_VERSION>.zip` (when `VERSION_LABEL = 'TRUE'`).
- `meta.json` and `index.json` in `prj/build/app/` are automatically updated
  with the new version string after a successful build.

---

## 3. Build Configuration

**File:** `prj/config/builder/build_config.py`

Each setting is a class variable on `BuildConfig`. The table below lists all
parameters, their allowed values, and when you should change them.

### 3.1 Application identity

| Parameter | Default | Description |
|-----------|---------|-------------|
| `APP_SCRIPT` | `'/src/main.py'` | Entry-point script, relative to the project root |
| `APP_NAME` | `'MyApp'` | Internal name used for output folder / exe name |
| `APP_DISPLAY_NAME` | `'My App'` | Human-readable name (may contain spaces) |
| `ICON_PATH` | `'/assets/icons/app.ico'` | Path to the `.ico` file for the Windows executable |

### 3.2 Packaging flags

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `ZIP` | `'TRUE'` / `'FALSE'` | `'TRUE'` | Create a `.zip` of the output folder after build |
| `VERSION_LABEL` | `'TRUE'` / `'FALSE'` | `'TRUE'` | Append version string to the zip / folder name |
| `SIGN_PACKAGE` | `'TRUE'` / `'FALSE'` | `'TRUE'` | Sign the zip using the ed25519 private key |
| `META_FILE` | `'TRUE'` / `'FALSE'` | `'TRUE'` | Generate `meta.json` after build |
| `UPDATE_INDEX` | `'TRUE'` / `'FALSE'` | `'TRUE'` | Update and re-sign `index.json` after build |
| `META_URL` | URL string or `None` | `None` | Override the `download_url` written into `meta.json`; `None` derives it automatically from `ServerConfig.BASE_PACKAGE_URL` |
| `CHECKSUM_ALGO` | `'sha256'`, `'md5'`, etc. | `'sha256'` | Hash algorithm used for the package checksum |

### 3.3 PyInstaller flags

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `ONEFILE` | `'TRUE'` / `'FALSE'` | `'FALSE'` | Pack everything into a single executable |
| `CONTENTS_DIRECTORY` | directory name | `'_internal'` | Sub-folder name for bundled internals (one-folder mode only) |
| `WINDOW` | `'TRUE'` / `'FALSE'` | `'FALSE'` | Show a console window (`FALSE` = windowed / GUI mode) |

### 3.4 Build behaviour

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `CLEAN` | `'TRUE'` / `'FALSE'` | `'TRUE'` | Delete PyInstaller cache and temp files before building |
| `CONFIRM` | `'TRUE'` / `'FALSE'` | `'FALSE'` | Prompt before overwriting an existing `dist/` folder |

### 3.5 Extra assets and exclusions

```python
FOLDERS = [
    '/assets',          # ← add any extra folder (project-root-relative)
]

FILES = [
    # '/path/to/file',  # ← add individual files if needed
]

EXCLUDE = [
    # 'SomeHeavyModule',  # ← modules to exclude from the bundle
]
```

> **Tip:** Paths in `FOLDERS` and `FILES` start with `/` and are resolved
> relative to the project root (the folder containing `pyproject.toml`).

---

## 4. Server / Download URL Configuration

**File:** `prj/config/server/server_config.py`

```python
class ServerConfig:
    BASE_PACKAGE_URL = "https://<artifactory-host>/artifactory/<repo-path>/<app-name>/"
```

`BASE_PACKAGE_URL` is the public base URL from which end-users download the
application. The build system appends `<version>/meta.json` and
`<APP_NAME>-<version>.zip` to this URL when generating `meta.json` and
`index.json`.

Change this value when:
- The Artifactory server hostname changes.
- The repository or folder path within Artifactory changes.
- You are migrating to a different distribution server.

---

## 5. Builder Environment (Tool Paths & Artifactory)

**File:** `prj/config/builder/builder_env.bat`

This batch file is `call`-ed by every build script to set up the environment.

### 5.1 Python / Qt tool executables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_VENV` | `.venv` (project root) | Root of the Python virtual environment |
| `PYTHON` | `%PYTHON_VENV%\Scripts\python.exe` | Python interpreter |
| `PYUIC` | `%PYTHON_VENV%\Scripts\pyside6-uic.exe` | UI-to-Python compiler |
| `PYRCC` | `%PYTHON_VENV%\Scripts\pyside6-rcc.exe` | Qt resource compiler |
| `QTDESIGNER` | `%PYTHON_VENV%\Scripts\pyside6-designer.exe` | Qt Designer |
| `VTRACER` | `..\..\tools\vtracer\vtracer.exe` | Raster-to-SVG converter |

Change these only if:
- The virtual environment is located outside the project root.
- You are using a system-wide Python installation instead of the venv.

### 5.2 Project directories

| Variable | Default | Description |
|----------|---------|-------------|
| `QTDESIGNER_UI_DIR` | `src/app/view/widgets/ui` | Folder containing `.ui` files |
| `QTDESIGNER_PY_DIR` | `src/app/view/widgets` | Destination for generated `.py` files |
| `RESOURCE_QRC_FILE` | `src/qt_embedded/resources.qrc` | Qt resource manifest |
| `RESOURCE_PY_DIR` | `src/qt_embedded` | Destination for compiled resource module |
| `RESOURCE_IMPORT` | `"from qt_embedded import resources"` | Import statement injected into generated code |
| `IMAGE_DIR` | `src/qt_embedded/originals` | Raster source images for SVG conversion |
| `SVG_DIR` | `src/qt_embedded/icons` | Output directory for generated SVG icons |
| `BUILD_DIR` | `prj/build/app` | Directory where build artefacts are placed |

### 5.3 Artifactory deployment variables

| Variable | Description |
|----------|-------------|
| `ARTIFACTORY_URL` | Base URL of the Artifactory instance (include port if non-standard) |
| `PACKAGE_REPO` | Repository path for the application zip package |
| `META_REPO` | Repository path for `meta.json` |

> **Important:** Keep `PACKAGE_REPO` / `META_REPO` in sync with
> `ServerConfig.BASE_PACKAGE_URL` in `server_config.py` so that the URLs
> embedded in `meta.json` resolve correctly.

---

## 6. Signing Keys

**Directory:** `prj/config/keys/`

| File | Purpose |
|------|---------|
| `ed25519_priv.pem` | Unencrypted private key — used by the build scripts to sign the package and `index.json` |
| `ed25519_priv_encrypted.pem` | Password-protected copy of the private key (for safe storage) |
| `ed25519_pub.pem` | Public key — distributed to clients for signature verification |
| `key_gen.bat` | Generate a new key pair |
| `key_encrypt.bat` | Encrypt the private key with a password |
| `key_decrypt.bat` | Decrypt the encrypted key back to plaintext |

### Rotating the signing key

1. Run `key_gen.bat` to generate a new key pair.
2. Run `key_encrypt.bat` to create the encrypted backup.
3. Distribute the updated `ed25519_pub.pem` to any client that validates signatures.
4. Delete or archive the old keys securely — do **not** commit private keys to version control.

> **Security note:** `ed25519_priv.pem` must never be committed to a public
> repository. Add it to `.gitignore` if it is not already there.

---

## 7. Running the Build Scripts

All build scripts live in `prj/build/`. Run them from that directory or via
the VS Code task panel.

| Script | VS Code Task | Description |
|--------|-------------|-------------|
| `01_env_check.bat` | `$(shield) Environment Check` | Verify build tools, Python, and keys |
| `02_qtdesigner.bat` | `$(device-desktop) Qt Designer` | Launch Qt Designer |
| `03_ui2py.bat` | `$(file-code) UI to Python` | Convert `.ui` files to `.py` |
| `04_build_resources.bat` | `$(package) Build Resources` | Convert images → SVG → `.qrc` → `.py` |
| `05_build.bat` | `$(tools) Build Software` | Incremental build (reuses PyInstaller cache) |
| `06_rebuild.bat` | `$(sync) Rebuild Software` | Clean rebuild from scratch |
| `07_cleanall.bat` | `$(trash) Clean All` | Remove all build artefacts |

### Typical release build sequence

```cmd
cd prj\build
06_rebuild.bat          # clean rebuild + package + sign + meta
```

Or, if you only changed Python source (no new assets):

```cmd
05_build.bat            # incremental build
```

If UI files or resources changed, run first:

```cmd
03_ui2py.bat            # regenerate widget Python files
04_build_resources.bat  # regenerate Qt resource module
```

### First-time environment setup

```cmd
cd prj\config\builder
setup_builder_env.bat   # copies build tools into prj/build
```

---

## 8. Running the Deployment Script

**Script:** `prj/build/11_artifactory_deploy.bat`

**VS Code Task:** `$(cloud-upload) Artifactory Deploy`

The script uploads the `.zip` package and `meta.json` from `prj/build/app/`
to the Artifactory repositories defined in `builder_env.bat`. It requires
valid Artifactory credentials available in the environment (or prompts for
them).

### Pre-deployment checklist

- [ ] Build completed successfully (`prj/build/app/*.zip` exists).
- [ ] `meta.json` is present in `prj/build/app/`.
- [ ] `ARTIFACTORY_URL`, `PACKAGE_REPO`, and `META_REPO` in `builder_env.bat`
      are correct for the target environment.
- [ ] `BASE_PACKAGE_URL` in `server_config.py` matches the Artifactory path.
- [ ] Artifactory credentials are configured (API key or username/password).

### Run

```cmd
cd prj\build
11_artifactory_deploy.bat
```

---

## 9. Post-build Artefacts Reference

After a successful build the following files are created / updated in `prj/build/app/`:

| File | Description |
|------|-------------|
| `<APP_NAME>-<version>/` | Unpacked application directory (PyInstaller output) |
| `<APP_NAME>-<version>.zip` | Zipped distribution package |
| `meta.json` | Release metadata (version, download URL, checksum, changelog, requirements) |
| `index.json` | Version index listing all known releases; signed with ed25519 |

### `meta.json` structure

```json
{
  "name": "<APP_NAME>",
  "version": "<version>",
  "released_at": "<ISO 8601 timestamp>",
  "download_url": "<BASE_PACKAGE_URL><version>/<APP_NAME>-<version>.zip",
  "size_bytes": 123456789,
  "checksum": {
    "algorithm": "sha256",
    "value": "<hex digest>"
  },
  "requires": { "os": ["windows"], "arch": ["x86_64", "AMD64"] },
  "changelog": ["..."]
}
```

### `index.json` structure

```json
{
  "latest": "<latest-version>",
  "signature": "<ed25519 base64 signature>",
  "versions": [
    { "version": "1.0.0", "metadata_url": "1.0.0/meta.json" },
    { "version": "1.1.0", "metadata_url": "1.1.0/meta.json" }
  ]
}
```

> The `signature` field covers the JSON content (excluding the `signature`
> key itself) and is verified by clients using `ed25519_pub.pem`.
