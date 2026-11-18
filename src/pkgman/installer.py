import os
import base64
import requests
import hashlib
import contextlib
import zipfile
import shutil
from pathlib import Path
from tempfile import gettempdir
from typing import Callable
from .package import Package
from .logprint import LogPrintMixin


class PackageInstallError(Exception): ...
class PackageDownloadError(Exception): ...
class PackageChecksumError(Exception): ...
class PackageCancelledError(Exception): ...

class PackageInstaller(LogPrintMixin):
    def __init__(self,
                 staging_dir: str = None,
                 logger=None,
                 printer=print,
                 username: str = None,
                 password: str = None,
                 api_key: str = None,
                 timeout: int = 60,
                 max_size_mb: int = 500):
        super().__init__(logger, printer)
        self._staging_dir = Path(staging_dir) if staging_dir else Path(gettempdir()) / "pkg_staging"
        self._staging_dir.mkdir(parents=True, exist_ok=True)
        self._username = username
        self._password = password
        self._api_key = api_key
        self._timeout = timeout
        self._max_size_bytes = max_size_mb * 1024 * 1024

    def set_logger(self, logger):
        super().set_logger(logger)
    
    @property
    def staging_dir(self) -> str:
        return str(self._staging_dir)

    def _auth_headers(self, override_token: str | None) -> dict:
        if override_token:
            return {"Authorization": f"Bearer {override_token}"}
        if self._api_key and not self._username:
            return {"Authorization": f"Bearer {self._api_key}"}
        if self._username and self._api_key:
            basic = base64.b64encode(f"{self._username}:{self._api_key}".encode()).decode()
            return {"Authorization": f"Basic {basic}"}
        return {}

    def _http_get(self, url: str, token: str | None):
        headers = self._auth_headers(token)
        auth = None
        if self._username and self._password and not token and not self._api_key:
            auth = (self._username, self._password)
        return requests.get(url, headers=headers, auth=auth, stream=True, timeout=self._timeout)

    def _sha256(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def download(self,
                 package: Package,
                 dest_dir: str,
                 download_token: str | None = None,
                 progress_callback: Callable[[int], None] | None = None,
                 is_cancelled: Callable[[], bool] | None = None) -> str:
        if not isinstance(package, Package):
            raise PackageDownloadError("Invalid package object")

        if download_token is None and hasattr(package, "download_token"):
            download_token = getattr(package, "download_token")

        filename = os.path.basename(str(package.path))
        dest_file = os.path.join(dest_dir, filename)
        Path(dest_dir).mkdir(parents=True, exist_ok=True)

        self.log(f"Downloading package: {package.name}-{package.version}")
        try:
            if str(package.path).startswith(("http://", "https://")):
                resp = self._http_get(package.path, download_token)
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", "0") or 0)
                if total and total > self._max_size_bytes:
                    raise PackageDownloadError(f"File too large (> {self._max_size_bytes/1024/1024:.1f} MB)")
                downloaded = 0
                with open(dest_file, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if is_cancelled and is_cancelled():
                            self.log("Download cancelled; cleaning partial file.")
                            with contextlib.suppress(Exception):
                                f.close()
                                if Path(dest_file).exists():
                                    Path(dest_file).unlink()
                            raise PackageCancelledError("download cancelled")
                        if not chunk:
                            continue
                        f.write(chunk)
                        if total:
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(min(int(downloaded * 100 / total), 100))
                if progress_callback and not total:
                    progress_callback(100)
            else:
                # local path copy
                if is_cancelled and is_cancelled():
                    raise PackageCancelledError("download cancelled")
                src_path = Path(package.path)
                if not src_path.exists():
                    raise PackageDownloadError(f"Source file not found: {src_path}")
                shutil.copy2(src_path, dest_file)
                if progress_callback:
                    progress_callback(100)

            checksum = getattr(package, "checksum", None)
            if checksum:
                if is_cancelled and is_cancelled():
                    raise PackageCancelledError("download cancelled")
                actual = self._sha256(dest_file).lower()
                expected = checksum.lower()
                if actual != expected:
                    self.log(f"Checksum mismatch (expected {expected}, got {actual})", exception=True)
                    with contextlib.suppress(Exception):
                        if Path(dest_file).exists():
                            Path(dest_file).unlink()
                    raise PackageChecksumError(f"Checksum mismatch for {filename}")
                self.log(f"Checksum verified: {actual}")
            else:
                self.log("No checksum provided; skipping verification.")

            self.log(f"Downloaded to: {dest_file}")
            return dest_file
        except (PackageChecksumError, PackageDownloadError):
            raise
        except PackageCancelledError:
            raise
        except Exception as e:
            self.log(f"Download failed: {e}", exception=True)
            raise PackageDownloadError(str(e)) from e

    def install(self,
                package: Package,
                install_dir: str,
                download_token: str | None = None,
                download_progress: Callable[[int], None] | None = None,
                install_progress: Callable[[int], None] | None = None,
                post_verify: bool = False,
                is_cancelled: Callable[[], bool] | None = None) -> str:
        archive = self.download(
            package,
            self._staging_dir,
            download_token,
            progress_callback=download_progress,
            is_cancelled=is_cancelled
        )

        install_path = os.path.join(install_dir, package.name)
        temp_path = install_path + ".tmp"
        try:
            if is_cancelled and is_cancelled():
                raise PackageCancelledError("install cancelled")
            self.log(f"Preparing install directory: {install_path}")
            # remove temp if exists
            if Path(temp_path).exists():
                if Path(temp_path).is_dir():
                    shutil.rmtree(temp_path, ignore_errors=True)
                else:
                    with contextlib.suppress(Exception):
                        Path(temp_path).unlink()
            Path(temp_path).mkdir(parents=True, exist_ok=True)

            self.log("Extracting...")
            if install_progress:
                install_progress(0)

            with zipfile.ZipFile(archive, "r") as zf:
                members = zf.infolist()
                total = len(members) or 1
                for i, m in enumerate(members, 1):
                    if is_cancelled and is_cancelled():
                        self.log("Extraction cancelled.")
                        raise PackageCancelledError("install cancelled")
                    zf.extract(m, temp_path)
                    if install_progress:
                        install_progress(min(int(i * 100 / total), 100))

            if is_cancelled and is_cancelled():
                raise PackageCancelledError("install cancelled")
            old_exists = Path(install_path).is_dir()
            self.log(
                f"Activating new package (version {package.version}): "
                f"{'replacing existing installation' if old_exists else 'fresh install'}"
            )
            if Path(install_path).exists():
                if Path(install_path).is_dir():
                    shutil.rmtree(install_path, ignore_errors=True)
                else:
                    with contextlib.suppress(Exception):
                        Path(install_path).unlink()
            parent = os.path.dirname(install_path)
            if parent:
                Path(parent).mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, install_path)
            if install_progress:
                install_progress(95)

            if is_cancelled and is_cancelled():
                raise PackageCancelledError("install cancelled")
            self.log(f"Cleanup: removing archive '{os.path.basename(archive)}'")
            with contextlib.suppress(Exception):
                if Path(archive).exists():
                    Path(archive).unlink()

            if post_verify:
                if is_cancelled and is_cancelled():
                    raise PackageCancelledError("install cancelled")
                agg = hashlib.sha256()
                for root, _, files in os.walk(install_path):
                    for f in files:
                        if is_cancelled and is_cancelled():
                            raise PackageCancelledError("install cancelled")
                        fp = os.path.join(root, f)
                        with open(fp, "rb") as fh:
                            for blk in iter(lambda: fh.read(1024 * 1024), b""):
                                agg.update(blk)
                self.log(f"Post-install aggregate hash: {agg.hexdigest()[:16]}")

            if install_progress:
                install_progress(100)
            self.log(f"Installed successfully: {install_path}")
            return install_path
        except PackageCancelledError:
            self.log("Install cancelled; cleaning staging.", exception=False)
            with contextlib.suppress(Exception):
                if Path(temp_path).exists():
                    if Path(temp_path).is_dir():
                        shutil.rmtree(temp_path, ignore_errors=True)
                    else:
                        Path(temp_path).unlink()
            with contextlib.suppress(Exception):
                if Path(archive).exists():
                    Path(archive).unlink()
            raise
        except Exception as e:
            self.log(f"Install failed: {e}", exception=True)
            with contextlib.suppress(Exception):
                if Path(temp_path).exists():
                    if Path(temp_path).is_dir():
                        shutil.rmtree(temp_path, ignore_errors=True)
                    else:
                        Path(temp_path).unlink()
            raise PackageInstallError(str(e)) from e