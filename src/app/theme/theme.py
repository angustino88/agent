"""Theme loader and application service.

App-layer module — lives in src/app/theme/, owned by the view layer.
Called from MainView._setup() so styling is a view concern and the asset
path comes from the model (AppConfig.ASSET_DIR).

Public API:
    Theme.apply(app, "light", asset_dir)   # called by MainView
    Theme.list_available(asset_dir)        # list of available theme names
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from src.app.model.config.app_config import get_bundle_dir
from . import tokens


def _themes_dir(asset_dir: str | Path | None = None) -> Path:
    """Return the themes directory.

    Uses the explicitly supplied asset_dir when available (preferred — passed
    from MainView via AppConfig.ASSET_DIR).  Falls back to get_bundle_dir()
    for test / script contexts that don't go through the MVC stack.
    """
    base = Path(asset_dir) if asset_dir else get_bundle_dir() / "assets"
    return base / "themes"


def _substitute(template: str, mapping: dict[str, str]) -> str:
    """Replace @token placeholders; longest keys first to avoid prefix masking."""
    out = template
    for placeholder, value in mapping.items():
        out = out.replace(placeholder, value)
    return out


class Theme:
    """Stateless namespace for theme application."""

    DEFAULT = "light"

    @staticmethod
    def list_available(asset_dir: str | Path | None = None) -> list[str]:
        d = _themes_dir(asset_dir)
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.qss"))

    @classmethod
    def apply(cls, app: QApplication, name: str | None = None,
              asset_dir: str | Path | None = None) -> None:
        """Apply the named theme to the QApplication.

        Parameters
        ----------
        app:       The running QApplication.
        name:      Theme name (default "light").
        asset_dir: Path to the ``assets/`` directory from AppConfig.ASSET_DIR.
                   When omitted (e.g. test contexts) falls back to get_bundle_dir().

        Sequence:
        1. Force Fusion style (QSS ::indicator rules require it).
        2. Override QPalette roles so widgets that bypass QSS (native arrows,
           selection colors) still match the theme.
        3. Load QSS template, resolve @arrow-root path, substitute tokens,
           then call app.setStyleSheet().

        Idempotent: safe to call again to switch themes at runtime.
        """
        theme_name = name or cls.DEFAULT

        app.setStyle(QStyleFactory.create("Fusion"))
        cls._apply_palette(app)

        themes_dir = _themes_dir(asset_dir)
        qss_path = themes_dir / f"{theme_name}.qss"
        if not qss_path.is_file():
            raise FileNotFoundError(
                f"Theme '{theme_name}' not found at {qss_path}. "
                f"Available: {cls.list_available(asset_dir)}"
            )

        template = qss_path.read_text(encoding="utf-8")
        # @arrow-root resolves to assets/themes/arrows/ using forward slashes
        # (Qt QSS url() requires forward slashes on all platforms)
        arrow_root = str(themes_dir / "arrows").replace("\\", "/")
        template = template.replace("@arrow-root", arrow_root)
        qss = _substitute(template, tokens.QSS_SUBSTITUTIONS)
        app.setStyleSheet(qss)

    @staticmethod
    def _apply_palette(app: QApplication) -> None:
        """Override QPalette roles with brand accent + chrome colors.

        Fusion uses palette roles (not QSS) for:
        - Highlight / HighlightedText: selection bg in list/combo/lineedit
        - Button / ButtonText: Fusion draws QComboBox/QSpinBox/QScrollBar
          arrows using ButtonText — must be dark on a light background.
        - Window / Base / WindowText / Text: general surface + text colors.
        """
        pal = app.palette()
        accent_soft  = QColor(tokens.ACCENT_SOFT)
        bg_window    = QColor(tokens.BG_WINDOW)
        bg_elevated  = QColor(tokens.BG_ELEVATED)
        bg_chrome    = QColor(tokens.BG_CHROME)
        text         = QColor(tokens.TEXT)
        text_inverse = QColor(tokens.TEXT_INVERSE)
        border       = QColor(tokens.BORDER_STRONG)

        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            pal.setColor(group, QPalette.ColorRole.Highlight,       accent_soft)
            pal.setColor(group, QPalette.ColorRole.HighlightedText, text_inverse)
            pal.setColor(group, QPalette.ColorRole.Window,          bg_chrome)
            pal.setColor(group, QPalette.ColorRole.WindowText,      text)
            pal.setColor(group, QPalette.ColorRole.Base,            bg_window)
            pal.setColor(group, QPalette.ColorRole.AlternateBase,   bg_elevated)
            pal.setColor(group, QPalette.ColorRole.Text,            text)
            pal.setColor(group, QPalette.ColorRole.Button,          bg_chrome)
            pal.setColor(group, QPalette.ColorRole.ButtonText,      text)
            pal.setColor(group, QPalette.ColorRole.Mid,             border)
            pal.setColor(group, QPalette.ColorRole.Dark,            border)

        app.setPalette(pal)
