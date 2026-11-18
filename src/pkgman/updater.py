import shutil
import contextlib
import logging
import time
import inspect
from enum import Enum
from pathlib import Path
from dirsync import sync
from typing import Callable, Iterable, List, Optional
from .package import Package
from .logprint import LogPrintMixin
from .installer import PackageInstaller, PackageCancelledError


class UpdateStage(Enum):
    READY      = "ready"
    PREPARE    = "prepare"
    DOWNLOAD   = "download"
    INSTALL    = "install"
    BACKUP     = "backup"
    RETAIN     = "retain"
    APPLY      = "apply"
    CLEANUP    = "cleanup"
    FINALIZE   = "finalize"
    ERROR      = "error"
    CANCELLED  = "cancelled"

class PackageUpdater(LogPrintMixin):
    def __init__(
        self,
        installer: PackageInstaller,
        logger=None,
        printer=print,
        backup_limit: int | None = 5,
    ):
        super().__init__(logger, printer)
        self.installer = installer
        self.backup_limit = backup_limit
        self._current_stage: UpdateStage | None = None
        self._stage_last_pct: dict[UpdateStage, int] = {}
        self._started_at: float = 0.0
        if logger and hasattr(self.installer, "set_logger"):
            with contextlib.suppress(Exception):
                self.installer.set_logger(logger)

    _STAGE_BASE = {
        UpdateStage.PREPARE: 5,
        UpdateStage.DOWNLOAD: 15,
        UpdateStage.INSTALL: 55,
        UpdateStage.BACKUP: 60,
        UpdateStage.RETAIN: 65,
        UpdateStage.APPLY: 65,
        UpdateStage.CLEANUP: 96,
        UpdateStage.FINALIZE: 100,
        UpdateStage.ERROR: 100,
        UpdateStage.CANCELLED: 100,
    }

    def set_logger(self, logger):
        super().set_logger(logger)
        self.installer.set_logger(logger)

    def _emit(
        self,
        stage: UpdateStage,
        pct: int | None = None,
        update_progress: Callable[[int, str], None] | None = None
    ):
        """Emit stage progress + structured log entry (throttled)."""
        if pct is None:
            pct = self._STAGE_BASE.get(stage, 0)
        pct = max(0, min(100, pct))
        last = self._stage_last_pct.get(stage, -100)
        if stage != self._current_stage or pct - last >= 5 or pct in (0, 100):
            self._stage_last_pct[stage] = pct
            self.log(f"[update] stage={stage.value} pct={pct}")
        self._current_stage = stage
        if update_progress:
            update_progress(pct, stage.value)

    @staticmethod
    def _iter_backups(app_dir: str, app_name: str) -> List[Path]:
        p = Path(app_dir)
        pattern = f"{app_name}.bak"
        backups = []
        if not p.exists():
            return backups
        for entry in p.iterdir():
            if entry.is_file() and entry.name.startswith(pattern):
                backups.append(entry)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return backups

    def _enforce_backup_limit(self, app_dir: str, app_name: str):
        if self.backup_limit is None:
            return
        backups = self._iter_backups(app_dir, app_name)
        for extra in backups[self.backup_limit:]:
            with contextlib.suppress(Exception):
                extra.unlink()
                self.log(f"[backup] old backup removed: {extra.name}")

    @staticmethod
    def _next_backup_path(app_dir: str, app_name: str) -> Path:
        base = Path(app_dir) / f"{app_name}.bak"
        if not base.exists():
            return base
        i = 1
        while True:
            cand = Path(app_dir) / f"{app_name}.bak{i}"
            if not cand.exists():
                return cand
            i += 1

    def _retain(self, old_root: str, new_root: str, paths: Iterable[str]):
        retained_dirs = 0
        retained_files = 0
        for rel in paths:
            src = Path(old_root) / rel
            dst = Path(new_root) / rel
            try:
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src, dst)
                    retained_dirs += 1
                elif src.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    retained_files += 1
                else:
                    self.log(f"[retain] skipped: missing path={rel}")
            except Exception as e:
                self.log(f"[retain] error: path={rel}, error={e}", exception=True)
        self.log(f"[retain] completed: directories={retained_dirs}, files={retained_files}")

    def update(
        self,
        package: Package,
        app_name: str,
        app_dir: str,
        download_token: str | None = None,
        retain_paths: Optional[List[str]] = None,
        pre_check: Optional[Callable[[Package, str], bool]] = None,
        post_apply: Optional[Callable[[Package, str], None]] = None,
        download_progress: Optional[Callable[[int], None]] = None,
        install_progress: Optional[Callable[[int], None]] = None,
        update_progress: Optional[Callable[[int, str], None]] = None,
        dry_run: bool = False,
        verify_executable: bool = False,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> str:
        """
        Perform update.

        download_progress(pct) -> download of archive only
        install_progress(pct)  -> staging install (extract + internal steps)
        update_progress(pct, stage) -> high-level lifecycle stages
        verify_executable -> if True, require that <app_name>.exe already exists in app_dir
        """
        if not isinstance(package, Package):
            raise ValueError(f"Expected Package, got {type(package).__name__}")
        app_dir_path = Path(app_dir)
        if not app_dir_path.is_dir():
            raise FileNotFoundError(f"Application directory missing: {app_dir}")

        exe_required_path = app_dir_path / f"{app_name}.exe"
        if verify_executable and not exe_required_path.exists():
            raise FileNotFoundError(
                f"Verification failed: required executable '{exe_required_path.name}' "
                f"not found in '{app_dir_path}'. Update aborted."
            )

        retain_paths = retain_paths or []
        self._current_stage = None
        self._stage_last_pct.clear()
        self._started_at = time.time()

        self.log(f"[update] started: package={package.name}, version={package.version}, app_dir={app_dir}")
        self._emit(UpdateStage.PREPARE, update_progress=update_progress)

        def _check_cancel(point: str):
            if is_cancelled and is_cancelled():
                self.log(f"[cancel] user requested cancellation at {point}")
                raise PackageCancelledError(f"Cancelled at {point}")

        # Pre-check
        if pre_check:
            try:
                if pre_check(package, app_dir) is False:
                    self.log("[pre-check] aborted: update cancelled")
                    self._emit(UpdateStage.FINALIZE, update_progress=update_progress)
                    return app_dir
            except Exception as e:
                self.log(f"[pre-check] error: {e}", exception=True)
                self._emit(UpdateStage.ERROR, update_progress=update_progress)
                raise

        if dry_run:
            self.log("[update] dry-run: no staged install performed, no changes applied")
            self._emit(UpdateStage.FINALIZE, update_progress=update_progress)
            return app_dir

        # --- Download and Install with state callbacks ---
        try:
            _check_cancel("before_download_install")
            token = getattr(package, "download_token", None) or download_token
            install_sig = inspect.signature(self.installer.install)
            install_kwargs = dict(
                download_token=token,
            )
            if "logger" in install_sig.parameters:
                install_kwargs["logger"] = self.logger
            if "is_cancelled" in install_sig.parameters:
                install_kwargs["is_cancelled"] = is_cancelled

            def download_progress_wrapper(pct):
                if pct == 0:
                    self._emit(UpdateStage.DOWNLOAD, update_progress=update_progress)
                if download_progress:
                    download_progress(pct)

            def install_progress_wrapper(pct):
                if pct == 0:
                    self._emit(UpdateStage.INSTALL, update_progress=update_progress)
                if install_progress:
                    install_progress(pct)

            install_kwargs["download_progress"] = download_progress_wrapper
            install_kwargs["install_progress"] = install_progress_wrapper

            staged_root = self.installer.install(
                package,
                self.installer.staging_dir,
                **install_kwargs
            )
        except PackageCancelledError:
            self.log("[download/install] cancelled by user")
            self._emit(UpdateStage.CANCELLED, update_progress=update_progress)
            with contextlib.suppress(Exception):
                if 'staged_root' in locals() and staged_root:
                    shutil.rmtree(staged_root, ignore_errors=True)
            raise
        except Exception:
            self.log("[download/install] error", exception=True)
            self._emit(UpdateStage.ERROR, update_progress=update_progress)
            raise
        self.log(f"[install] completed: root={staged_root}")

        _check_cancel("after_install")

        # 2. Backup executable
        exe_path = app_dir_path / f"{app_name}.exe"
        self._emit(UpdateStage.BACKUP, update_progress=update_progress)
        _check_cancel("before_backup")
        if exe_path.exists():
            bak = self._next_backup_path(app_dir, app_name)
            try:
                exe_path.rename(bak)
                self.log(f"[backup] created: {bak.name}")
                self._enforce_backup_limit(app_dir, app_name)
            except Exception as e:
                self.log(f"[backup] error: {e}", exception=True)
        self.log(f"[backup] completed: executable_present={'yes' if exe_path.exists() else 'no'}")

        _check_cancel("after_backup")

        # 3. Retain
        self._emit(UpdateStage.RETAIN, update_progress=update_progress)
        if retain_paths:
            _check_cancel("before_retain")
            self._retain(app_dir, staged_root, retain_paths)
        _check_cancel("after_retain")

        # 4. Apply (dirsync or swap)
        self.log(f"[apply] started: mode=dirsync, purge=True, src={staged_root}, dest={app_dir_path}")
        self._emit(UpdateStage.APPLY, pct=65, update_progress=update_progress)
        _check_cancel("before_apply")
        try:
            sync(
                staged_root,
                str(app_dir_path),
                'sync',
                purge=True,
                content=True,
                logger=logging.getLogger('null')
            )
            self._emit(UpdateStage.APPLY, pct=90, update_progress=update_progress)
            self.log("[apply] completed: directory synchronized")
        except PackageCancelledError:
            self.log("[apply] cancelled", exception=False)
            self._emit(UpdateStage.CANCELLED, update_progress=update_progress)
            raise
        except Exception:
            self.log("[apply] error", exception=True)
            self._emit(UpdateStage.ERROR, update_progress=update_progress)
            raise

        _check_cancel("after_apply")

        # 5. Cleanup
        self._emit(UpdateStage.CLEANUP, update_progress=update_progress)
        _check_cancel("before_cleanup")
        with contextlib.suppress(Exception):
            shutil.rmtree(staged_root, ignore_errors=True)
        self.log("[cleanup] completed: staged directory removed")

        _check_cancel("after_cleanup")

        # 6. Post-apply
        if post_apply:
            try:
                _check_cancel("before_post_apply")
                post_apply(package, app_dir)
            except PackageCancelledError:
                self.log("[post-apply] cancelled", exception=False)
                self._emit(UpdateStage.CANCELLED, update_progress=update_progress)
                raise
            except Exception as e:
                self.log(f"[post-apply] hook error (ignored): {e}", exception=True)

        duration = time.time() - self._started_at
        _check_cancel("before_finalize")
        self._emit(UpdateStage.FINALIZE, update_progress=update_progress)
        self.log(f"[update] completed: version={package.version}, duration={duration:.2f}s, app_dir={app_dir}")
        return app_dir