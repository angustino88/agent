"""Design tokens for the VectorT32ape light theme.

These are the single source of truth for all visual constants. They are:
- consumed by `theme.py` to substitute @placeholders in QSS templates
- importable from Python code that needs token values directly
  (e.g., palette setup, status pill state colors, dynamic computed styles)

Naming convention: SCREAMING_SNAKE_CASE constants grouped by purpose.
Adding a token? Also add the matching @placeholder usage in light.qss.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------
# Brand accent — olive-green family
ACCENT          = "#556B55"   # primary brand: Save buttons, focus rings
ACCENT_HOVER    = "#627a62"   # button hover
ACCENT_PRESSED  = "#3d503d"   # button pressed / deep active
ACCENT_TINT     = "#eef2ee"   # very light olive tint: row hover, soft surfaces
ACCENT_SOFT     = "#7a9e7a"   # medium olive: list/combo selection bg

# Application chrome — light gray (toolbar / menubar / statusbar)
BG_CHROME       = "#f0f0f0"   # light gray chrome background
BG_CHROME_HOVER = "#e0e8e0"   # hover inside chrome (subtle olive tint)
DIVIDER_CHROME  = "#d0d0d0"   # separator lines inside chrome areas
TEXT_CHROME     = "#222222"   # primary text on light chrome
TEXT_CHROME_DIM = "#6e6e6e"   # muted text on light chrome

# Content surfaces — clean white / neutral gray
BG_WINDOW       = "#ffffff"   # dialog / window background
BG_ELEVATED     = "#f5f5f5"   # group-box bg, alternating table rows, console
BG_PANEL        = "#ebebeb"   # table header, tab bar inactive

# Borders / dividers (content areas)
BORDER          = "#d0d0d0"   # input + group-box borders
BORDER_STRONG   = "#b8b8b8"   # tab pane / table outer border, stronger edges
DIVIDER         = "#e0e0e0"   # table grid lines, separator frames

# Text (content areas)
TEXT            = "#222222"   # default body text
TEXT_MUTED      = "#6e6e6e"   # secondary labels, hints, disabled
TEXT_INVERSE    = "#ffffff"   # text on accent fill / dark backgrounds

# Status indicators
STATUS_OK       = "#4caf50"
STATUS_ERROR    = "#e05555"
STATUS_IDLE     = "#8a9e8a"
STATUS_WARN     = "#d08800"

# ---------------------------------------------------------------------------
# Typography tokens
# ---------------------------------------------------------------------------
FONT_FAMILY     = '"Segoe UI", "Inter", "Arial", sans-serif'
FONT_MONO       = '"Consolas", "Courier New", monospace'

FS_XS   = "7pt"    # captions, console header
FS_SM   = "8pt"    # hints, secondary labels, tab labels
FS_BASE = "8.5pt"  # body / default
FS_MD   = "9.5pt"  # section titles
FS_LG   = "13pt"   # dialog headers
FS_XL   = "18pt"   # splash titles

# ---------------------------------------------------------------------------
# Spacing tokens (4-px grid)
# ---------------------------------------------------------------------------
SP_XS = 4
SP_SM = 8
SP_MD = 12
SP_LG = 16
SP_XL = 24

# ---------------------------------------------------------------------------
# Substitution table for QSS template loading
# ---------------------------------------------------------------------------
# Keys appear as @<key> in the .qss file. Order: longest first so e.g.
# @accent-pressed is replaced before @accent-soft before @accent.
QSS_SUBSTITUTIONS: dict[str, str] = {
    # chrome (longest keys first within group)
    "@bg-chrome-hover":    BG_CHROME_HOVER,
    "@bg-chrome":          BG_CHROME,
    "@divider-chrome":     DIVIDER_CHROME,
    "@text-chrome-dim":    TEXT_CHROME_DIM,
    "@text-chrome":        TEXT_CHROME,
    # accent
    "@accent-pressed":     ACCENT_PRESSED,
    "@accent-hover":       ACCENT_HOVER,
    "@accent-tint":        ACCENT_TINT,
    "@accent-soft":        ACCENT_SOFT,
    "@accent":             ACCENT,
    # surfaces
    "@bg-elevated":        BG_ELEVATED,
    "@bg-window":          BG_WINDOW,
    "@bg-panel":           BG_PANEL,
    # borders
    "@border-strong":      BORDER_STRONG,
    "@border":             BORDER,
    "@divider":            DIVIDER,
    # text
    "@text-inverse":       TEXT_INVERSE,
    "@text-muted":         TEXT_MUTED,
    "@text":               TEXT,
    # status
    "@status-ok":          STATUS_OK,
    "@status-error":       STATUS_ERROR,
    "@status-idle":        STATUS_IDLE,
    "@status-warn":        STATUS_WARN,
    # typography
    "@font-family":        FONT_FAMILY,
    "@font-mono":          FONT_MONO,
    "@fs-xs":              FS_XS,
    "@fs-sm":              FS_SM,
    "@fs-base":            FS_BASE,
    "@fs-md":              FS_MD,
    "@fs-lg":              FS_LG,
    "@fs-xl":              FS_XL,
}
