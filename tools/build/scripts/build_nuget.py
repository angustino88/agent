#!/usr/bin/env python3
"""
Build the Chocolatey NuGet package for the current project.

Steps
-----
1. Locate the built ZIP artifact in DIST_DIR.
2. Create a staging directory with the nuspec (already version-synced by
   bump_version.py) and the chocolatey scripts.
3. Copy the built ZIP into staging/tools/ as <AppName>.zip (name expected by
   chocolateyinstall.ps1).
4. Run ``choco pack`` to produce the .nupkg.
5. Output the .nupkg to DIST_DIR and clean up the staging area.

The nuspec version and release notes are kept in sync with version_config.py
by bump_version.py (08_bump_version.bat), so no runtime patching is needed
here.

Usage
-----
  python tools/build/scripts/build_nuget.py
"""
import os
import re
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape as xml_escape
from pathlib import Path

# build_config adds _ROOT_DIR to sys.path so downstream imports work
from build_config import DIST_DIR, _ROOT_DIR
from prj.config.version.version_config import VersionConfig
from prj.config.builder.build_config import BuildConfig
import report

# ---------------------------------------------------------------------------
# Paths derived from project layout
# ---------------------------------------------------------------------------
NUGET_CONFIG_DIR = Path(_ROOT_DIR) / 'prj' / 'config' / 'nuget'
NUGET_TOOLS_SRC  = NUGET_CONFIG_DIR / 'tools'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_nuspec(nuget_config_dir: Path) -> Path:
    """Discover the .nuspec file in *nuget_config_dir* (project-agnostic).

    Raises FileNotFoundError if no .nuspec is present so the caller gets a
    clear error rather than a silent no-op.
    """
    candidates = sorted(nuget_config_dir.glob('*.nuspec'))
    if not candidates:
        raise FileNotFoundError(
            f'No .nuspec file found in {nuget_config_dir}. '
            'Add a <appname>.nuspec to prj/config/nuget/ first.'
        )
    return candidates[0]


def _copy_with_tokens(src: Path, dst: Path, tokens: dict) -> None:
    """Copy *src* tree to *dst*, substituting ``{{TOKEN}}`` placeholders in
    text files (.ps1, .bat, .txt, .md) with project-specific values.

    Binary files are copied verbatim.
    """
    _TEXT_EXTS = {'.ps1', '.bat', '.txt', '.md', '.nuspec'}
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in _TEXT_EXTS:
            content = src.read_text(encoding='utf-8')
            for placeholder, value in tokens.items():
                content = content.replace(placeholder, value)
            if src.suffix.lower() == '.nuspec':
                unresolved = re.findall(r'\{\{[^{}]+\}\}', content)
                if unresolved:
                    raise ValueError(
                        f'Unresolved nuspec token(s) in {src.name}: '
                        + ', '.join(sorted(set(unresolved)))
                    )
            dst.write_text(content, encoding='utf-8')
        else:
            shutil.copy2(str(src), str(dst))
        return

    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        dest_item = dst / item.name
        if item.is_dir():
            _copy_with_tokens(item, dest_item, tokens)
        elif item.suffix.lower() in _TEXT_EXTS:
            content = item.read_text(encoding='utf-8')
            for placeholder, value in tokens.items():
                content = content.replace(placeholder, value)
            dest_item.write_text(content, encoding='utf-8')
        else:
            shutil.copy2(str(item), str(dest_item))


