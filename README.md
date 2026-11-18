# Lab Mango Agent

The Lab Mango agent runs on each lab computer. It gates logins with a booking code or a user
one-time password, times the session, and reports live activity, remote sessions and USB devices
to the department's Lab Mango backend through the signed agent API.

- Architecture, layout, glossary and conventions: [docs/architecture.md](docs/architecture.md)
- Backend contract, feature mapping and what changed: [docs/agent-backend-integration.md](docs/agent-backend-integration.md)
- Build parameters: [docs/build-deployment-guide.md](docs/build-deployment-guide.md)

## Quick start (development, Windows, Python 3.12)

```powershell
python setup_venv.py                 # uv sync --all-packages --frozen into .venv
.venv\Scripts\python.exe src\main.py   # or run_app.bat
```

## Enroll a computer

An operator creates the agent in Lab Mango (computing equipment → Agent → Set up) and receives an
agent UID and a one-time grant. On the computer, as the account that runs the agent:

```powershell
LabMango.exe enroll --url https://<backend>/api/<dept> --agent-uid <uuid>   # prompts for the grant
LabMango.exe status
```

From source use `python src\main.py enroll ...`. Exit codes, TLS options and unenrolling are
described in [docs/agent-backend-integration.md](docs/agent-backend-integration.md).

## Tests

```powershell
uv run pytest -q
uv run ruff check src/core src/agent_cli.py tests
```

CI (`.github/workflows/ci.yml`) runs both on Windows.

---

## 🏗️ Build & Maintenance Guide

This document provides detailed, professional instructions for building, maintaining, and extending the Lab Mango software. It is intended for maintainers and contributors.

---

### 📂 Project Structure

- **prj/build/**: Main build scripts and build output (batches: `05_build.bat`, `06_rebuild.bat`, etc.)
- **prj/config/builder/**: Build configuration, environment setup scripts, and build extensions.
- **prj/config/keys/**: Ed25519 keys for signing (private key is NOT committed; public key is safe to commit).
- **tools/build/scripts/**: Python build and utility scripts for resource conversion, packaging, signing, and deployment.
- **src/**: Application source code, including controllers, models, views, and core logic.

---

### 🚀 How to Build

1. **Setup Build Environment**
   - Run the setup script to prepare the build environment:
     ```powershell
     cd prj\config\builder
     setup_builder_env.bat
     ```

2. **Build the Software**
   - From the build directory, run:
     ```powershell
    cd ..\..\build
    05_build.bat
     ```
   - Or use the VSCode task:  
     **Terminal → Run Task... → $(tools) Build Software**

3. **Rebuild or Clean (Optional)**
   - To rebuild:
     ```powershell
    06_rebuild.bat
     ```
   - To clean all build outputs:
     ```powershell
    07_cleanall.bat
     ```

4. **Resource and UI Tools**
  - Convert UI files: `03_ui2py.bat`
  - Build resources: `04_build_resources.bat`
  - Launch Qt Designer: `02_qtdesigner.bat`

5. **Deploy to Artifactory**
   - After a successful build, deploy artifacts:
     ```powershell
    11_artifactory_deploy.bat
     ```
   - Or use the VSCode task:  
     **Terminal → Run Task... → $(cloud-upload) Artifactory Deploy**

---

### 🔑 Key Management

- **Never commit private keys** (`ed25519_priv.pem`) to version control.
- The public key (`ed25519_pub.pem`) is safe to commit and is used for signature verification.
- If a key is compromised or a maintainer leaves, generate and distribute a new key securely.
- Document the location and usage of keys in your team’s onboarding or security documentation.

---

### ⚙️ Configuration

- Build configuration: `prj/config/builder/build_config.py`; version: `prj/config/version/version_config.py`.
- Update version numbers, quotas, and other settings as needed.
- Background task intervals: `src/app/model/config/task_schedule_config.py`.
- Environment variables and build environment setup are managed in `builder_env.bat` and related scripts.

---

### 🧹 Maintenance

- **Logs and Artifacts:**  
  - Build logs and artifacts (zip packages, `meta.json`) are written under `prj/build/`.
- **Regularly review and rotate keys** as part of your security policy.

---

### 👥 Onboarding New Maintainers

- Share this README and the key management policy with new maintainers.
- Provide access to necessary scripts, configuration files, and secure key distribution.
- Ensure new maintainers understand the build, deployment, and maintenance process.
- Encourage adherence to coding standards and documentation practices.

---

### 📄 Additional Notes

- Follow PEP8 and project coding standards for all Python code.
- Add docstrings and comments for maintainability.
- Write and update unit tests as needed.
- For any changes to the build or deployment process, update this README and related documentation.
- Use the provided VSCode tasks for a streamlined development workflow.

---