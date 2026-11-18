import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

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
