import os
import sys
import subprocess
import logging
import contextlib
from dataclasses import replace
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Signal, QMetaObject, Qt, QTimer, QObject, Slot

from src.mvc.base_controller import BaseController
from src.mvc.slot_guard import slot_guard
from src.mvc.task_schedule import task
from src.pkgman.installer import PackageInstaller
from src.pkgman.updater import PackageUpdater, UpdateStage
from src.app.model.update_checker import PackageUpdate
from src.app.model.config.task_schedule_config import TaskScheduleConfig
from src.app.controller.app_update.app_update_thread import UpdateCheckThread, UpdateRunThread

class ExitInvoker(QObject):
    @Slot()
    def do_exit(self):
        app = QApplication.instance()
        if not app:
            return
        for w in app.topLevelWidgets():
            try:
                w.close()
            except Exception:
                pass
        app.closeAllWindows()
        app.quit()

_exit_invoker = ExitInvoker()

class _AppUpdateSignals(QObject):
    restart_app = Signal(int)

class AppUpdateCtrl(BaseController):
    def __init__(self):
        super().__init__()

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._app_settings = self.model.config_model.app_settings
        self._logging_model = self.model.logging_model
        self._logger = self.model.logging_model.system_logger
        self._gateway_model = self.model.gateway_model
        self._message_box = self.view.message_box
        self._app_update_view = self.view.app_update_view
        self._app_update_view.ui.update_btn.clicked.connect(self.apply_update)
        self._app_update_view.ui.cancel_btn.clicked.connect(self.cancel_download_install)
        self.view.main_window_view.ui.check_update_action.triggered.connect(self.check_update)

        self._app_update_signals = _AppUpdateSignals()
        self._app_update_signals.restart_app.connect(self._restart_app)

        # Installer / updater
        self._installer = PackageInstaller()
        self._updater = PackageUpdater(installer=self._installer, backup_limit=3)

        # Pending update/meta
        self._pending_update_pkg = None
        self._pending_update_token = None
        self._last_pkg_update: PackageUpdate | None = None
        self._current_update_target_version: str | None = None

        # Threads
        self._update_thread: UpdateCheckThread | None = None
        self._update_run_thread: UpdateRunThread | None = None

        # Auto-update state
        self._auto_last_seen_version: str | None = None
        self._auto_last_applied_version: str | None = None
        self._auto_busy = False
        self._auto_applying = False

        # Flags
        self._cancel_requested = False
        self._session_finalized = False

        # Progress counters
        self._reset_manual_progress_state()

    # -------------- UI / Console Helpers --------------
    def _handle_exception(self, e):
        self._message_box.error(e, parent=self._app_update_view)

    def _console_emit(self, msg: str, level: str = "info", inline: bool = False, final: bool = False):
        level_map = {
            "debug": logging.DEBUG, "info": logging.INFO,
            "warn": logging.WARNING, "warning": logging.WARNING,
            "error": logging.ERROR, "critical": logging.CRITICAL
        }
        lvl = level_map.get(level.lower(), logging.INFO)
        self._app_update_view.console.log(msg, level=lvl, inline=inline, final=final)

    def _fmt_progress_line(self, label: str, pct: int, stage: str | None = None):
        # Format: | label      |  XX%   | stage=stage
        label_fmt = f"{label:<11}"
        pct_fmt = f"{pct:>3}%"
        if stage:
            return f"| {label_fmt} | {pct_fmt} | stage={stage}"
        else:
            return f"| {label_fmt} | {pct_fmt} |"

    # -------------- Summary Rendering --------------
    def _normalize_changelog(self, pkg_update: PackageUpdate):
        pkg = pkg_update.package
        raw = pkg_update.changelog or (pkg.changelog if pkg and hasattr(pkg, "changelog") else "") or ""
        if isinstance(raw, list):
            raw = "\n".join(str(x) for x in raw if x is not None)
        elif not isinstance(raw, str):
            with contextlib.suppress(Exception):
                raw = str(raw)
        raw = raw.strip() or "(no changelog provided)"
        max_len = 800
        truncated_len = len(raw) > max_len
        disp = raw[:max_len] + "... (truncated)" if truncated_len else raw
        lines_all = [line for line in disp.splitlines() if line.strip()] or ["(empty)"]
        max_lines = 12
        truncated_cl = len(lines_all) > max_lines
        return lines_all[:max_lines], (truncated_len or truncated_cl)

    def _build_update_summary(self, rows: list[tuple[str, str]], changelog_lines: list[str], truncated: bool) -> str:
        if not rows:
            return "=== Update Available ===\n(no details)"
        label_w = max(len(k) for k, _ in rows)
        def fmt(k, v): return f"{k:<{label_w}}: {v}"
        lines = ["=== Update Available ===", *(fmt(k, v) for k, v in rows)]
        widest = max(len(line) for line in lines[1:]) if len(lines) > 1 else len(lines[0])
        lines.append("-" * widest)
        lines.append("Changelog (preview):")
        lines.extend(changelog_lines)
        if truncated:
            lines.append("... (changelog truncated)")
        lines.append("=" * len(lines[0]))
        return "\n".join(lines)

    def _render_update_summary(self, pkg_update: PackageUpdate):
        current_version = self._app_config.APP_VERSION
        pkg = pkg_update.package
        rows = [
            ("Current",  current_version),
            ("New",      pkg_update.latest_version or (pkg.version if pkg else "?")),
            ("Type",     pkg_update.update_type or "-"),
            ("Size",     pkg_update.size_human or "-"),
            ("Released", pkg_update.released_at or "-"),
        ]
        lines, trunc = self._normalize_changelog(pkg_update)
        summary = self._build_update_summary(rows, lines, trunc)
        self._console_emit(summary, "info")
        self._console_emit("Call update action to proceed with installation.", "info")

    # -------------- Progress Callbacks --------------
    def _download_progress(self, p: int):
        if self._cancel_requested or p < 0 or p > 100 or p == self._last_dp:
            return
        self._last_dp = p
        line = self._fmt_progress_line("downloading", p)
        self._console_emit(line, "info", inline=(p < 100))

    def _install_progress(self, p: int):
        if self._cancel_requested or p < 0 or p > 100 or p <= self._last_ip:
            return
        self._last_ip = p
        line = self._fmt_progress_line("installing", p)
        self._console_emit(line, "info", inline=(p < 100))

    def _update_progress(self, p: int, stage: str):
        if not hasattr(self, "_last_stage_pct"):
            self._last_stage_pct = {}
        last_pct = self._last_stage_pct.get(stage)
        if last_pct == p:
            return
        self._last_stage_pct[stage] = p

        self._app_update_view.set_stage(UpdateStage(stage))
        line = self._fmt_progress_line("update", p, stage=stage)
        self._console_emit(line, "info")

    # -------------- Internal State Helpers --------------
    def _reset_manual_progress_state(self):
        self._last_dp = -1
        self._last_ip = -1
        self._last_up = -1
        self._download_final_logged = False
        self._install_final_logged = False
        self._last_stage_pct = {}
        if hasattr(self._app_update_view, "reset_progress"):
            with contextlib.suppress(Exception):
                self._app_update_view.reset_progress()

    # -------------- Update Check Thread Callbacks --------------
    def _on_update_thread_done(self, pkg_update: PackageUpdate):
        self._update_thread = None
        if not pkg_update or not pkg_update.has_update:
            self._console_emit(f"No update available. Current version: {self._app_config.APP_VERSION}", "info")
            self._app_update_view.set_stage(None)
            return
        self._pending_update_pkg = pkg_update.package
        self._pending_update_token = pkg_update.download_token
        self._last_pkg_update = pkg_update
        self._render_update_summary(pkg_update)
        self._app_update_view.set_stage(UpdateStage.READY)

    def _on_update_thread_exception(self, e: Exception):
        self._console_emit(f"Update check failed: {e}", "error")
        self._update_thread = None
        self._app_update_view.set_stage(None)

    def _restart_app(self, delay: int = 3):
        try:
            exe_path = sys.executable
            args = sys.argv[1:]

            if "--skip-instance-check" not in args:
                args.append("--skip-instance-check")
            quoted_exe = f'"{exe_path}"'
            quoted_args = " ".join(f'"{a}"' for a in args)

            cmd = (
                f'timeout /t {delay} >nul && '
                f'cd /d "{os.path.dirname(exe_path)}" && '
                f'start "" {quoted_exe} {quoted_args} >nul 2>&1'
            )
            subprocess.Popen(cmd, shell=True, close_fds=True)
            self.bus_emit("systray:destroy")
            QMetaObject.invokeMethod(_exit_invoker, "do_exit", Qt.QueuedConnection)

        except Exception as e:
            self._logger.exception("Failed to restart app", exc_info=e)

    # -------------- Public: Manual Check --------------
    @slot_guard(on_exception=_handle_exception)
    def check_update(self):
        self._app_update_view.show()
        if self._update_thread and self._update_thread.isRunning():
            self._console_emit("Update check already running...", "warn")
            return
        self._app_update_view.console.clear()
        self._app_update_view.set_stage(None)
        self._console_emit("Checking for updates...", "info")
        t = UpdateCheckThread(self._gateway_model, self._app_config.APP_VERSION, self._logger)
        self._update_thread = t
        t.done.connect(self._on_update_thread_done)
        t.exception.connect(self._on_update_thread_exception)
        t.start()

    # -------------- Public: Manual Apply --------------
    @slot_guard(on_exception=_handle_exception)
    def apply_update(self):
        if self._app_config.IS_DEVELOPMENT:
            self._console_emit("Update disabled in development mode.", "warning")
            return
        if not self._app_config.APP_UPDATE_ENABLED:
            self._console_emit("App updates are disabled.", "warning")
            return
        if self._auto_applying:
            self._console_emit("Automatic update is currently applying. Please wait until it completes.", "warn")
            return
        if not self._pending_update_pkg:
            self._console_emit("No pending update package.", "info")
            return
        if self._update_run_thread and self._update_run_thread.isRunning():
            self._console_emit("Update already running...", "warn")
            return

        # Fresh session
        self._reset_manual_progress_state()

        pkg = self._pending_update_pkg
        if (self._pending_update_token and hasattr(pkg, "download_token") and
                getattr(pkg, "download_token", None) != self._pending_update_token):
            with contextlib.suppress(TypeError):
                pkg = replace(pkg, download_token=self._pending_update_token)
                self._pending_update_pkg = pkg

        target_version = self._last_pkg_update.latest_version
        self._current_update_target_version = target_version
        self._cancel_requested = False
        self._session_finalized = False

        try:
            self._logging_model.begin_update_session(target_version)
            self._updater.set_logger(self._logging_model.update_logger)
        except Exception as e:
            self._console_emit(f"Failed to prepare update log: {e}", "warning")

        self._updater.set_logger(self._logging_model.update_logger)
        self._console_emit("Starting update in background...", "info")
        self._logger.info(f"Starting manual update for version {target_version}")
        t = UpdateRunThread(
            updater=self._updater,
            pkg=pkg,
            app_name=self._app_config.APP_NAME,
            app_dir=self._app_config.ROOT_DIR,
            download_token=self._pending_update_token,
            logger=self._logger
        )
        self._update_run_thread = t
        t.download_progress.connect(self._download_progress)
        t.install_progress.connect(self._install_progress)
        t.update_progress.connect(self._update_progress)
        t.finished.connect(self._on_update_run_thread_finished)

        def ok():
            if not self._session_finalized:
                self._logging_model.finalize_update_session(target_version, success=True)
                self._session_finalized = True
            self._console_emit("Update completed successfully.", "info")
            self._logger.info(f"Update completed successfully for version {target_version}")
            self._app_update_view.set_stage(None)
            self._console_emit("The application will restart to apply the update", "info")
            QTimer.singleShot(3000, self._restart_app)
            self._update_run_thread = None

        def fail(err: str):
            if not self._session_finalized:
                self._logging_model.finalize_update_session(target_version, success=False)
                self._session_finalized = True
            if self._cancel_requested:
                self._console_emit("Update cancelled.", "warning")
                self._logger.info("Update cancelled by user.")
            else:
                self._console_emit(f"Update failed: {err}", "error")
                self._logger.error(f"Update failed: {err}")
            self._update_run_thread = None
            self._app_update_view.set_stage(UpdateStage.ERROR if self._pending_update_pkg else None)

        t.success.connect(ok)
        t.failed.connect(fail)
        t.exception.connect(lambda e: fail(str(e)))
        self._app_update_view.set_stage(UpdateStage.PREPARE)
        t.start()

    # -------------- Public: Manual Cancel --------------
    @slot_guard(on_exception=_handle_exception)
    def cancel_download_install(self):
        t = self._update_run_thread
        if not t or not t.isRunning():
            self._console_emit("No active update to cancel.", "info")
            return
        downloading = self._last_dp < 100
        installing = self._last_ip < 100
        if not (downloading or installing):
            self._console_emit("Cannot cancel: update is applying changes.", "warn")
            return
        if self._cancel_requested:
            self._console_emit("Cancellation already requested...", "info")
            return
        self._cancel_requested = True
        self._console_emit("Cancelling update (download/install phase)...", "warn")
        if hasattr(t, "cancel"):
            with contextlib.suppress(Exception):
                t.cancel()
        elif hasattr(t, "requestInterruption"):
            with contextlib.suppress(Exception):
                t.requestInterruption()

    def cancel_update(self):
        """Alias for UI: cancel during download/install phases."""
        self.cancel_download_install()

    # -------------- Auto Update --------------
    @task(schedule=TaskScheduleConfig.AUTO_UPDATE, heavy=True)
    def auto_update(self):
        if not self._app_config.APP_UPDATE_ENABLED or self._app_config.IS_DEVELOPMENT:
            return
        if self._auto_busy or self._auto_applying:
            return
        if (self._update_thread and self._update_thread.isRunning()) or \
           (self._update_run_thread and self._update_run_thread.isRunning()):
            return

        self._auto_busy = True
        current_version = self._app_config.APP_VERSION
        try:
            try:
                pkg_update: PackageUpdate = self._gateway_model.check_package_update(current_version)
            except Exception as e:
                self._logger.debug(f"Auto-update check failed: {e}")
                return

            if not pkg_update or not pkg_update.has_update:
                self._auto_last_seen_version = None
                return

            pkg = pkg_update.package
            if not pkg:
                return

            new_version = pkg_update.latest_version or getattr(pkg, "version", None)
            if not new_version:
                return

            if self._auto_last_applied_version == new_version:
                return

            if self._auto_last_seen_version != new_version:
                self._auto_last_seen_version = new_version

            token = pkg_update.download_token
            if token and hasattr(pkg, "download_token") and getattr(pkg, "download_token", None) != token:
                with contextlib.suppress(TypeError):
                    pkg = replace(pkg, download_token=token)

            self._pending_update_pkg = pkg
            self._pending_update_token = token
            self._last_pkg_update = pkg_update
            self._app_update_view.set_stage(UpdateStage.READY)

            self._logger.info(f"Auto-update: applying {current_version} -> {new_version} ...")
            self._auto_applying = True

            try:
                self._logging_model.begin_update_session(new_version)
                self._updater.set_logger(self._logging_model.update_logger)
            except Exception as e:
                self._logger.warning(f"Auto-update: failed to init update log ({e})")

            success = False
            try:
                self._updater.update(
                    package=pkg,
                    app_name=self._app_config.APP_NAME,
                    app_dir=self._app_config.ROOT_DIR,
                    download_token=token,
                    download_progress=None,
                    install_progress=None,
                    update_progress=None,
                    verify_executable=True,
                )
                success = True
            except Exception as e:
                self._logger.exception(f"Auto-update failed for {new_version}: {e}")
            finally:
                self._logging_model.finalize_update_session(new_version, success=success)

            if success:
                self._auto_last_applied_version = new_version
                self._logger.info(f"Auto-update: successfully updated to {new_version}")
                self._app_update_view.update_version_label(new_version)
                self._app_update_view.set_stage(None)
                self._pending_update_pkg = None
                self._pending_update_token = None
                self._app_update_signals.restart_app.emit(3)
        finally:
            self._auto_applying = False
            self._auto_busy = False

    # -------------- Run Thread Finish Handler --------------
    def _on_update_run_thread_finished(self):
        # If success/fail handlers already cleared state, nothing to do
        if self._update_run_thread and self._update_run_thread.isRunning():
            return  # Should not happen, safety
        # Handle cancellation finalize
        if self._cancel_requested and not self._session_finalized:
            if self._current_update_target_version:
                with contextlib.suppress(Exception):
                    self._logging_model.finalize_update_session(
                        self._current_update_target_version, success=False
                    )
            self._session_finalized = True
            self._console_emit("Update cancelled before apply.", "warning")
            self._reset_manual_progress_state()
        # Fallback: unexpected silent termination (no success/fail)
        if (not self._cancel_requested) and (not self._session_finalized) and self._current_update_target_version:
            with contextlib.suppress(Exception):
                self._logging_model.finalize_update_session(
                    self._current_update_target_version, success=False
                )
            self._session_finalized = True
            self._console_emit("Update ended unexpectedly.", "error")
        self._update_run_thread = None
        self._cancel_requested = False
        # Re-enable button if still a pending package and update not successful
        if self._pending_update_pkg and not (self._session_finalized and not self._cancel_requested):
            self._app_update_view.set_stage(UpdateStage.ERROR)
        else:
            self._app_update_view.set_stage(None)