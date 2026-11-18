# Utils Module

This folder contains general-purpose utility modules for the Lab Mango application.

---

## 📦 Structure & Purpose

- **config.py**           — Configuration file helpers and management
- **path.py**             — Path utilities for cross-platform file and directory handling
- **file.py, dir.py**     — File and directory operations (copy, move, scan, etc.)
- **datetime.py**         — Date and time utilities
- **hash.py**             — Hashing and checksum helpers
- **zip.py**              — ZIP archive creation and extraction
- **email.py**            — Email sending and formatting utilities
- **excel.py**            — Excel file reading and writing helpers
- **postgres_db.py, sqlite_db.py** — Database helpers for PostgreSQL and SQLite
- **http_client.py**      — HTTP(S) client for API requests, with logging and retry logic
- **systray.py**          — System tray integration helpers
- **windows.py**          — Windows-specific utilities
- **class_property.py, metaclass.py** — Advanced Python class helpers
- **list.py, dict.py**    — List and dictionary manipulation helpers
- **conversion.py**       — Data conversion utilities
- **otp.py**              — One-time password and token helpers
- **remote_desktop.py**   — Remote desktop session helpers
- ...and more

---

## 🛠️ Usage Example

```python
from utils.config import ConfigFileManager
from utils.path import PathUtil
from utils.http_client import ClientRequest
```

---

## 👥 For Maintainers

- All shared, reusable code that does not fit into a specific MVC, controller, or model module should be placed here.
- When adding new utilities, provide clear docstrings and usage examples if possible.
- Keep code modular and avoid unnecessary dependencies between utility modules.
- Update this README if you add or change major components.

---

## 📄 Contribution & Code Quality

- Contributions are welcome! Please ensure your code is well-documented and tested.
- Follow PEP8 and project coding standards.
- Add docstrings and comments for maintainability.
- For any changes to the utility framework, update this README and notify the team.