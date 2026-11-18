"""Reusable one-shot background worker pair for controllers.

``WorkerThread`` runs a single callable in a Qt thread and emits
``succeeded`` or ``failed`` depending on the outcome.

``WorkerRelay`` lives on the main thread and delivers those results safely
to GUI-touching callbacks via Qt's queued connection mechanism.

Typical usage in a controller::

    def _run_worker(self, fn, on_done, on_fail) -> None:
        if self._relay is not None:
            self._relay.deleteLater()
        if self._worker is not None:
            self._worker.deleteLater()
        self._relay  = WorkerRelay(on_done, on_fail)
        self._worker = WorkerThread(fn)
        self._worker.succeeded.connect(self._relay.on_done)
        self._worker.failed.connect(self._relay.on_fail)
        self._worker.start()
"""
from PySide6.QtCore import QObject, Signal, Slot
from .base_thread import BaseThread, EHandle


class WorkerThread(BaseThread):
    """One-shot background thread that runs a callable and reports the result.

    Emits ``succeeded`` when the callable returns normally, or ``failed``
    (carrying the exception) when it raises.  Uses ``EHandle.IGNORE`` so
    ``BaseThread``'s own exception handler does not also fire — all routing
    goes through the two explicit signals.

    Named ``succeeded`` rather than ``finished`` to avoid shadowing
    ``QThread.finished``, which PySide6 emits automatically when ``run()``
    returns regardless of success or failure.
    """
    succeeded = Signal()
    failed    = Signal(object)   # carries Exception

    def __init__(self, fn):
        super().__init__(loop=False, e_handle=EHandle.IGNORE)
        self._fn = fn

    def run_user(self):
        try:
            self._fn()
            self.succeeded.emit()
        except Exception as exc:
            self.failed.emit(exc)


class WorkerRelay(QObject):
    """Delivers ``WorkerThread`` results to the main (GUI) thread.

    Because ``WorkerRelay`` is a ``QObject`` living on the main thread,
    Qt's auto-connection queues calls from the worker thread to these slots,
    making it safe to touch Qt widgets inside ``on_done`` / ``on_fail``.
    """

    def __init__(self, on_done, on_fail, parent=None):
        super().__init__(parent)
        self._on_done = on_done
        self._on_fail = on_fail

    @Slot()
    def on_done(self):
        self._on_done()

    @Slot(object)
    def on_fail(self, exc):
        self._on_fail(exc)
