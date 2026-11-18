# PkgMan (Package Manager)

This module provides package management utilities for the Lab Mango application, including installation, updating, scanning, and version management of application packages.

---

## 📦 Structure & Purpose

- **installer.py**   — Handles installation of packages and dependencies.
- **updater.py**     — Manages package updates and version checks.
- **scanner.py**     — Scans for available packages and their metadata.
- **package.py**     — Core package object and logic for handling package files.
- **version.py**     — Version comparison and semantic versioning helpers.
- **logprint.py**    — Logging and print utilities for package operations.

---

## 🛠️ Usage Example

```python
from pkgman.installer import install_package
from pkgman.updater import check_for_updates
from pkgman.scanner import scan_packages
```

---

## 👥 For Maintainers

- All package management logic should be placed in this folder for clarity and maintainability.
- When adding new features, provide clear docstrings and usage examples if possible.
- Keep code modular and avoid unnecessary dependencies between modules.
- Update this README if you add or change major components.

---

## 📄 Contribution & Code Quality

- Contributions are welcome! Please ensure your code is well-documented and tested.
- Follow PEP8 and project coding standards.
- Add docstrings and comments for maintainability.
- For any changes to the package management framework, update this README and notify the team.
