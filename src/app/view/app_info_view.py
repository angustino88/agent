from datetime import datetime
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDialog, QSizePolicy
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.AppInfoGui import Ui_AppInfoDialog

_TEXT_MUTED = "#94a3b8"
_FS         = "10pt"
_FS_S       = "9pt"


@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class AppInfoView(QDialog, BaseView, metaclass=metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_AppInfoDialog()
        self.ui.setupUi(self)
        self._app_config = None

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._ui_init()

    def _ui_init(self):
        for lbl in (self.ui.body_info_label,):
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        self.ui.close_btn.clicked.connect(self.close)
        self.ui.name_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.ui.version_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        name_font = QFont(self.ui.name_label.font())
        name_font.setBold(True)
        name_font.setPointSize(max(name_font.pointSize(), 14))
        self.ui.name_label.setFont(name_font)

        self.ui.name_label.setText(str(self._app_config.APP_DISPLAY_NAME))
        self.ui.version_label.setText(f"Version {self._app_config.APP_VERSION}")

        build_mode = "Development" if getattr(self._app_config, "IS_DEVELOPMENT", False) else "Production"
        year = datetime.now().strftime("%Y")
        self.ui.body_info_label.setText(self._build_table([
            ("Developer", "Huynh Thai An"),
            ("Build",     build_mode),
            ("Copyright", f"&copy; {year} &nbsp; All rights reserved."),
        ], fs=_FS_S))

    @staticmethod
    def _build_table(rows: list[tuple[str, str]], fs: str = _FS) -> str:
        """Render a two-column label / value HTML table."""
        tds = "".join(
            f"<tr>"
            f"<td align='right' width='120'"
            f" style='color:{_TEXT_MUTED}; font-size:{fs}; padding:4px 18px 4px 0;"
            f" white-space:nowrap; vertical-align:top;'>{k}</td>"
            f"<td style='font-size:{fs}; padding:4px 0; vertical-align:top;'>{v}</td>"
            f"</tr>"
            for k, v in rows
        )
        return f"<table cellspacing='0' cellpadding='0'>{tds}</table>"
