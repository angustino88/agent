import json
import os
import subprocess
import sys
import shutil
import time
from datetime import datetime
from pathlib import Path
from zip import ZipUtil
from build_config import *
from build_config import _resolve_path, _ROOT_DIR
from meta_build import build_meta_json
from update_index import update_index
from sign_package import sign_exe, verify_exe_signature
import PyInstaller.__main__
import build_history
from sbom import generate as _gen_sbom
import report

#=============================================================
# Create build environment
#=============================================================
def _rotate_log():
    """Archive the previous log file with a timestamp suffix, keeping the last 10."""
    log_path = Path(LOG_FILE)
    if log_path.exists() and log_path.stat().st_size > 0:
        ts = time.strftime("%Y%m%d_%H%M%S")
        archive = log_path.with_name(log_path.stem + f'_{ts}' + log_path.suffix)
        shutil.copy2(log_path, archive)
        # Prune: keep only the 10 most recent archives
        archives = sorted(log_path.parent.glob(log_path.stem + '_*' + log_path.suffix))
        for old in archives[:-10]:
            old.unlink(missing_ok=True)


def validate_inputs():
    """Fail fast when required input files are missing before PyInstaller starts."""
    checks = [
        (_resolve_path(_ROOT_DIR, BuildConfig.APP_SCRIPT), 'Entry script (BuildConfig.APP_SCRIPT)'),
        (_resolve_path(_ROOT_DIR, BuildConfig.ICON_PATH),  'Icon file (BuildConfig.ICON_PATH)'),
        (PRIVATE_KEY_PATH, 'Private key (prj/config/keys/ed25519_priv.pem)'),
        (PUBLIC_KEY_PATH,  'Public key  (prj/config/keys/ed25519_pub.pem)'),
    ]
    missing = [(path, label) for path, label in checks if not os.path.isfile(path)]
    if missing:
        for path, label in missing:
            report.fail(f'Missing {label}: {path}')
        sys.exit(1)


def _check_changelog_not_empty():
    """Warn (or abort) when CHANGELOG is empty to avoid shipping release notes-free builds."""
    if not VersionConfig.CHANGELOG:
        report.warn('VersionConfig.CHANGELOG is empty — meta.json will have no release notes.')


def setup_env():
    """Create build directories and prepare environment."""
    for directory in [TMP_DIR, DIST_DIR, LOG_DIR]:
        os.makedirs(directory, exist_ok=True)
    _rotate_log()
    with open(LOG_FILE, 'w'):
        pass
    validate_version()
    write_build_info_file()
    write_version_config_file()

#=============================================================
# Create build arguments for PyInstaller
#=============================================================
def create_build_args():
    """Populate build_args using BUILD_SPECS."""
    for spec in BUILD_SPECS:
        if callable(spec.handler):
            spec.handler(spec.flag, spec.value, spec.condition)

#=============================================================
# Move versioned build output
#=============================================================
def _move_versioned_app(app_dir, app_dir_with_version):
    """Move the built app to its versioned folder with retries."""
    if os.path.exists(app_dir_with_version):
        shutil.rmtree(app_dir_with_version)

    last_error = None
    for attempt in range(5):
        try:
            os.rename(app_dir, app_dir_with_version)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))

    try:
        shutil.copytree(app_dir, app_dir_with_version)
        shutil.rmtree(app_dir)
    except Exception:
        if last_error is not None:
            raise last_error
        raise

#=============================================================
# Build summary
#=============================================================
def _print_build_summary(
    zip_file:  str | None,
    elapsed_s: float,
    pkg_meta:  tuple = (None, None, None),
) -> None:
    """Print a styled summary box at the end of the build."""
    import report

    pkg_name, size_mb, sha256 = pkg_meta if any(pkg_meta) else _package_meta(zip_file)
    size_str = f'{size_mb:.1f} MB' if size_mb else None

    # — Git info
    git_info: str | None = None
    try:
        sha = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL, cwd=str(_ROOT_DIR)
        ).decode().strip()
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL, cwd=str(_ROOT_DIR)
        ).decode().strip()
        git_info = f'{report.CYN}{sha}{report.RST}  {report.DIM}({branch}){report.RST}'
    except Exception:
        pass

    # — Render
    print()
    report.box_top('BUILD SUMMARY')
    report.box_blank()
    report.box_row('Application',
        f'{report.BOLD}{BuildConfig.APP_NAME}{report.RST}  '
        f'{report.GRN}{report.BOLD}{VersionConfig.APP_VERSION}{report.RST}')
    if git_info:
        report.box_row('Git commit', git_info)
    report.box_row('Built at',  datetime.now().strftime('%Y-%m-%d  %H:%M:%S'))
    report.box_row('Duration',  report.format_duration(elapsed_s))

    if pkg_name:
        report.box_blank()
        report.box_sep()
        report.box_blank()
        report.box_row('Package', f'{report.WHT}{pkg_name}{report.RST}')
        report.box_row('Size',    size_str)
        # Split SHA-256 across two visual rows
        report.box_row('SHA-256', f'{report.DIM}{sha256[:42]}{report.RST}')
        report.box_row('',        f'{report.DIM}{sha256[42:]}{report.RST}')

    report.box_blank()
    report.box_bot()
    print()


