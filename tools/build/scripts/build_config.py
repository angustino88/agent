import os
import re
import sys
import logging
from typing import Any, Callable, NamedTuple, Optional
from logging import getLogger
from pathlib import Path
from packaging.version import parse as parse_version
import PyInstaller.__main__

_ROOT_DIR = Path(__file__).resolve().parents[3]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

# Sync PyInstaller logger
logger = getLogger('PyInstaller')

from prj.config.builder.build_config import BuildConfig
from prj.config.builder.build_extension import BuildExtension
from prj.config.version.version_config import VersionConfig

def _resolve_path(*parts) -> str:
    """Join path components, stripping leading slashes from non-root parts."""
    base = Path(parts[0])
    for part in parts[1:]:
        base = base / str(part).lstrip('/\\')
    return str(base)

# Define sub-folder in build folder
TMP_REL_DIR  = 'prj/build/tmp'
DIST_REL_DIR = 'prj/build/app'
LOG_REL_DIR  = 'prj/build/log'
LOG_REL_FILE = 'prj/build/log/01_logs.txt'

TMP_DIR  = _resolve_path(_ROOT_DIR, TMP_REL_DIR)
DIST_DIR = _resolve_path(_ROOT_DIR, DIST_REL_DIR)
LOG_DIR  = _resolve_path(_ROOT_DIR, LOG_REL_DIR)
LOG_FILE = _resolve_path(_ROOT_DIR, LOG_REL_FILE)

# Define version info file
VERSION_CONFIG_FILE = _resolve_path(TMP_DIR, 'version_config.rc')

PRIVATE_KEY_PATH = _resolve_path(_ROOT_DIR, 'prj/config/keys/ed25519_priv.pem')
PUBLIC_KEY_PATH = _resolve_path(_ROOT_DIR, 'prj/config/keys/ed25519_pub.pem')
INDEX_JSON_PATH = _resolve_path(_ROOT_DIR, 'prj/config/version/index.json')

build_args = []

#========================================================================================
# PyInstaller argument builder functions
#========================================================================================

def configure_log_file(flag, value, condition):
    """Attach a file handler to the PyInstaller logger."""
    if value:
        logger.addHandler(logging.FileHandler(_resolve_path(_ROOT_DIR, value)))

def append_flag(flag, value, condition):
    """Append a PyInstaller flag to build_args if value matches condition (case-insensitive)."""
    if flag and value and condition:
        if str(value).lower() == str(condition).lower():
            build_args.append(str(flag))

def append_script(flag, value, condition):
    """Append the entry-point script path to build_args."""
    if value:
        build_args.append(_resolve_path(_ROOT_DIR, value))

def append_value(flag, value, condition):
    """Append a flag=value string to build_args."""
    if flag and value:
        build_args.append(f'{flag}={value}')

def append_path(flag, value, condition):
    """Append a flag=<resolved_path> argument to build_args."""
    if flag and value:
        build_args.append(f'{flag}={_resolve_path(_ROOT_DIR, value)}')

def append_excludes(flag, modules, condition):
    """Append one --exclude-module entry per module to build_args."""
    if flag and modules:
        for module in modules:
            if module:
                build_args.append(f'{flag}={module}')

def append_folders(flag, folders, condition):
    """Append one --add-data entry per folder to build_args."""
    if flag and folders:
        for rel_folder in folders:
            if rel_folder:
                folder_name = os.path.basename(rel_folder)
                build_args.append(f'{flag}={_resolve_path(_ROOT_DIR, rel_folder)};{folder_name}')

def append_files(flag, files, condition):
    """Append one --add-data entry per file to build_args."""
    if flag and files:
        for rel_file in files:
            if rel_file:
                build_args.append(f'{flag}={_resolve_path(_ROOT_DIR, rel_file)};.')

def append_contents_directory(flag, value, condition):
    """Append the PyInstaller contents directory for one-folder builds."""
    if flag and value and str(BuildConfig.ONEFILE).upper() == 'FALSE':
        build_args.append(f'{flag}={value}')

def validate_version():
    """Validate the version string format."""
    version = VersionConfig.APP_VERSION
    assert len(str(version).split('.')) == 3, f'Invalid version: {version}'
    parse_version(version)

def write_build_info_file():
    """Write a temporary build_info.py with git commit, branch, and build date.

    The file is written into the build TMP_DIR and registered with PyInstaller via
    an ``--add-data`` entry so the built artifact contains the file but the
    repository workspace is not modified.
    """
    import subprocess
    from datetime import datetime
    from pathlib import Path

    git_sha = git_branch = 'unknown'
    try:
        git_sha = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL, cwd=str(_ROOT_DIR)
        ).decode().strip()
        git_branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL, cwd=str(_ROOT_DIR)
        ).decode().strip()
    except Exception:
        pass

    build_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Write into the build temp directory so the repo tree is not polluted
    tmp_out = Path(TMP_DIR) / 'build_info.py'
    tmp_out.parent.mkdir(parents=True, exist_ok=True)
    tmp_out.write_text(
        f'class BuildInfo:\n'
        f'    GIT_COMMIT:  str = {git_sha!r}\n'
        f'    GIT_BRANCH:  str = {git_branch!r}\n'
        f'    BUILD_DATE:  str = {build_date!r}\n',
        encoding='utf-8',
    )

    # Ensure PyInstaller includes this file in the distribution under
    # prj/config/version so imports like ``prj.config.version.build_info`` work
    # when the app is frozen. Use the same add-data semantics as append_files.
    add_data_arg = f"--add-data={_resolve_path(_ROOT_DIR, TMP_REL_DIR, 'build_info.py')};prj/config/version"
    build_args.append(add_data_arg)

    import report
    report.info(
        f'build_info.py prepared for bundling  '
        f'commit={git_sha}  branch={git_branch}'
    )


