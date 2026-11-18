import os
import json
import hashlib
import subprocess
from datetime import datetime
from prj.config.server.server_config import ServerConfig
from prj.config.builder.build_config import BuildConfig
from prj.config.version.version_config import VersionConfig
import report


def _get_git_sha() -> str:
    """Return the short HEAD commit SHA, or 'unknown' if git is not available."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return 'unknown'

def get_file_size(file_path):
    return os.path.getsize(file_path)

def get_file_checksum(file_path, algorithm="sha256"):
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def build_meta_json(zip_path, output_path):
    base_url = (ServerConfig.BASE_PACKAGE_URL or '').strip()
    if not base_url:
        raise ValueError(
            'ServerConfig.BASE_PACKAGE_URL is not set. '
            'Update prj/config/server/server_config.py before building.'
        )
    size_bytes = get_file_size(zip_path)
    checksum_value = get_file_checksum(zip_path, BuildConfig.CHECKSUM_ALGO)
    zip_name = os.path.basename(zip_path)
    download_url = base_url.rstrip('/') + '/' + zip_name
    meta = {
        "name": BuildConfig.APP_NAME,
        "version": VersionConfig.APP_VERSION,
        "released_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_commit": _get_git_sha(),
        "download_url": download_url,
        "size_bytes": size_bytes,
        "checksum": {
            "algorithm": BuildConfig.CHECKSUM_ALGO,
            "value": checksum_value
        },
        "requires": VersionConfig.REQUIRES,
        "changelog": VersionConfig.CHANGELOG
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    report.ok(f'Meta JSON written to {output_path}')