#=============================================================
# Dry-run: show build plan without executing
#=============================================================
def _dry_run() -> None:
    """Print what would be built and exit 0 — nothing is executed."""
    import report

    steps: list[str] = []
    mode = 'one-file' if getattr(BuildConfig, 'ONEFILE', 'FALSE') == 'TRUE' else 'one-folder'
    steps.append(f'PyInstaller  ({mode})')
    if BuildConfig.SIGN_PACKAGE == 'TRUE':
        steps.append('Sign EXE  (Ed25519)')
    if BuildConfig.VERSION_LABEL == 'TRUE':
        steps.append(f'Rename output → {BuildConfig.APP_NAME}-{VersionConfig.APP_VERSION}/')
    if BuildConfig.ZIP == 'TRUE':
        steps.append(f'Zip package  → {BuildConfig.APP_NAME}-{VersionConfig.APP_VERSION}.zip')
    if BuildConfig.META_FILE == 'TRUE':
        steps.append('Write meta.json')
    if BuildConfig.UPDATE_INDEX == 'TRUE':
        steps.append('Update index.json  (+ sign)')
    steps.append('Generate SBOM  (pip list snapshot)')
    steps.append('Record build history')

    print()
    report.box_top('DRY RUN — nothing will be built')
    report.box_blank()
    report.box_row('Application',
        f'{report.BOLD}{BuildConfig.APP_NAME}{report.RST}  '
        f'{report.GRN}{VersionConfig.APP_VERSION}{report.RST}')
    report.box_row('Entry script', BuildConfig.APP_SCRIPT)
    report.box_row('Icon',         BuildConfig.ICON_PATH)
    report.box_row('Output dir',   DIST_REL_DIR)
    report.box_blank()
    report.box_sep()
    report.box_blank()
    report.box_row(f'{report.BOLD}Steps that would run:{report.RST}')
    for step in steps:
        report.box_row('', f'{report.INFO_IC}  {step}')
    report.box_blank()
    report.box_bot()
    print()


