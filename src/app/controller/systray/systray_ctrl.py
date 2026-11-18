from src.utils.systray import SystemTray
from src.mvc.base_controller import BaseController

class SystrayCtrl(BaseController):
    def __init__(self):
        super().__init__()
        self._initialized = False
        self._systray = None

    def init(self):
        if self._initialized:
            return self

        self._app_config = self.model.config_model.app_config
        self._main_window_view = self.view.main_window_view

        if self._app_config.SYS_TRAY_ENABLED:
            self._systray = SystemTray()
            self._systray.set_tooltip(self._app_config.APP_DISPLAY_NAME)
            self._systray.set_icon(self._app_config.APP_ICON)
            self._systray.add_icon_action(
                SystemTray.IconActivateReason.TRIGGER,
                self._on_systray_activated
            )
            self._systray.start()

        self.bus_subscribe("systray:destroy", lambda _: self.destroy())
        self._initialized = True
        return self

    def _on_systray_activated(self):
        self._main_window_view.restore_and_focus_window()
    
    def destroy(self):
        if self._systray and self._systray.tray:
            self._systray.tray.setVisible(False)
            self._systray.tray.deleteLater()
            self._systray = None