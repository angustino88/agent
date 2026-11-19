from datetime import datetime
from PySide6.QtCore import Signal
from src.mvc.base_thread import BaseThread, EHandle

class HealthCheckThread(BaseThread):
    health_info = Signal(str)

    def __init__(self,
        backend_model,
        gateway_model,
        model_runner,
        view_runner,
        controller_runner
    ):
        super().__init__(loop=False, e_handle=EHandle.ONLY_E_CHANGE)
        self._backend_model = backend_model
        self._gateway_model = gateway_model
        self.runners = {
            "Model Tasks": model_runner,
            "View Tasks": view_runner,
            "Controller Tasks": controller_runner
        }
    
    def run_user(self):
        try:
            self.health_info.emit("=== Health Check Report ===")
            self.check_services()
            self.check_runners()
            self.health_info.emit("===========================")
        except Exception as e:
            self.exception.emit(e)

    def check_services(self):
        """Check front-end and back-end availability."""
        services = [
            ("Web app", self._backend_model.frontend_url, self._backend_model.check_frontend_alive),
            ("Backend", self._backend_model.backend_url or "(not enrolled)", self._backend_model.check_alive),
            ("Service gateway", self._gateway_model.url, self._gateway_model.check_alive),
        ]

        for name, url, alive_func in services:
            alive = "✅" if alive_func() else "❌"
            self.health_info.emit(f"{name}:")
            self.health_info.emit(f"  URL   : {url}")
            self.health_info.emit(f"  Alive : {alive}")
            self.health_info.emit("---------------------------")

    def check_runners(self):
        """Check all task runners."""
        for runner_name, runner in self.runners.items():
            self.health_info.emit(f"{runner_name}:")
            task_health = runner.check_task_health()

            if not task_health:
                self.health_info.emit("  No tasks found.")
                self.health_info.emit("---------------------------")
                continue

            for task_name, info in task_health.items():
                last_success = info.get("last_success")
                if last_success:
                    status = "✅ Active" if (datetime.now() - last_success).total_seconds() < 120 else "⚠️ Stopped"
                    last_success_str = last_success.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    status = "❌ Never ran"
                    last_success_str = "N/A"

                last_run_str = info.get("last_run").strftime("%Y-%m-%d %H:%M:%S") if info.get("last_run") else "N/A"
                last_success_str = last_success.strftime("%Y-%m-%d %H:%M:%S") if last_success else "N/A"

                # Next run
                next_run = info.get("next_run")
                next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "N/A"

                # Last error
                last_error = info.get("last_error")
                last_error_str = str(last_error) if last_error else "None"

                # Emit line
                self.health_info.emit(
                    f"{task_name}: {status}, last run: {last_run_str}, last success: {last_success_str}, "
                    f"next_run: {next_run_str}, last_error: {last_error_str}"
                )

            self.health_info.emit("---------------------------")