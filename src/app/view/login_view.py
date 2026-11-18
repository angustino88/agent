import keyboard
import qdarktheme
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QApplication
from src.utils.metaclass import metaclass_factory
from src.mvc.base_view import BaseView
from src.mvc.event_logger import log_events
from src.app.view.widgets.BlankWindowGui import Ui_BlankDialog
from src.app.view.widgets.LoginGui import Ui_LoginDialog
from time import monotonic

class BlankWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_BlankDialog()
        self.ui.setupUi(self)

    def show_screen(self, screen):
        self.move(screen.geometry().center())
        self.showFullScreen()

    def close_screen(self):
        self.close()


@log_events('showEvent', 'closeEvent', logger_name='view.logger')
class LoginView(QDialog, BaseView, metaclass = metaclass_factory(QDialog, BaseView)):
    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginDialog()
        self.ui.setupUi(self)
        self._hotkey_disabled = False
        self._blank_screens = []
        # secret pattern: double-click → long-press (>=600ms) within 2.5s window
        self._pattern_state = 0
        self._press_start_time = None
        self._pattern_timer = QTimer(self)
        self._pattern_timer.setSingleShot(True)
        self._pattern_timer.setInterval(2500)
        self._pattern_timer.timeout.connect(self._reset_secret_pattern)
        self.ui.icon_btn.clicked.connect(self._on_icon_btn_clicked)
        self.ui.icon_btn.pressed.connect(self._on_icon_btn_pressed)
        self.ui.icon_btn.released.connect(self._on_icon_btn_released)

    def init(self):
        self._app_config = self.model.config_model.app_config
        self._app_config_dynamic = self.model.config_model.app_config_dynamic
        self._logger = self.model.logging_model.system_logger
        self._ui_init()

    def _ui_init(self):
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.ui.icon_btn.setEnabled(True)
        self.ui.icon_btn.setFocusPolicy(Qt.NoFocus)
        self.ui.icon_btn.setStyleSheet("""
            QPushButton { border: none; background-color: transparent; }
            QPushButton:hover { background-color: transparent; }
            QPushButton:pressed { background-color: transparent; }
        """)

    def _disable_hotkey(self, disabled):
        if self._app_config_dynamic.app_debug_enabled:
            return

        if disabled:
            keyboard.block_key('esc')
            keyboard.block_key('alt')
            keyboard.block_key('windows')
            self._hotkey_disabled = True
        else:
            if self._hotkey_disabled:
                keyboard.unblock_key('esc')
                keyboard.unblock_key('alt')
                keyboard.unblock_key('windows')
                self._hotkey_disabled = False

    def _suspend_all_windows(self):
        """Temporarily hide all application windows and dialogs (non-destructive)."""
        for widget in QApplication.topLevelWidgets():
            try:
                # Skip already hidden ones
                if not widget.isVisible():
                    continue

                # Hide modal dialogs (opened via exec)
                if isinstance(widget, QDialog):
                    widget.hide()  # temporarily hide; keep loop running for later resume
                    continue

                # Hide normal windows
                widget.hide()
            except Exception as e:
                self._logger.exception(f"Failed to suspend {widget}: {e}")

    def show_screen(self):
        self._suspend_all_windows()
        qdarktheme.setup_theme('dark')
        self._disable_hotkey(True)
        self.clear_login_input()
        screens = QApplication.screens()
        self.move(screens[0].geometry().center())
        self.ui.widget.move(QApplication.primaryScreen().availableGeometry().center() - self.ui.widget.rect().center())
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

        # Fill additional screens with blank windows
        if len(screens) > 1:
            for idx, screen in enumerate(screens[1:]):
                blank = BlankWindow()
                blank.show_screen(screen)
                self._blank_screens.append(blank)

    def close_screen(self):
        qdarktheme.setup_theme('light')
        self._disable_hotkey(False)
        self.close()

        #close blank screen if any
        for blank_screen in self._blank_screens:
            blank_screen.close_screen()
        self._blank_screens.clear()

    def get_login_input(self):
        return self.ui.login_input_edit.text().strip()

    def clear_login_input(self):
        self.ui.login_input_edit.setText('')

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return:
            self.ui.login_btn.click()
        else:
            event.ignore()

    def _on_icon_btn_clicked(self):
        if self._pattern_state == 0:
            self._pattern_state = 1
            self._pattern_timer.start()
            return
        if self._pattern_state == 1:
            self._pattern_state = 2
            self._pattern_timer.start()
            return
        self._reset_secret_pattern()

    def _on_icon_btn_pressed(self):
        if self._pattern_state == 2:
            self._press_start_time = monotonic()
            self._pattern_timer.start()

    def _on_icon_btn_released(self):
        if self._press_start_time is None:
            return
        held = monotonic() - self._press_start_time
        self._press_start_time = None
        if self._pattern_state == 2 and held >= 0.6:
            self._reset_secret_pattern()
            self.close_screen()
        else:
            self._reset_secret_pattern()

    def _reset_secret_pattern(self):
        self._pattern_state = 0
        self._press_start_time = None
        try:
            self._pattern_timer.stop()
        except Exception:
            pass