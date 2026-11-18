"""Bus event descriptor — lives in the MVC layer so EventBus can import it.

Design mirrors PyQt/PySide Signal declaration: the payload type is an actual
Python ``type`` (or tuple of types), not a string.  The bus enforces the type
at emit-time, just like signals enforce argument types.

Usage::

    from src.mvc.event_def import EventDef

    class SignalEvents:
        IMPORTED          = EventDef('signals.imported',          list)
        VALIDATION_FAILED = EventDef('signals.validation_failed', str)
        NO_PAYLOAD_EVENT  = EventDef('something.happened',        type(None))

    # emit — validated:
    bus.emit(SignalEvents.IMPORTED, ['a', 'b'])       # OK
    bus.emit(SignalEvents.IMPORTED, 'not a list')     # → TypeError

    # subscribe — EventDef or plain string both work:
    bus.subscribe(SignalEvents.IMPORTED, handler)
    bus.subscribe('signals.imported',   handler)      # same channel
"""
from typing import NamedTuple, Any, Union

# A payload-type spec: one type or a tuple of types (for isinstance multi-match)
PayloadType = Union[type, tuple[type, ...]]


class EventDef(NamedTuple):
    """Strongly-typed bus event constant.

    Attributes
    ----------
    name:
        The string key used by the event bus (same as PyQt signal name).
    payload_type:
        The exact Python ``type`` (or tuple of types) that every payload
        passed to ``bus.emit(this_event, payload)`` must satisfy.
        Use ``type(None)`` for events that carry no data.
    """

    name:         str
    payload_type: PayloadType  # actual Python type — *not* a string

    # ------------------------------------------------------------------
    # String interop — EventDef is pass-through as a bus event key
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        """Return the bus key so EventDef can be used anywhere a str is expected."""
        return self.name

    # ------------------------------------------------------------------
    # Validation — called by EventBus.emit() before dispatching handlers
    # ------------------------------------------------------------------

    def validate(self, payload: Any) -> None:
        """Raise ``TypeError`` if *payload* is not an instance of ``payload_type``.

        Matches the semantics of a PyQt ``Signal(type)`` argument check.

        Examples::

            EventDef('e', list).validate(['a'])          # OK
            EventDef('e', list).validate('oops')         # TypeError
            EventDef('e', type(None)).validate(None)     # OK
            EventDef('e', (str, int)).validate(42)       # OK — union
        """
        if not isinstance(payload, self.payload_type):
            raise TypeError(
                f"Bus event '{self.name}': expected payload of type "
                f"'{self._label()}', got '{type(payload).__name__}'"
            )

    def _label(self) -> str:
        """Human-readable name of the expected payload type."""
        if isinstance(self.payload_type, tuple):
            return ' | '.join(t.__name__ for t in self.payload_type)
        return self.payload_type.__name__
