import os
import sys
from pathlib import Path

def get_app_root() -> Path:
    """
    Returns the directory where the application is installed or running from.
    Works for:
    - Development (Python script)
    - Packaged EXE (PyInstaller)
    - Any working directory
    """
    if getattr(sys, 'frozen', False):
        # When bundled (PyInstaller EXE)
        return Path(sys.executable).parent
    else:
        # When running from source
        return Path(__file__).resolve().parent.parent

APP_ROOT = get_app_root()
sys.path.insert(0, str(APP_ROOT))
os.environ["LABMANGO_ROOT"] = str(APP_ROOT)

def attach_parent_console() -> None:
    """The packaged app is a windowed executable without a console. When it is started from a
    terminal for a command-line sub-command, attach to that terminal so output and prompts show."""
    if os.name != "nt" or sys.stdout is not None:
        return
    import ctypes
    ATTACH_PARENT_PROCESS = -1
    if ctypes.windll.kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", buffering=1)
        sys.stdin = open("CONIN$", "r", encoding="utf-8")


# Command line sub-commands (`LabMango enroll|status|unenroll ...`) run without starting Qt.
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] in ("enroll", "status", "unenroll"):
    attach_parent_console()
    from src.agent_cli import main as agent_cli_main
    sys.exit(agent_cli_main(sys.argv[1:]))

from PySide6.QtWidgets import QApplication

from src.mvc.router import Router
from src.app.view.main_view import MainView
from src.app.model.main_model import MainModel
from src.app.controller.main_controller import MainController
from src.utils.single_instance import SingleInstance, InstanceScope
from prj.config.builder.build_config import BuildConfig

class LabMangoApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        route_name = BuildConfig.APP_NAME
        self.router = Router()
        self.router.register(route_name, MainModel, MainView, MainController)
        self.controller = self.router.resolve(route_name)
        self.controller.view.main_window_view.show()

if __name__ == '__main__':
        single_instance = "--skip-instance-check" not in sys.argv
        instance_guard = SingleInstance(BuildConfig.APP_NAME, scope=InstanceScope.PER_USER)
        instance_guard.acquire_or_exit(enable=single_instance, exit_code=0)
        app = LabMangoApp(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        app.exec()
