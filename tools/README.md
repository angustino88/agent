# Tools

This folder contains scripts and utilities that support building, integration, packaging, deployment, and GUI resource management for the Lab Mango project.

---

## 📦 Structure & Purpose

- **build/**
  - Batch scripts for building, rebuilding, cleaning, resource generation, UI conversion, and deployment (e.g., `05_build.bat`, `11_artifactory_deploy.bat`).
  - Python scripts for automation and build steps (`build/scripts/`).
- **vtracer/**
  - Third-party or custom tools for image/vector conversion (e.g., `vtracer.exe`).

---

## 🛠️ Main Build & Utility Scripts

- **01_env_check.bat** — Environment check; verifies required tools and settings.
- **02_qtdesigner.bat** — Launches Qt Designer for editing UI files.
- **03_ui2py.bat** — Converts Qt Designer `.ui` files to Python modules.
- **04_build_resources.bat** — Compiles Qt resource files (`.qrc`) to Python.
- **05_build.bat** — Main build entry point; compiles and packages the application.
- **06_rebuild.bat** — Cleans and rebuilds all outputs.
- **07_cleanall.bat** — Removes all build artifacts and temporary files.
- **08_bump_version.bat** — Interactively bump version and collect changelog.
- **09_build_history.bat** — Show build audit/history and stats.
- **10_changelog.bat** — Generate CHANGELOG.md from git history.
- **13_build_nuget.bat** — Builds the Chocolatey NuGet package (`.nupkg`) from the versioned application ZIP.
- **11_artifactory_deploy.bat** — Deploys build artifacts to Artifactory or other package repositories.
- **12_release.bat** — Full release pipeline: rebuild + deploy + tag.
- **scripts/** — Python scripts for resource conversion, signing, deployment, and other build steps.

---

## 🚀 Usage

- Use the batch scripts in `tools/build/` for all build, clean, and deployment operations.
- Each script is documented with comments and can be run directly from the command line or via VSCode tasks.
- For custom build steps or automation, extend the Python scripts in `tools/build/scripts/`.

---

## 📦 NuGet / Chocolatey Package

The NuGet package is a Chocolatey package containing the versioned application ZIP. The package metadata is rendered from the project configuration at build time:

- `prj/config/nuget/*.nuspec` — Nuspec template. Values use project-independent `{{TOKEN}}` placeholders.
- `prj/config/nuget/tools/` — Chocolatey install and uninstall templates.
- `prj/config/builder/build_config.py` — Application name and NuGet metadata such as package ID, authors, description, tags, and copyright.
- `prj/config/version/version_config.py` — Application version and release notes.
- `prj/config/builder/builder_env.bat` — Chocolatey/Artifactory tools and repository configuration.

### Prerequisites

1. Set up the virtual environment with `python setup_venv.py`.
2. Ensure Chocolatey is installed and `choco.exe` is available on `PATH`.
3. Build the software first so the versioned ZIP exists in `prj/build/app/`.

### Build the package

From the repository root, run:

```bat
prj\build\05_build.bat
```

The software build automatically runs the NuGet packaging step. To package an already-built ZIP separately, run:

```bat
prj\build\13_build_nuget.bat
```

The resulting file is written to `prj/build/app/` using the package ID and version, for example:

```text
labmango.2.7.0.nupkg
```

The package contains the versioned application archive, for example `LabMango-2.7.0.zip`. The package builder validates that all nuspec tokens are resolved and keeps the release notes from `version_config.py` in the packed nuspec.

### Deploy the package

Run the normal deployment command:

```bat
prj\build\11_artifactory_deploy.bat
```

The script discovers the ZIP, `meta.json`, `index.json`, and `.nupkg` files in `prj/build/app/`. It then:

1. Requests the Artifactory token when it is not already provided by the environment.
2. Shows the deployment target and discovered artifacts.
3. Asks independently whether to upload `index.json` and the NuGet package.
4. Asks for final confirmation before uploading.
5. Uploads selected artifacts and prints a deployment summary with status, size, and duration.

The NuGet repository is configured by `NUGET_REPO` in `prj/config/builder/builder_env.bat`. The current project configuration targets:

```text
https://artifactory.example
```

To deploy the NuGet package, answer `Y` to the NuGet upload prompt. Choosing `N` skips only the `.nupkg`; the ZIP and metadata deployment can continue normally.

### Build and deploy in one release

For the complete workflow, run:

```bat
prj\build\12_release.bat
```

This rebuilds the software, creates the NuGet package, runs the deployment confirmation flow, and creates the release tag when deployment succeeds.

### Master scripts and project mirror

`tools/build/` is the reusable tools submodule and contains the master Python and batch scripts. `prj/build/` contains the project-side copy and entry points. Keep reusable implementation changes in `tools/build/`; update the project mirror only when its batch wrapper is project-specific.

---

## 👥 For Maintainers

- Keep all build and integration tools in this folder for clarity and maintainability.
- When adding new tools or scripts, provide clear comments and usage instructions.
- Update this README if you add or change major components.

---

## 📄 Additional Notes

- All scripts should be cross-platform where possible (Windows batch and Python).
- Follow project coding standards and document any external dependencies.
- For any changes to the build or deployment process, update this README and notify the team.

---