def _find_zip(dist_dir: str, app_name: str, version: str) -> Path:
    """Return the path to the built ZIP artifact.

    Looks first for the canonical versioned name ``<AppName>-<version>.zip``.
    Falls back to any ``.zip`` in *dist_dir* so the script is resilient to
    minor naming variations in BuildConfig.
    """
    expected = Path(dist_dir) / f'{app_name}-{version}.zip'
    if expected.exists():
        return expected

    zips = sorted(Path(dist_dir).glob('*.zip'))
    if not zips:
        raise FileNotFoundError(
            f'No ZIP artifact found in {dist_dir}. '
            'Run the software build (05_build.bat / 06_rebuild.bat) first.'
        )
    return zips[-1]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_nuget() -> None:
    version  = VersionConfig.APP_VERSION
    app_name = BuildConfig.APP_NAME
    package_id = getattr(BuildConfig, 'NUGET_PACKAGE_ID', app_name.lower())

    print()
    report.box_top('NUGET PACKAGE')
    report.box_blank()
    report.box_row('Application', f'{report.BOLD}{app_name}{report.RST}')
    report.box_row('Package ID', f'{report.CYN}{package_id}{report.RST}')
    report.box_row('Version', f'{report.GRN}{report.BOLD}{version}{report.RST}')
    report.box_blank()
    report.box_bot()

    # -- Locate artifacts ------------------------------------------------------
    zip_file   = _find_zip(DIST_DIR, app_name, version)
    nuspec_src = _find_nuspec(NUGET_CONFIG_DIR)
    report.section('Input artifacts')
    report.info(f'ZIP    {report.DIM}{zip_file.name}{report.RST}')
    report.info(f'Nuspec {report.DIM}{nuspec_src.name}{report.RST}')

    # -- Create a clean staging directory -------------------------------------
    staging_dir = Path(DIST_DIR) / '_nuget_staging'
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    try:
        # Copy chocolatey scripts with token substitution (project-agnostic templates)
        tokens = {
            '{{APP_NAME}}':         app_name,
            '{{APP_DISPLAY_NAME}}': getattr(BuildConfig, 'APP_DISPLAY_NAME', app_name),
            '{{PACKAGE_ID}}':        getattr(BuildConfig, 'NUGET_PACKAGE_ID', app_name.lower()),
            '{{PACKAGE_AUTHORS}}':   getattr(BuildConfig, 'NUGET_AUTHORS', 'Package Authors'),
            '{{APP_DESCRIPTION}}':   getattr(BuildConfig, 'NUGET_DESCRIPTION',
                                               getattr(BuildConfig, 'APP_DISPLAY_NAME', app_name)),
            '{{VERSION}}':           version,
            '{{RELEASE_NOTES}}':     '\t\t' + '\n\t\t'.join(
                xml_escape(str(note)) for note in getattr(VersionConfig, 'CHANGELOG', [])
            ),
            '{{PACKAGE_TAGS}}':       getattr(BuildConfig, 'NUGET_TAGS', app_name.lower()),
            '{{REQUIRE_LICENSE_ACCEPTANCE}}': str(
                getattr(BuildConfig, 'NUGET_REQUIRE_LICENSE_ACCEPTANCE', False)
            ).lower(),
            '{{PACKAGE_COPYRIGHT}}':  getattr(BuildConfig, 'NUGET_COPYRIGHT', ''),
        }
        tools_dst = staging_dir / 'tools'
        _copy_with_tokens(NUGET_TOOLS_SRC, tools_dst, tokens)

        # Preserve the version in the package filename. The installer derives
        # the same name from ChocolateyPackageVersion.
        packaged_zip_name = f'{app_name}-{version}.zip'
        shutil.copy2(str(zip_file), str(tools_dst / packaged_zip_name))

        # Copy the committed nuspec and resolve project metadata tokens.
        nuspec_dst = staging_dir / nuspec_src.name
        _copy_with_tokens(nuspec_src, nuspec_dst, tokens)

        report.section('Packaging')
        report.info(f'Rendered metadata into {report.DIM}{nuspec_dst.name}{report.RST}')
        report.info(f'Included application archive as {report.DIM}{packaged_zip_name}{report.RST}')

        # -- Run choco pack ---------------------------------------------------
        report.info('Running Chocolatey pack')
        result = subprocess.run(
            ['choco', 'pack', nuspec_dst.name, '--out', str(Path(DIST_DIR))],
            cwd=str(staging_dir),
        )

        if result.returncode != 0:
            report.fail('Chocolatey package creation failed.')
            sys.exit(result.returncode)

    finally:
        # Always clean up staging regardless of success/failure
        shutil.rmtree(staging_dir, ignore_errors=True)

    # -- Report the output file -----------------------------------------------
    expected_nupkg = Path(DIST_DIR) / f'{nuspec_src.stem}.{version}.nupkg'
    if expected_nupkg.exists():
        package_path = expected_nupkg
    else:
        pkgs = sorted(Path(DIST_DIR).glob('*.nupkg'))
        if pkgs:
            package_path = pkgs[-1]
        else:
            report.fail('Chocolatey completed, but no .nupkg was found in the build output.')
            sys.exit(1)

    report.section('Result')
    report.ok(f'Created {report.BOLD}{package_path.name}{report.RST}')
    report.hint(str(package_path.resolve()))
    print()


if __name__ == '__main__':
    build_nuget()
