from enum import Enum
from PySide6.QtCore import QThread, Signal, QMutex, QWaitCondition

class EHandle(Enum):
    """
    Exception handling strategies for BaseThread:

    - IGNORE: Ignore all exceptions.
    - ALL: Emit all exceptions.
    - ONLY_E_CHANGE: Emit only if the exception message changes.
    """
    IGNORE = 1
    ALL = 2
    ONLY_E_CHANGE = 3


class BaseThread(QThread):
    """
    A robust QThread subclass with built-in loop control, pause/resume,
    exception handling, and signals for UI-safe messaging.
    """
    info = Signal(str)
    exception = Signal(Exception)

    def __init__(
        self,
        loop: bool = False,
        interval: float = 0,
        e_handle: EHandle = EHandle.ALL
    ):
        """
        Initialize the BaseThread.

        Args:
            loop (bool): Whether to repeatedly run `run_user()`.
            interval (float): Interval between executions in seconds (if looping).
            e_handle (EHandle): Exception handling strategy.
        """
        super().__init__()
        self._loop = loop
        self._interval = int(interval * 1000)  # Convert seconds to milliseconds
        self._e_handle = e_handle
        self._thread_kill = False
        self._thread_started = False
        self._last_exception = None

        # Pause/Resume support
        self._mutex = QMutex()
        self._pause_cond = QWaitCondition()
        self._thread_paused = False

    def kill(self) -> None:
        """
        Request the thread to stop.

        Note:
            The thread may take a short time to terminate if currently executing run_user().
        """
        self._thread_kill = True
        self.resume()  # Wake thread if paused

    def pause(self) -> None:
        """Pause the thread's execution."""
        self._thread_paused = True

    def resume(self) -> None:
        """
        Resume the thread's execution if paused.

        If the thread is currently paused, it will wake immediately.
        """
        if self._thread_paused:
            self._thread_paused = False
            self._mutex.lock()
            self._pause_cond.wakeAll()
            self._mutex.unlock()

    def has_started(self) -> bool:
        """Return True if the thread has started."""
        return self._thread_started

    def has_paused(self) -> bool:
        """Return True if the thread is currently paused."""
        return self._thread_paused

    def run_user(self) -> None:
        """
        Main logic for the thread
        """
        ...

    def e_handler(self, e: Exception) -> None:
        """
        Custom exception handler
        """
        ...

    def _e_handler(self, e: Exception) -> None:
        """
        Internal exception handler based on EHandle setting
        """
        if self._e_handle == EHandle.ALL:
            self.exception.emit(e)
            self.e_handler(e)
        elif self._e_handle == EHandle.ONLY_E_CHANGE:
            if str(e) != str(self._last_exception):
                self.exception.emit(e)
                self.e_handler(e)
                self._last_exception = e
 
    def run(self) -> None:
        """
        Main thread loop
        """
        self._thread_started = True
        try:
            while not self._thread_kill:
                # Handle pause
                self._mutex.lock()
                if self._thread_paused:
                    self._pause_cond.wait(self._mutex)
                self._mutex.unlock()

                # Execute user logic
                try:
                    self.run_user()
                except Exception as e:
                    self._e_handler(e)

                # Check for kill
                if self._thread_kill:
                    break

                # Stop if not looping
                if not self._loop:
                    break

                # Loop delay
                if self._interval > 0:
                    QThread.msleep(self._interval)
        finally:
            self._thread_started = False
