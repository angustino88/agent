# Tools — AGENTS.md

Shared build, packaging, and deployment scripts. Used as a git submodule across multiple projects.
This file guides agents working **inside** this submodule.

---

## What this module is

Build toolchain for PySide6 desktop applications:

| Path | Purpose |
|---|---|
| `build/01_env_check.bat` | Environment check (verify tools & keys) |
| `build/02_qtdesigner.bat` | Launch Qt Designer |
| `build/03_ui2py.bat` | Convert `.ui` → `*Gui.py` via `uic` |
| `build/04_build_resources.bat` | Compile `.qrc` → `resources.py` via `rcc` |
| `build/05_build.bat` | Main PyInstaller build |
| `build/06_rebuild.bat` | Clean + rebuild |
| `build/07_cleanall.bat` | Remove all build artifacts |
| `build/08_bump_version.bat` | Bump version and collect changelog |
| `build/09_build_history.bat` | Show build history and stats |
| `build/10_changelog.bat` | Generate CHANGELOG.md |
| `build/11_artifactory_deploy.bat` | Deploy artifacts |
| `build/scripts/` | Python helpers: signing, resource gen, version injection |
| `vtracer/` | SVG/vector conversion tool |

---

## Rules for modifying this module

- Build scripts must remain project-agnostic — project names, paths, and versions are injected via `build_config.py` in the consumer project's `prj/config/builder/`.
- Do not hardcode project-specific strings in any script here.
- Test changes against at least two consumer projects before committing.
`03_ui2py.bat` and `04_build_resources.bat` are the most frequently used — keep them fast and side-effect-free.
- Scripts must run from the consumer project's `prj/build/` directory (they use relative paths upward to project root).
