# Utils — AGENTS.md

Shared general-purpose Python utilities. Used as a git submodule across multiple projects.
This file guides agents working **inside** this submodule.

> **If you are working in a consumer project**, just import what you need — no need to read this file.

---

## What this module is

Framework-agnostic Python utility library. No PySide6, no project-specific logic.

| Module | Purpose |
|---|---|
| `path.py` | `PathUtil` — Windows-first path join, normalize, resolve |
| `file.py` | File read/write/copy/delete helpers |
| `dir.py` | Directory scan, create, clean helpers |
| `config.py` | YAML/JSON config file load/save with defaults |
| `metaclass.py` | `metaclass_factory()` — resolve PySide6 metaclass conflicts |
| `single_instance.py` | Prevent multiple app instances via named mutex |
| `hash.py` | SHA256 / MD5 file and string hashing |
| `zip.py` | ZIP archive create/extract |
| `datetime.py` | Timestamp formatting, delta, UTC helpers |
| `http_client.py` | Requests wrapper with retry, logging, timeout |
| `conversion.py` | Unit conversion helpers |
| `list.py` / `dict.py` | Collection manipulation helpers |
| `sqlite_db.py` / `postgres_db.py` | Thin DB helpers |
| `windows.py` | Windows-specific: registry, process, DPI |
| `systray.py` | System tray icon helpers |
| `mdf.py` | asammdf MDF4 read/write helpers |

---

## Rules for modifying this module

- **No PySide6 imports** — must remain usable without Qt installed.
- **No project-specific logic** — keep utilities generic.
- **No inter-utility dependencies** — each file should be importable independently.
- Functions must be stateless where possible; prefer `@staticmethod` or module-level functions.
- All public functions must have docstrings with parameter and return type descriptions.
- Backward compatibility — consumer projects import directly by name; renames break them.