def write_version_config_file():
    """Write version config file for PyInstaller, handling pre-release versions."""
    with open(VERSION_CONFIG_FILE, 'w', encoding='utf-8') as f:
        # Split numeric parts
        major, minor, patch = VersionConfig.APP_VERSION.split('.')[:3]

        # Remove any pre-release suffix from patch for numeric filevers
        patch_numeric = patch
        if not patch.isdigit():
            m = re.search(r'\d+', patch)
            patch_numeric = m.group(0) if m else '0'

        f.write(f"VSVersionInfo(\n")
        f.write(f"  ffi=FixedFileInfo(\n")
        f.write(f"    filevers=({major}, {minor}, {patch_numeric}, 0),\n")
        f.write(f"    prodvers=({major}, {minor}, {patch_numeric}, 0),\n")
        f.write(f"    mask=0x3f,\n")
        f.write(f"    flags=0x0,\n")
        f.write(f"    OS=0x40004,\n")
        f.write(f"    fileType=0x1,\n")
        f.write(f"    subtype=0x0,\n")
        f.write(f"    date=(0, 0)\n")
        f.write(f"    ),\n")
        f.write(f"  kids=[\n")
        f.write(f"    StringFileInfo(\n")
        f.write(f"      [\n")
        f.write(f"      StringTable(\n")
        f.write(f"        u'040904B0',\n")
        f.write(f"        [StringStruct(u'CompanyName', u'Company'),\n")
        f.write(f"        StringStruct(u'FileDescription', u'{BuildConfig.APP_NAME}.exe'),\n")
        f.write(f"        StringStruct(u'FileVersion', u'{VersionConfig.APP_VERSION}'),\n")
        f.write(f"        StringStruct(u'LegalCopyright', u'\xa9 Company. All rights reserved.'),\n")
        f.write(f"        StringStruct(u'ProductName', u'{BuildConfig.APP_NAME}.exe'),\n")
        f.write(f"        StringStruct(u'ProductVersion', u'{VersionConfig.APP_VERSION}')])\n")
        f.write(f"      ]), \n")
        f.write(f"    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])\n")
        f.write(f"  ]\n")
        f.write(f")")

#========================================================================================
# Build argument specification
#========================================================================================
class BuildSpec(NamedTuple):
    handler:   Callable
    flag:      Optional[str]
    value:     Any
    condition: Optional[str]

#========================================================================================
# Ordered list of build argument specifications.
# Each entry defines a handler, its PyInstaller flag, the config value, and an optional
# condition that must match the value (case-insensitive) for the flag to be emitted.
#========================================================================================
BUILD_SPECS = [
    # handler                  flag                    value                         condition
    BuildSpec(append_script,      None,               BuildConfig.APP_SCRIPT,        None),    # 0
    BuildSpec(append_value,       '--name',           BuildConfig.APP_NAME,          None),    # 1
    BuildSpec(append_path,        '--workpath',       TMP_REL_DIR,                   None),    # 2
    BuildSpec(append_path,        '--distpath',       DIST_REL_DIR,                  None),    # 3
    BuildSpec(append_path,        '--specpath',       LOG_REL_DIR,                   None),    # 4
    BuildSpec(append_path,        '--icon',           BuildConfig.ICON_PATH,         None),    # 5
    BuildSpec(configure_log_file, None,               LOG_REL_FILE,                  None),    # 6
    BuildSpec(append_flag,        '--onefile',        BuildConfig.ONEFILE,          'TRUE'),  # 7
    BuildSpec(append_flag,        '--windowed',       BuildConfig.WINDOW,           'FALSE'), # 8
    BuildSpec(append_flag,        '--clean',          BuildConfig.CLEAN,            'TRUE'),  # 9
    BuildSpec(append_flag,        '--noconfirm',      BuildConfig.CONFIRM,          'FALSE'), # 10
    BuildSpec(append_contents_directory, '--contents-directory', BuildConfig.CONTENTS_DIRECTORY, None), # 11
    BuildSpec(append_folders,     '--add-data',       BuildConfig.FOLDERS,           None),    # 12
    BuildSpec(append_files,       '--add-data',       BuildConfig.FILES,             None),    # 13
    BuildSpec(append_excludes,    '--exclude-module', BuildConfig.EXCLUDE,           None),    # 14
    BuildSpec(append_path,        '--version-file',   VERSION_CONFIG_FILE,           None),    # 15
]