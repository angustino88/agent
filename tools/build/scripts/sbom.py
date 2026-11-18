"""
Software Bill of Materials (SBOM) generator.

Captures a snapshot of every installed Python package at build time.
Output: <DIST_DIR>/<AppName>-<version>-sbom.json

Usage (standalone):
  python sbom.py                           # auto-detect output from build config
  python sbom.py --output path/to/out.json

Called automatically by build.py at the end of each successful build.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import report

_ROOT_DIR = Path(__file__).resolve().parents[3]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


def generate(output_path: str, version: str, app_name: str = '') -> str:
    """Write an SBOM JSON file to *output_path* and return the path.

    The file lists every package visible to the current Python interpreter,
    along with metadata about when and by whom the build was run.
    """
    packages = _list_packages()
    data = {
        'sbom_format':   'custom-pip-list/1.0',
        'generated_at':  datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        'python_version': sys.version,
        'app_name':       app_name,
        'app_version':    version,
        'package_count':  len(packages),
        'packages':       packages,
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    report.ok(f'SBOM written to {out.name} ({len(packages)} packages)')
    return str(out)


def _list_packages() -> list[dict]:
    """Return [{name, version}, ...].

    Attempt multiple methods to discover installed packages in order of
    reliability/availability:
      1. `importlib.metadata.distributions()` (standard library)
      2. `pkg_resources.working_set` (setuptools)
      3. `python -m pip list --format=json` (subprocess fallback)

    Using the in-process APIs avoids failures when `pip` is unavailable
    or when invoking subprocesses is restricted.
    """
    # 1) importlib.metadata (preferred)
    try:
        try:
            from importlib.metadata import distributions
        except Exception:
            # Backport name for older environments
            from importlib_metadata import distributions

        pkgs: list[dict] = []
        for dist in distributions():
            try:
                name = dist.metadata.get('Name') or getattr(dist, 'name', None)
            except Exception:
                name = getattr(dist, 'name', None)
            version = getattr(dist, 'version', None)
            if name:
                pkgs.append({'name': name, 'version': version})
        if pkgs:
            return sorted(pkgs, key=lambda p: p.get('name', '').lower())
    except Exception as exc:
        # Fall through to next method
        report.hint(f'importlib.metadata unavailable: {exc}')

    # 2) pkg_resources (setuptools)
    try:
        import pkg_resources

        pkgs = [{'name': d.project_name, 'version': d.version} for d in pkg_resources.working_set]
        if pkgs:
            return sorted(pkgs, key=lambda p: p.get('name', '').lower())
    except Exception as exc:
        report.hint(f'pkg_resources unavailable: {exc}')

    # 3) pip (fallback via subprocess)
    try:
        raw = subprocess.check_output(
            [sys.executable, '-m', 'pip', 'list', '--format=json'],
            stderr=subprocess.DEVNULL,
        ).decode()
        return sorted(json.loads(raw), key=lambda p: p.get('name', '').lower())
    except Exception as exc:
        report.warn(f'Could not read pip list: {exc}')
        return []


def main() -> None:
    from build_config import DIST_DIR
    from prj.config.builder.build_config import BuildConfig
    from prj.config.version.version_config import VersionConfig

    parser = argparse.ArgumentParser(description='Generate a Software Bill of Materials.')
    parser.add_argument(
        '--output', metavar='PATH',
        help='Output path (default: <DIST_DIR>/<AppName>-<version>-sbom.json)',
    )
    args = parser.parse_args()

    out = args.output or str(
        Path(DIST_DIR) / f'{BuildConfig.APP_NAME}-{VersionConfig.APP_VERSION}-sbom.json'
    )
    generate(out, VersionConfig.APP_VERSION, BuildConfig.APP_NAME)


if __name__ == '__main__':
    main()
