import sys
import json
import time
import requests
from pathlib import Path

import report


def get_version_from_meta(meta_path: str) -> str:
    """Extract version string from a JSON meta file."""
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return meta["version"]


def _check_version_not_deployed(version: str, index_path_str: str, force: bool) -> None:
    """Abort if this version already exists in index.json.

    Pass force=True (--force flag) to skip this check when intentionally
    re-deploying the same version.
    """
    if force:
        report.warn(f'--force flag set: skipping version check for {version}.')
        return
    # If no index path provided, skip the check.
    if not index_path_str:
        return

    index_path = Path(index_path_str)
    if not index_path.exists():
        return
    data = json.loads(index_path.read_text(encoding='utf-8'))
    deployed = [v['version'] for v in data.get('versions', [])]
    if version in deployed:
        report.fail(f'Version {version} is already deployed in index.json.')
        report.hint('To re-deploy the same version run with --force.')
        sys.exit(1)

def upload_file(file_path: str, repo: str, artifactory_url: str, token: str) -> tuple[bool, int]:
    """Uploads a file to the specified Artifactory repository with progress.

    Returns (success, size_bytes) instead of exiting, so callers can collect
    results for all artifacts and render a single summary at the end.
    """
    print()
    file = Path(file_path)

    if not file.is_file():
        report.fail(f'File not found: {file}')
        return False, 0

    upload_url = f"{artifactory_url.rstrip('/')}/{repo.strip('/')}/{file.name}"
    headers = {"Authorization": f"Bearer {token}"}

    report.info(f'Uploading {report.BOLD}{file.name}{report.RST}')
    report.hint(f'Target: {upload_url}')

    file_size = file.stat().st_size
    chunk_size = 1024 * 1024  # 1MB

    def file_stream():
        sent = 0
        with file.open("rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                sent += len(chunk)
                report.progress(sent, file_size)
                yield chunk
        report.progress(file_size, file_size)

    try:
        response = requests.put(upload_url, data=file_stream(), headers=headers, timeout=120)

        if response.status_code in (200, 201):
            report.ok(f'Uploaded {report.BOLD}{file.name}{report.RST}')
            return True, file_size
        else:
            report.fail(f'Upload failed ({response.status_code}): {response.text}')
            return False, file_size

    except requests.exceptions.RequestException as e:
        report.fail(f'Request failed: {e}')
        return False, file_size


def _print_deploy_summary(version: str, target: str, results: list, elapsed_s: float) -> None:
    """Print a styled summary box recapping every uploaded artifact."""
    print()
    report.box_top('DEPLOYMENT SUMMARY')
    report.box_blank()
    report.box_row('Version',  f'{report.GRN}{report.BOLD}{version}{report.RST}')
    report.box_row('Target',   target)
    report.box_row('Duration', report.format_duration(elapsed_s))
    report.box_blank()
    report.box_sep()
    report.box_blank()
    for r in results:
        icon = report.OK_IC if r['ok'] else report.FAIL_IC
        size = report.format_bytes(r['size']) if r['size'] else '—'
        report.box_row(r['label'], f"{icon}  {r['name']}  {report.DIM}({size}){report.RST}")
    report.box_blank()
    report.box_bot()
    print()

    if all(r['ok'] for r in results):
        report.ok('Deployment completed successfully.')
    else:
        report.fail('Deployment completed with errors.')
    print()


def main() -> None:
    """Main entry point."""
    force = '--force' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--force']

    if len(args) not in (6, 7, 8, 9):
        print(__doc__)
        sys.exit(1)

    artifactory_url, package_repo, meta_repo, token, package_path, meta_path = args[:6]
    index_path = args[6] if len(args) >= 7 else ''
    nuget_repo = args[7] if len(args) >= 8 else ''
    nuget_path = args[8] if len(args) >= 9 else ''

    # Validate token presence
    if not token or not token.strip():
        report.fail('ARTIFACTORY_TOKEN is empty or whitespace. Aborting.')
        sys.exit(1)

    # Version guard: block re-deploying an already-released version unless --force
    version = get_version_from_meta(meta_path)
    _check_version_not_deployed(version, index_path, force)

    meta_repo_with_version = f"{meta_repo.rstrip('/')}/{version}"

    print()
    report.box_top('ARTIFACTORY DEPLOYMENT')
    report.box_blank()
    report.box_row('Version',      f'{report.GRN}{report.BOLD}{version}{report.RST}')
    report.box_row('Target',       artifactory_url)
    report.box_row('Package repo', package_repo)
    report.box_row('Meta repo',    meta_repo)
    if nuget_repo.strip() and nuget_path.strip():
        report.box_row('NuGet repo', nuget_repo)
    report.box_blank()
    report.box_bot()

    start = time.time()
    results: list = []

    def _upload(label: str, path: str, repo: str) -> None:
        ok, size = upload_file(path, repo, artifactory_url, token)
        results.append({'label': label, 'name': Path(path).name, 'size': size, 'ok': ok})

    _upload('Package', package_path, package_repo)
    if index_path.strip():
        _upload('Index', index_path, meta_repo)
    _upload('Meta', meta_path, meta_repo_with_version)
    if nuget_repo.strip() and nuget_path.strip():
        _upload('NuGet', nuget_path, nuget_repo)

    _print_deploy_summary(version, artifactory_url, results, time.time() - start)

    if not all(r['ok'] for r in results):
        sys.exit(1)

if __name__ == "__main__":
    main()
