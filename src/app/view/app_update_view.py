from PySide6.QtGui import QFont
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QDialog, QMessageBox
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.console import WidgetConsole
from src.mvc.event_logger import log_events
from src.app.view.widgets.AppUpdateGui import Ui_AppUpdateDialog
from src.pkgman.updater import UpdateStage

@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class AppUpdateView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    LOG_MAX_LINES = 2000

    log_message = Signal(str, bool)  # text, is_exception

    def __init__(self):
        super().__init__()
        self.ui = Ui_AppUpdateDialog()
        self.ui.setupUi(self)
        self._stage: UpdateStage | None = None
        self._app_config = None
        self._syslog = None
        self._console: WidgetConsole | None = None

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._syslog = self.model.logging_model.system_logger
        self._ui_init()
        self.set_stage(None)

    def get_stage(self) -> UpdateStage | None:
        return self._stage

    def set_stage(self, stage: UpdateStage | None):
        self._stage = stage
        if stage is None:
            upd_enabled = False
            cancel_enabled = False
        elif stage == UpdateStage.READY:
            upd_enabled = True
            cancel_enabled = False
        elif stage in (UpdateStage.DOWNLOAD, UpdateStage.INSTALL, UpdateStage.FINALIZE):
            upd_enabled = False
            cancel_enabled = True
        elif stage == UpdateStage.ERROR:
            upd_enabled = True
            cancel_enabled = True
        else:
            upd_enabled = False
            cancel_enabled = False

        self.ui.update_btn.setEnabled(upd_enabled)
        self.ui.cancel_btn.setEnabled(cancel_enabled)

    def update_stage(self, stage_str: str):
        try:
            stage = UpdateStage(stage_str)
        except Exception:
            return
        self.set_stage(stage)

    def _ui_init(self):
        font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.ui.console_output.setFont(font)
        self._console = WidgetConsole(
            self.ui.console_output,
            theme='light',
            formatter="[{timestamp}] [{level:<5}] {msg}")
        self.ui.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.ui.version_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        name_font = QFont(self.ui.name_label.font())
        name_font.setBold(True)
        name_font.setPointSize(max(name_font.pointSize(), 14))
        self.ui.name_label.setFont(name_font)

        self.ui.name_label.setText(self._app_config.APP_DISPLAY_NAME)
        self.update_version_label(self._app_config.APP_VERSION)

    def update_version_label(self, version: str):
        self.ui.version_label.setText(f'Version {version}')

    @property
    def console(self):
        return self._console
    
    def closeEvent(self, event):
        if self._stage == UpdateStage.FINALIZE:
            QMessageBox.information(self, 'Update', 'Finalizing update; cannot close.\nThe application will restart after finalization.')
            event.ignore()
        elif self._stage not in (None, UpdateStage.READY, UpdateStage.ERROR):
            QMessageBox.information(self, 'Update', 'Update in progress; cannot close.')
            event.ignore()
        else:
            event.accept()
            super().closeEvent(event)