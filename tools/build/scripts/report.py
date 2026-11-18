"""
Shared console reporting utilities for build scripts.

Provides:
  - ANSI color support (auto-enabled on Windows 10+)
  - Unicode box-drawing helpers
  - Status icons and section headers
"""
import re
import sys

# ── ANSI virtual-terminal mode (Windows 10+) ──────────────────────────────────
def _enable_vt() -> bool:
    if sys.platform != 'win32':
        return True
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        k32.SetConsoleMode(k32.GetStdHandle(-11), 7)
        return True
    except Exception:
        return False

_COLOR = _enable_vt()

# ── ANSI codes ────────────────────────────────────────────────────────────────
RST  = '\033[0m'  if _COLOR else ''
BOLD = '\033[1m'  if _COLOR else ''
DIM  = '\033[2m'  if _COLOR else ''
GRN  = '\033[92m' if _COLOR else ''
RED  = '\033[91m' if _COLOR else ''
YLW  = '\033[93m' if _COLOR else ''
CYN  = '\033[96m' if _COLOR else ''
WHT  = '\033[97m' if _COLOR else ''

# ── Status icons ──────────────────────────────────────────────────────────────
OK_IC   = f'{GRN}✓{RST}'
FAIL_IC = f'{RED}✗{RST}'
WARN_IC = f'{YLW}⚠{RST}'
INFO_IC = f'{CYN}·{RST}'

# ── ANSI-aware string helpers ─────────────────────────────────────────────────
_ANSI_RE = re.compile(r'\033\[[0-9;]*m')

def vlen(s: str) -> int:
    """Visible length of *s* (ANSI escape codes do not count)."""
    return len(_ANSI_RE.sub('', s))

def pad(text: str, width: int) -> str:
    """Right-pad *text* to *width* visible characters."""
    return text + ' ' * max(0, width - vlen(text))

def trunc(s: str, max_w: int) -> str:
    """Truncate *s* to *max_w* characters, appending '...' if needed."""
    if len(s) <= max_w:
        return s
    return s[:max_w - 3] + '...'

def vtrunc(s: str, max_visible: int) -> str:
    """ANSI-aware truncation: keep colour codes intact, limit visible width.

    Truncated output ends with '...' followed by a reset code so colour never
    bleeds into whatever is printed afterwards.
    """
    if max_visible <= 0:
        return ''
    if vlen(s) <= max_visible:
        return s
    ellipsis = '...'
    limit = max(0, max_visible - len(ellipsis))
    out, visible, i, n = [], 0, 0, len(s)
    while i < n and visible < limit:
        m = _ANSI_RE.match(s, i)
        if m:
            out.append(m.group(0))
            i = m.end()
            continue
        out.append(s[i])
        visible += 1
        i += 1
    out.append(ellipsis)
    out.append(RST)
    return ''.join(out)

def format_bytes(n: float) -> str:
    """Human-readable byte size, e.g. 1536 -> '1.5 KB'."""
    size = float(n)
    for unit in ('B', 'KB', 'MB', 'GB'):
        if size < 1024 or unit == 'GB':
            return f'{int(size)} {unit}' if unit == 'B' else f'{size:.1f} {unit}'
        size /= 1024
    return f'{size:.1f} GB'

def format_duration(seconds: float) -> str:
    """Human-readable duration, e.g. 4.2 -> '4.2s', 93 -> '1m 33s'."""
    seconds = float(seconds)
    if seconds < 60:
        return f'{seconds:.1f}s'
    m, s = divmod(int(round(seconds)), 60)
    if m < 60:
        return f'{m}m {s:02d}s'
    h, m = divmod(m, 60)
    return f'{h}h {m:02d}m {s:02d}s'

# ── Box drawing ───────────────────────────────────────────────────────────────
# Inner visible width between the ║ border characters.
_W = 60
WIDTH = _W

def box_top(title: str = '') -> None:
    """Print the top border of a box, with an optional centred title."""
    if title:
        t = f' {BOLD}{WHT}{title}{RST} '
        tv = vlen(t)
        rem = _W - tv
        l, r = rem // 2, rem - rem // 2
        print(f'╔{"═" * l}{t}{"═" * r}╗')
    else:
        print(f'╔{"═" * _W}╗')

def box_sep() -> None:
    """Print a mid-box separator row."""
    print(f'╠{"═" * _W}╣')

def box_bot() -> None:
    """Print the bottom border of a box."""
    print(f'╚{"═" * _W}╝')

def box_blank() -> None:
    """Print an empty row inside a box."""
    print(f'║{" " * _W}║')

def box_row(label: str = '', value: str = '', label_w: int = 14) -> None:
    """Print a content row inside a box.

    If *value* is provided the row is formatted as:
        ║  {label:<label_w}  {value}  ║
    otherwise the label fills the full width.

    Overlong content is truncated (ANSI-aware) so the box border always
    stays aligned.
    """
    if label and value:
        prefix = f'  {DIM}{label:<{label_w}}{RST}  '
        avail = _W - vlen(prefix)
        text = prefix + (vtrunc(str(value), avail) if avail > 0 else '')
    elif label:
        text = vtrunc(f'  {label}', _W)
    else:
        text = ''
    print(f'║{pad(text, _W)}║')

def box_line(text: str) -> None:
    """Print an arbitrary pre-formatted line inside a box.

    Use for custom content (e.g. table headers/rows) that box_row's
    label/value layout doesn't fit. Truncated (ANSI-aware) to the box width.
    """
    print(f'║{pad(vtrunc(text, _W), _W)}║')

# ── Section headers ───────────────────────────────────────────────────────────
def section(title: str) -> None:
    """Print a section heading with an underline rule."""
    print(f'\n  {BOLD}{title}{RST}')
    print('  ' + '─' * 50)

# ── Status lines (outside a box) ─────────────────────────────────────────────
def ok(msg: str)   -> None: print(f'  {OK_IC}  {msg}')
def fail(msg: str) -> None: print(f'  {FAIL_IC}  {msg}')
def warn(msg: str) -> None: print(f'  {WARN_IC}  {msg}')
def info(msg: str) -> None: print(f'  {INFO_IC}  {msg}')
def hint(msg: str) -> None: print(f'     {DIM}{msg}{RST}')

# ── Progress bar (in-place, single line) ──────────────────────────────────────
def progress(current: int, total: int, *, width: int = 30, label: str = '') -> None:
    """Render/update an in-place progress bar for streaming operations.

    Call repeatedly with increasing *current*; the line is redrawn in place.
    Automatically prints a trailing newline once *current* reaches *total*.
    """
    pct = 100 if total <= 0 else max(0, min(100, int(current * 100 / total)))
    filled = int(width * pct / 100)
    bar = f'{GRN}{"█" * filled}{RST}{DIM}{"░" * (width - filled)}{RST}'
    size = f'{format_bytes(current)} / {format_bytes(total)}' if total else ''
    prefix = f'{label}  ' if label else ''
    line = f'  {prefix}[{bar}] {pct:>3}%  {DIM}{size}{RST}'
    sys.stdout.write(f'\r\033[K{line}')
    sys.stdout.flush()
    if pct >= 100:
        sys.stdout.write('\n')
        sys.stdout.flush()
