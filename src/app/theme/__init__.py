"""VectorT32ape theme system.

App-layer module — lives in src/app/theme/, owned by the view layer.

Usage (in MainView._setup()):
    from src.app.theme import Theme
    from PySide6.QtWidgets import QApplication
    Theme.apply(QApplication.instance(), "light",
                self.model.config_model.app_config.ASSET_DIR)
"""
from .theme import Theme
from . import tokens

__all__ = ["Theme", "tokens"]
