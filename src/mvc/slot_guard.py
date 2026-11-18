from __future__ import annotations
import traceback
from functools import wraps
from PySide6.QtCore import Slot
from typing import Callable, List, Optional

def slot_guard(
    error_msg: Optional[str] = None,
    slot_args: Optional[List[type]] = None,
    on_exception: Optional[Callable] = None,
    logger: Optional[object] = None,
    reraise: bool = False
):
    """
    Decorator for PySide slot methods to catch and log exceptions.
    """
    slot_args = slot_args or []

    def log_exception(exc: Exception, context: str):
        message = f"{context}: {exc}" if context else str(exc)
        if logger and hasattr(logger, "exception"):
            logger.exception(message)
        elif logger and hasattr(logger, "error"):
            logger.error(message)
        else:
            print(f"[ERROR] {message}")
            traceback.print_exc()

    def decorator(func):
        @Slot(*slot_args)
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                log_exception(e, error_msg or func.__name__)
                if callable(on_exception):
                    try:
                        on_exception(self, e)
                    except Exception as handler_error:
                        log_exception(handler_error, "on_exception handler failed")
                if reraise:
                    raise
        return wrapper

    return decorator
