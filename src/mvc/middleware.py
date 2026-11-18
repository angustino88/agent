from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Any, Callable
from .command import Command


class Middleware(metaclass=ABCMeta):
    """Intercept every command passing through ``BaseMainModel.execute()``.

    Implement ``before()`` to inspect or block commands before execution and
    ``after()`` to react to results or errors afterward.  Return ``False``
    from ``before()`` to abort execution without raising an exception.

    Middleware is ordered; earlier-registered middleware wraps outer layers.
    Register instances via ``BaseMainModel.add_middleware()``.
    """

    def before(self, cmd: Command) -> bool:
        """Called before ``cmd.execute()``.  Return ``False`` to abort."""
        return True

    def after(self, cmd: Command, result: Any, error: Exception | None) -> None:
        """Called after ``cmd.execute()`` regardless of success or failure."""


class LoggingMiddleware(Middleware):
    """Log every command dispatch to a callable sink (e.g. ``logging.info``)."""

    def __init__(self, sink: Callable[[str], None] | None = None) -> None:
        import logging as _logging
        self._sink = sink or _logging.getLogger(__name__).info

    def before(self, cmd: Command) -> bool:
        name = type(cmd).__name__
        desc = f" — {cmd.description}" if getattr(cmd, "description", "") else ""
        self._sink(f"[CMD] execute  {name}{desc}")
        return True

    def after(self, cmd: Command, result: Any, error: Exception | None) -> None:
        name = type(cmd).__name__
        if error:
            self._sink(f"[CMD] error    {name}: {error}")
        else:
            self._sink(f"[CMD] done     {name}")


class MiddlewarePipeline:
    """Ordered chain of ``Middleware`` objects applied to every command.

    ``run(cmd, execute_fn)`` calls each middleware's ``before()`` in order,
    then calls *execute_fn*, then calls each ``after()`` in reverse order.
    If any ``before()`` returns ``False`` the command is skipped and ``None``
    is returned.
    """

    def __init__(self) -> None:
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> None:
        """Append *middleware* to the end of the pipeline."""
        self._middlewares.append(middleware)

    def remove(self, middleware: Middleware) -> None:
        """Remove *middleware* from the pipeline if present."""
        try:
            self._middlewares.remove(middleware)
        except ValueError:
            pass

    def run(self, cmd: Command, execute_fn: Callable[[], Any]) -> Any:
        """Run *execute_fn* through the full middleware chain."""
        passed: list[Middleware] = []
        for mw in self._middlewares:
            if not mw.before(cmd):
                # aborted — still call after() for those that ran before()
                error = RuntimeError(f"Command blocked by {type(mw).__name__}")
                for m in reversed(passed):
                    m.after(cmd, None, error)
                return None
            passed.append(mw)

        result, error = None, None
        try:
            result = execute_fn()
        except Exception as exc:
            error = exc

        for mw in reversed(passed):
            mw.after(cmd, result, error)

        if error:
            raise error
        return result
