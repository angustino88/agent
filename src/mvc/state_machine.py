from __future__ import annotations
from typing import Any, Callable


class StateMachine:
    """Lightweight FSM for sub-models with complex mode transitions.

    Define states and allowed transitions up-front, then call ``transition()``
    to move between them.  ``on_enter`` / ``on_exit`` hooks fire automatically.
    Guards can reject a transition without raising.  History of visited states
    is available via ``history``.

    Usage inside a ``BaseModel.init()``::

        self._sm = StateMachine(initial="idle")
        self._sm.add_transition("idle",       "installing", on_enter=self._start_install)
        self._sm.add_transition("installing", "idle",       on_enter=self._finish)
        self._sm.add_transition("installing", "cancelling", on_enter=self._begin_cancel)
        self._sm.add_transition("cancelling", "idle")
    """

    def __init__(self, initial: str, *, track_history: bool = False) -> None:
        self._initial = initial
        self._state   = initial
        self._table   : dict[tuple[str, str], dict] = {}
        self._history : list[str] = [initial] if track_history else []
        self._track   = track_history

    # ---- definition ---------------------------------------------------------

    def add_transition(
        self,
        from_state : str,
        to_state   : str,
        *,
        guard      : Callable[[], bool] | None = None,
        on_exit    : Callable[[], None] | None = None,
        on_enter   : Callable[[], None] | None = None,
    ) -> None:
        """Register an allowed transition and optional callbacks.

        *guard* — zero-arg callable; if it returns ``False`` the transition is
        silently blocked.  *on_exit* fires just before leaving *from_state*;
        *on_enter* fires just after entering *to_state*.
        """
        self._table[(from_state, to_state)] = {
            "guard"   : guard,
            "on_exit" : on_exit,
            "on_enter": on_enter,
        }

    # ---- runtime ------------------------------------------------------------

    @property
    def state(self) -> str:
        """Current state name."""
        return self._state

    @property
    def history(self) -> list[str]:
        """Ordered list of states visited (only populated when ``track_history=True``)."""
        return list(self._history)

    def valid_transitions(self) -> list[str]:
        """Return all target states reachable from the current state (guards not checked)."""
        return [to for (frm, to) in self._table if frm == self._state]

    def reset(self) -> None:
        """Reset to the initial state without firing any callbacks or guards."""
        self._state = self._initial
        if self._track:
            self._history.clear()
            self._history.append(self._initial)

    def can_transition(self, to_state: str) -> bool:
        """Return ``True`` if moving to *to_state* is allowed right now."""
        edge = self._table.get((self._state, to_state))
        if edge is None:
            return False
        guard = edge["guard"]
        return guard() if guard else True

    def transition(self, to_state: str) -> bool:
        """Attempt to move to *to_state*.  Returns ``True`` on success.

        Raises ``ValueError`` if the transition is not defined.  Returns
        ``False`` (without raising) when the guard rejects the transition.
        """
        key = (self._state, to_state)
        if key not in self._table:
            raise ValueError(
                f"No transition defined from {self._state!r} to {to_state!r}"
            )
        edge = self._table[key]
        guard = edge["guard"]
        if guard and not guard():
            return False

        on_exit  = edge["on_exit"]
        on_enter = edge["on_enter"]

        if on_exit:
            on_exit()
        self._state = to_state
        if self._track:
            self._history.append(to_state)
        if on_enter:
            on_enter()
        return True

    def __repr__(self) -> str:
        return f"<StateMachine state={self._state!r}>"