#=============================================================
# Package metadata helper (SHA-256 computed once)
#=============================================================
def _package_meta(zip_file: str | None) -> tuple:
    """Return (pkg_name, size_mb, sha256) for *zip_file*, or (None, None, None)."""
    if not zip_file or not os.path.isfile(zip_file):
        return None, None, None
    import hashlib
    h = hashlib.sha256()
    with open(zip_file, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    size_mb = os.path.getsize(zip_file) / (1024 * 1024)
    return os.path.basename(zip_file), size_mb, h.hexdigest()


#=============================================================
# SBOM generation (non-fatal)
#=============================================================
def _generate_sbom(zip_file: str | None) -> None:
    """Write an SBOM JSON alongside the release package."""
    try:
        out = os.path.join(
            DIST_DIR,
            f'{BuildConfig.APP_NAME}-{VersionConfig.APP_VERSION}-sbom.json',
        )
        _gen_sbom(out, VersionConfig.APP_VERSION, BuildConfig.APP_NAME)
    except Exception as exc:
        report.warn(f'SBOM generation failed: {exc}')


#=============================================================
# Build history (non-fatal)
#=============================================================
def _record_build_history(
    outcome: str,
    zip_file: str | None,
    elapsed_s: float,
    pkg_name:  str | None = None,
    size_mb:   float | None = None,
    sha256:    str | None = None,
) -> None:
    """Append one entry to the build audit log."""
    try:
        git_sha = git_branch = ''
        try:
            git_sha    = subprocess.check_output(
                ['git', 'rev-parse', '--short', 'HEAD'],
                stderr=subprocess.DEVNULL, cwd=str(_ROOT_DIR)
            ).decode().strip()
            git_branch = subprocess.check_output(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                stderr=subprocess.DEVNULL, cwd=str(_ROOT_DIR)
            ).decode().strip()
        except Exception:
            pass

        build_history.record({
            'version':    VersionConfig.APP_VERSION,
            'git_sha':    git_sha,
            'git_branch': git_branch,
            'duration_s': round(elapsed_s, 1),
            'outcome':    outcome,
            'package':    pkg_name,
            'size_mb':    round(size_mb, 2) if size_mb else None,
            'sha256':     sha256,
        })
    except Exception as exc:
        report.warn(f'Could not record build history: {exc}')


#=============================================================
# Clean build directories
#=============================================================
def clean():
    """Remove build directories if they exist."""
    for directory in [TMP_DIR, DIST_DIR, LOG_DIR]:
        if os.path.exists(directory):
            shutil.rmtree(directory)

#=============================================================
# Build process
#=============================================================
def build():
    """Run the full build process."""
    _check_changelog_not_empty()
    validate_inputs()
    setup_env()
    _build_start = time.time()
    create_build_args()

    zip_file = None
    elapsed  = 0.0
    outcome  = 'failure'
    pkg_meta = (None, None, None)   # (pkg_name, size_mb, sha256)

    try:
        app_dir = os.path.join(DIST_DIR, f'{BuildConfig.APP_NAME}')
        bundle_dir_name = getattr(BuildConfig, 'CONTENTS_DIRECTORY', '')
        bundle_dir = os.path.join(app_dir, bundle_dir_name) if bundle_dir_name else app_dir
        build_extension = BuildExtension(bundle_dir, BuildConfig.APP_NAME, VersionConfig.APP_VERSION, build_args)
        build_extension.before()
        PyInstaller.__main__.run(build_args)
        build_extension.after()

        if BuildConfig.SIGN_PACKAGE == 'TRUE':
            exe_path = os.path.join(app_dir, f'{BuildConfig.APP_NAME}.exe')
            sig_path = os.path.join(bundle_dir, 'package.sig')
            sign_exe(exe_path, PRIVATE_KEY_PATH, sig_path)
            verify_exe_signature(exe_path, PUBLIC_KEY_PATH, sig_path)

        if BuildConfig.VERSION_LABEL == 'TRUE':
            app_dir_with_version = f'{app_dir}-{VersionConfig.APP_VERSION}'
            _move_versioned_app(app_dir, app_dir_with_version)
            app_dir = app_dir_with_version

        if BuildConfig.ZIP == 'TRUE':
            zip_file = f'{app_dir}.zip'
            ZipUtil.zip_directory(app_dir, zip_file)

        if BuildConfig.META_FILE == 'TRUE':
            meta_file = os.path.join(DIST_DIR, 'meta.json')
            build_meta_json(zip_file, meta_file)

        if BuildConfig.UPDATE_INDEX == 'TRUE':
            # Pass output_path so the committed template (INDEX_JSON_PATH) is never
            # modified. The signed artifact lands only in DIST_DIR/index.json.
            update_index(VersionConfig.APP_VERSION, PRIVATE_KEY_PATH, INDEX_JSON_PATH,
                         DIST_DIR, metadata_url=BuildConfig.META_URL,
                         output_path=Path(DIST_DIR) / 'index.json')

        outcome  = 'success'
        elapsed  = time.time() - _build_start
        pkg_meta = _package_meta(zip_file)
        _print_build_summary(zip_file, elapsed, pkg_meta)
        _generate_sbom(zip_file)

    except Exception:
        elapsed = time.time() - _build_start
        raise
    finally:
        _record_build_history(outcome, zip_file, elapsed, *pkg_meta)

        # Post-build: remove temporary build_info.py created in TMP_DIR
        try:
            tmp_build_info = Path(TMP_DIR) / 'build_info.py'
            if tmp_build_info.exists():
                tmp_build_info.unlink()
        except Exception as exc:
            report.warn(f'Failed to remove temporary build_info: {exc}')

#=============================================================
# Rebuild process
#=============================================================
def rebuild():
    """Clean and then build."""
    clean()
    build()

#=============================================================
# Main entry point
#=============================================================
if __name__ == '__main__':
    """
    Build modes:
        --build      incremental build (reuse PyInstaller cache)
        --rebuild    clean then build
        --clean      remove all build artefacts
        --dry-run    show what would be built without running anything
    """
    if len(sys.argv) < 2:
        print('Usage: build.py [--build|--rebuild|--clean|--dry-run]')
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == '--build':
        build()
    elif mode == '--rebuild':
        rebuild()
    elif mode == '--clean':
        clean()
    elif mode == '--dry-run':
        _dry_run()
    else:
        print(f'Unknown mode: {mode}')
        sys.exit(1)
