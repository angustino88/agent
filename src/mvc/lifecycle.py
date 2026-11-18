from enum import Enum, auto
from typing import Callable
import logging

_log = logging.getLogger(__name__)


class State(Enum):
    CREATED     = auto()
    INITIALIZED = auto()
    RUNNING     = auto()
    STOPPED     = auto()
    ERROR       = auto()


class Lifecycle:
    """Mixin that adds explicit state management to any MVC component."""
    def __init__(self) -> None:
        self._state   = State.CREATED
        self._on_state_change: list[Callable[[State], None]] = []

    @property
    def state(self) -> State:
        return self._state

    def on_state_change(self, handler: Callable[[State], None]) -> None:
        """Register a callback invoked with the new ``State`` on each transition."""
        self._on_state_change.append(handler)

    def _transition(self, new_state: State) -> None:
        """Move to *new_state* and notify all registered state-change listeners.

        No-op if *new_state* equals the current state.  Listener exceptions are
        caught and logged so one bad callback cannot block the others.
        """
        if new_state is self._state:
            return
        self._state = new_state
        for handler in self._on_state_change:
            try:
                handler(new_state)
            except Exception:
                _log.exception("Lifecycle callback %r raised", handler)

    # ---- convenience predicates --------------------------------------------

    def is_created(self) -> bool:
        """Return ``True`` if the component has not yet been initialized."""
        return self._state == State.CREATED

    def is_initialized(self) -> bool:
        """Return ``True`` if the component has been initialized but not started."""
        return self._state == State.INITIALIZED

    def is_running(self) -> bool:
        """Return ``True`` if the current state is ``RUNNING``."""
        return self._state == State.RUNNING

    def is_stopped(self) -> bool:
        """Return ``True`` if the component has been stopped."""
        return self._state == State.STOPPED

    def is_error(self) -> bool:
        """Return ``True`` if the component is in the ``ERROR`` state."""
        return self._state == State.ERROR