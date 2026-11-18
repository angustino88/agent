"""App tests need PySide6 (QtCore only). pyautogui is replaced so no display is required."""

import sys
import types

import pytest

pytest.importorskip("PySide6.QtCore")

if "pyautogui" not in sys.modules:
    fake = types.ModuleType("pyautogui")
    fake.position = lambda: (0, 0)
    sys.modules["pyautogui"] = fake
