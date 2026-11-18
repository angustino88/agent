"""
Create an annotated git tag for the current application version.

Tag format: v<APP_VERSION>  (e.g. v2.5.0)

The tag is created locally only. Push it manually when ready:
  git push origin v<version>
"""
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT_DIR = Path(__file__).resolve().parents[3]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from prj.config.version.version_config import VersionConfig
import report


def main() -> int:
    version = VersionConfig.APP_VERSION
    tag = f'v{version}'

    if not shutil.which('git'):
        report.warn('git not found in PATH. Skipping tag creation.')
        return 0

    cwd = str(_ROOT_DIR)

    # Check if tag already exists locally
    try:
        existing = subprocess.check_output(
            ['git', 'tag', '--list', tag], cwd=cwd, stderr=subprocess.DEVNULL
        ).decode().strip()
        if existing:
            report.info(f'Git tag {tag} already exists. Skipping.')
            return 0
    except subprocess.CalledProcessError:
        pass

    # Create annotated tag
    try:
        subprocess.check_call(
            ['git', 'tag', '-a', tag, '-m', f'Release {version}'],
            cwd=cwd,
        )
        report.ok(f'Created git tag: {tag}')
        report.hint(f'Push when ready: git push origin {tag}')
        return 0
    except subprocess.CalledProcessError as e:
        report.fail(f'Failed to create git tag {tag}: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())
