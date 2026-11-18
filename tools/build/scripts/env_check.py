"""
Pre-build environment checker.
Verifies that all tools, executables, Python packages, and keys required
for building and deploying the application are present and meet version
requirements.  Exit code 0 = all OK, 1 = one or more checks failed.
"""
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parents[3]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from build_config import PRIVATE_KEY_PATH, PUBLIC_KEY_PATH
from prj.config.builder.build_config import BuildConfig
import report

# ── Minimum required Python version ──────────────────────────────────────────
_REQUIRED_PYTHON = (3, 12)

# ── Python packages that must be importable ───────────────────────────────────
_REQUIRED_PACKAGES = [
    'PyInstaller',
    'PySide6',
    'cryptography',
    'requests',
    'packaging',
]

# ── Environment variables set by builder_env.bat that must point to files ─────
_REQUIRED_ENV_TOOLS = [
    ('PYTHON',      'Python interpreter'),
    ('PYUIC',       'pyside6-uic  (UI → Python compiler)'),
    ('PYRCC',       'pyside6-rcc  (Qt resource compiler)'),
    ('QTDESIGNER',  'pyside6-designer'),
    ('VTRACER',     'vtracer  (raster → SVG converter)'),
]


def _ok(label: str) -> None:
    report.ok(label)


def _fail(label: str) -> None:
    report.fail(label)


def _warn(label: str) -> None:
    report.warn(label)


def _section(title: str) -> None:
    report.section(title)


# ── Individual checks ─────────────────────────────────────────────────────────

def check_python_version() -> bool:
    v = sys.version_info
    label = f'Python {v.major}.{v.minor}.{v.micro}'
    if v[:2] == _REQUIRED_PYTHON:
        _ok(label)
        return True
    _fail(f'{label}  (need {".".join(str(x) for x in _REQUIRED_PYTHON)}.x)')
    return False


def check_env_tools() -> bool:
    all_ok = True
    for var, description in _REQUIRED_ENV_TOOLS:
        path = os.environ.get(var, '').strip()
        if not path:
            _fail(f'{var} not set  ({description})')
            all_ok = False
        elif Path(path).exists():
            _ok(f'{var} = {path}')
        else:
            _fail(f'{var} not found: {path}  ({description})')
            all_ok = False
    return all_ok


def check_packages() -> bool:
    all_ok = True
    for pkg in _REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            ver = getattr(mod, '__version__', '?')
            _ok(f'{pkg}  {ver}')
        except ImportError:
            _fail(f'{pkg}  (not installed)')
            all_ok = False
    return all_ok


def check_git() -> bool:
    git = shutil.which('git')
    if not git:
        _fail('git not found in PATH')
        return False
    try:
        ver = subprocess.check_output(
            ['git', '--version'], stderr=subprocess.DEVNULL
        ).decode().strip()
        subprocess.check_output(
            ['git', '-C', str(_ROOT_DIR), 'rev-parse', '--git-dir'],
            stderr=subprocess.DEVNULL
        )
        _ok(f'{ver}  (repo OK)')
        return True
    except subprocess.CalledProcessError:
        _warn(f'{git}  (not inside a git repository)')
        return True   # non-fatal; building works without a repo


def check_signing_keys() -> bool:
    all_ok = True
    for label, path in [('Private key', PRIVATE_KEY_PATH),
                         ('Public key ', PUBLIC_KEY_PATH)]:
        if Path(path).exists():
            _ok(f'{label}: {path}')
        else:
            _fail(f'{label} not found: {path}')
            all_ok = False
    return all_ok


def check_build_config() -> bool:
    all_ok = True
    entry = _ROOT_DIR / BuildConfig.APP_SCRIPT.lstrip('/\\')
    if entry.exists():
        _ok(f'APP_SCRIPT  : {BuildConfig.APP_SCRIPT}')
    else:
        _fail(f'APP_SCRIPT not found: {entry}')
        all_ok = False

    icon = _ROOT_DIR / BuildConfig.ICON_PATH.lstrip('/\\')
    if icon.exists():
        _ok(f'ICON_PATH   : {BuildConfig.ICON_PATH}')
    else:
        _fail(f'ICON_PATH not found: {icon}')
        all_ok = False
    return all_ok


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    report.box_top('BUILD ENVIRONMENT CHECK')
    report.box_blank()
    report.box_bot()

    results = []

    _section('Python runtime')
    results.append(check_python_version())

    _section('Build tool executables  (from builder_env.bat)')
    results.append(check_env_tools())

    _section('Required Python packages')
    results.append(check_packages())

    _section('Git')
    results.append(check_git())

    _section('Signing keys')
    results.append(check_signing_keys())

    _section('Build config paths')
    results.append(check_build_config())

    print()
    if all(results):
        report.ok('All checks passed. Ready to build.')
        return 0
    else:
        report.fail('Some checks failed. Fix the issues above before building.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
