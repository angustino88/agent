from __future__ import annotations
import logging
from typing import Callable


class LogPrintMixin:
    """Mixin providing unified logging and console printing.

    Subclasses should call ``super().__init__(logger, printer)`` in their
    ``__init__``.
    """

    def __init__(
        self,
        logger: logging.Logger | None = None,
        printer: Callable[[str], None] | None = print,
    ) -> None:
        self._logger  = logger
        self._printer = printer

    def log(
        self,
        msg: str,
        *,
        exception: bool = False,
        log: bool = True,
        print_msg: bool = True,
    ) -> None:
        """Log and/or print *msg*."""
        if log and self._logger:
            if exception:
                self._logger.exception(msg)
            else:
                self._logger.info(msg)
        if print_msg and self._printer:
            self._printer(msg)

    def set_logger(self, logger: logging.Logger) -> None:
        """Set or replace the logger."""
        self._logger = logger

    def set_printer(self, printer: Callable[[str], None] | None) -> None:
        """Set or replace the printer function."""
        self._printer = printer
        self._printer = printer
