import logging
import inspect
import re
import traceback
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Qt, QEvent, QUrl
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor, QFont, QDesktopServices
from PySide6.QtWidgets import QPlainTextEdit, QMessageBox

# ============================================================
# Base logger
# ============================================================
class BaseLogger(QObject):
    _DEFAULT_FORMAT = "[{timestamp}] [{level}] [{module}.{func}:{line}] {msg}"

    def __init__(self, logger: logging.Logger = None, formatter: str = None):
        super().__init__()
        self._logger = logger or logging.getLogger(__name__)
        self._formatter = formatter or self._DEFAULT_FORMAT

    # -------- internals --------
    def _get_caller_info(self):
        frame = inspect.currentframe()
        while frame:
            cls = frame.f_locals.get("self", None).__class__ if "self" in frame.f_locals else None
            if cls not in (BaseLogger, WidgetConsole, MessageBoxConsole):
                break
            frame = frame.f_back
        module = frame.f_globals.get("__name__", "") if frame else ""
        func = frame.f_code.co_name if frame else ""
        line = frame.f_lineno if frame else 0
        return module, func, line

    def _format_message(self, msg: str, level: int) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        lvl = logging.getLevelName(level)
        module, func, line = self._get_caller_info()
        return self._formatter.format(
            timestamp=ts,
            level=lvl,
            module=module,
            func=func,
            line=line,
            msg=msg
        )

    def _log_to_python(self, msg: str, level: int, exception: bool | tuple | None):
        # Ensure the message is encodable by all attached logging handlers.
        s = str(msg)
        # Collect handlers from this logger and its parents (respect propagate)
        handlers = []
        logger = self._logger
        while logger is not None:
            handlers.extend(getattr(logger, 'handlers', []) or [])
            if not getattr(logger, 'propagate', True):
                break
            logger = getattr(logger, 'parent', None)

        for h in handlers:
            enc = getattr(h, 'encoding', None)
            if not enc:
                stream = getattr(h, 'stream', None)
                enc = getattr(stream, 'encoding', None) if stream is not None else None
            if not enc:
                continue
            try:
                s.encode(enc)
            except Exception:
                try:
                    s = s.encode(enc, errors='replace').decode(enc)
                except Exception:
                    # Last-resort fallback: strip to ASCII
                    s = s.encode('ascii', errors='replace').decode('ascii')

        self._logger.log(level, s, exc_info=exception)

    # API
    def log(self, msg: object, level: int = logging.INFO, exception: bool = False, **kwargs):
        raise NotImplementedError


# ============================================================
# Widget console with optional single-line inline updates
# ============================================================
class WidgetConsole(BaseLogger):
    """
    QPlainTextEdit log console.
    inline=True -> replaces a single live line (no newline growth).
    Any inline=False call commits the inline line (newline) first.
    """
    _log_signal = Signal(str, int, bool, bool, object, object, bool)  # formatted message, level, inline, final, color, segments, timestamp

    DARK_COLORS = {
        logging.DEBUG:    "#808080",
        logging.INFO:     "#E0E0E0",
        logging.WARNING:  "#FFA500",
        logging.ERROR:    "#FF5555",
        logging.CRITICAL: "#FF1493",
    }
    LIGHT_COLORS = {
        logging.DEBUG:    "#606060",
        logging.INFO:     "#202020",
        logging.WARNING:  "#C06000",
        logging.ERROR:    "#B00020",
        logging.CRITICAL: "#8B0045",
    }
    _URL_RE = re.compile(r"(?P<url>(?:https?://|www\.)[^\s<>()\[\]{}]+)")
    _LOCAL_PATH_RE = re.compile(
        r"(?P<path>(?:[A-Za-z]:[\\/]|\\\\[^\\/\s]+\\[^\\/\s]+|/)[^\s<>()\[\]{}]+)"
    )

    def __init__(self,
                 widget: QPlainTextEdit,
                 logger: logging.Logger = None,
                 formatter: str = None,
                 theme: str = "dark",
                 custom_colors: dict[int, str] | None = None):
        if not isinstance(widget, QPlainTextEdit):
            raise TypeError("widget must be a QPlainTextEdit")
        super().__init__(logger, formatter)
        self._widget = widget
        self._theme = theme.lower()
        palette = self.DARK_COLORS if self._theme == "dark" else self.LIGHT_COLORS
        if custom_colors:
            palette = {**palette, **custom_colors}
        self._colors = palette
        self._inline_active = False
        self._inline_level = logging.INFO
        self._viewport = self._widget.viewport()
        self._widget.setTextInteractionFlags(
            self._widget.textInteractionFlags()
            | Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._viewport.installEventFilter(self)
        self._log_signal.connect(self._dispatch_log)

    # -------- appearance --------
    def set_theme(self, theme: str):
        theme = theme.lower()
        if theme not in ("dark", "light"):
            return
        self._theme = theme
        self._colors = self.DARK_COLORS if theme == "dark" else self.LIGHT_COLORS

    def set_level_color(self, level: int, color: str):
        self._colors[level] = color

    def _resolve_color(self, level: int) -> QColor:
        return QColor(self._colors.get(level, self._colors.get(logging.INFO, "#E0E0E0")))

    def _resolve_message_color(self, level: int, color: object | None) -> QColor:
        if color is None:
            return self._resolve_color(level)
        if isinstance(color, QColor):
            return color
        return QColor(str(color))

    def _resolve_link_target(self, target: object) -> QUrl:
        if isinstance(target, QUrl):
            return target
        if isinstance(target, Path):
            return QUrl.fromLocalFile(str(target))

        text = str(target).strip()
        if not text:
            return QUrl()
        if text.startswith("www."):
            return QUrl(f"https://{text}")
        if text.startswith(("http://", "https://")):
            return QUrl(text)
        if re.match(r"^[A-Za-z]:[\\/]|^\\\\|^/", text):
            return QUrl.fromLocalFile(text)
        if Path(text).is_absolute():
            return QUrl.fromLocalFile(text)
        return QUrl(text)

    def _build_link_segments(self, text: str, default_color: QColor, bold: bool = False) -> list[tuple]:
        segments: list[tuple] = []
        last_end = 0
        for match in re.finditer(rf"{self._URL_RE.pattern}|{self._LOCAL_PATH_RE.pattern}", text):
            start, end = match.span()
            if start > last_end:
                segments.append((text[last_end:start], default_color, None, bold, None))
            link_text = match.group("url") or match.group("path")
            href = link_text
            segments.append((link_text, QColor("#2563eb"), None, bold, href))
            last_end = end
        if last_end < len(text):
            segments.append((text[last_end:], default_color, None, bold, None))
        return segments

    def _normalize_segment(self, segment: tuple, default_color: QColor) -> tuple:
        if len(segment) == 5:
            text, fg, bg, bold, href = segment
            return (str(text), fg, bg, bool(bold), href)
        if len(segment) == 4:
            text, fg, bg, bold = segment
            return (str(text), fg, bg, bool(bold), None)
        if len(segment) == 2:
            text, bold = segment
            return (str(text), default_color, None, bool(bold), None)
        return (str(segment), default_color, None, False, None)

    def _coerce_rich_message(self, msg: object) -> tuple[str, list[tuple] | None]:
        if isinstance(msg, str):
            return msg, None
        if isinstance(msg, (list, tuple)):
            plain_parts: list[str] = []
            segments: list[tuple] = []
            for item in msg:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    return str(msg), None
                text, bold = item
                text = str(text)
                plain_parts.append(text)
                segments.append((text, None, None, bool(bold)))
            return "".join(plain_parts), segments
        return str(msg), None

    # -------- low-level appenders --------
    def _append_block(self, msg: str, level: int, color: object | None = None):
        color = self._resolve_message_color(level, color)
        scrollbar = self._widget.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        cursor = self._widget.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(color)
        fmt.setFontUnderline(False)
        cursor.setCharFormat(fmt)
        cursor.insertText(msg + "\n")
        self._widget.setTextCursor(cursor)

        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        self._inline_active = False

    def _append_inline(self, msg: str, level: int, color: object | None = None):
        color = self._resolve_message_color(level, color)
        scrollbar = self._widget.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        cursor = self._widget.textCursor()
        cursor.movePosition(QTextCursor.End)

        doc = self._widget.document()
        last_block = doc.lastBlock()

        if not self._inline_active:
            # Insert a new block only if the last block already contains text;
            # prevents an empty blank line before the first inline message.
            if doc.blockCount() == 0:
                pass
            else:
                if last_block.text().strip():  # only insert if previous block had content
                    cursor.insertBlock()
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            fmt.setFontUnderline(False)
            cursor.setCharFormat(fmt)
            cursor.insertText(msg)
            self._inline_active = True
            self._inline_level = level
        else:
            start = last_block.position()
            end = start + last_block.length() - 1
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            fmt.setFontUnderline(False)
            cursor.setCharFormat(fmt)
            cursor.insertText(msg)

        self._widget.setTextCursor(cursor)
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _finalize_inline(self):
        if not self._inline_active:
            return
        cursor = self._widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        # Append a single newline ( NOT an empty extra block )
        cursor.insertText("\n")
        self._widget.setTextCursor(cursor)
        self._inline_active = False

    # -------- dispatcher --------
    def _dispatch_log(self, msg: str, level: int, inline: bool, final: bool,
                    color: object | None, segments: object | None, timestamp: bool):
        if segments is not None:
            if self._inline_active:
                self._finalize_inline()
            if timestamp:
                prefix = self._format_message("", level)
                segments = [
                    (prefix, self._resolve_color(level), None, False, None),
                ] + list(segments)
            self._append_segments(segments)
            return
        if inline:
            self._append_inline(msg, level, color)
            if final:
                self._finalize_inline()
            return
        if self._inline_active:
            self._finalize_inline()
        self._append_block(msg, level, color)

    def _append_segments(self, segments: list[tuple]):
        """
        segments: list of (text, fg_color_str, bg_color_str | None, bold: bool, href: str | None)
        Appends all segments as one line, then newlines.
        """
        if self._inline_active:
            self._finalize_inline()

        scrollbar = self._widget.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()
        cursor = self._widget.textCursor()
        cursor.movePosition(QTextCursor.End)

        for segment in segments:
            text, fg, bg, bold, href = self._normalize_segment(segment, self._resolve_color(logging.INFO))
            fmt = QTextCharFormat()
            if fg is not None:
                fmt.setForeground(QColor(fg))
            if bg:
                fmt.setBackground(QColor(bg))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            if href:
                url = self._resolve_link_target(href)
                if url.isEmpty():
                    href = None
                else:
                    href = url.toString() if url.scheme() else url.toLocalFile()
                fmt.setAnchor(True)
                fmt.setAnchorHref(str(href))
                fmt.setFontUnderline(True)
            cursor.setCharFormat(fmt)
            cursor.insertText(text)

        # reset format then newline
        cursor.setCharFormat(QTextCharFormat())
        cursor.insertText("\n")
        self._widget.setTextCursor(cursor)
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    # -------- public API --------
    def log(self,
            msg: object = "",
            level: int = logging.INFO,
            exception: bool = False,
            *,
            inline: bool = False,
            final: bool = False,
            color: object | None = None,
            segments: list[tuple] | None = None,
            timestamp: bool = True,
            **_):
        s, rich_segments = self._coerce_rich_message(msg)
        formatted = self._format_message(s, level) if msg else ""
        if s:
            self._log_to_python(s, level, exception)
        if rich_segments is not None and segments is None:
            default_fg = self._resolve_message_color(level, color)
            normalized_segments: list[tuple] = []
            for text, fg, bg, bold in rich_segments:
                text_segments = self._build_link_segments(text, default_fg if fg is None else fg, bold)
                for seg_text, seg_fg, seg_bg, seg_bold, seg_href in text_segments:
                    normalized_segments.append((seg_text, seg_fg, seg_bg, seg_bold, seg_href))
            rich_segments = normalized_segments
            if timestamp:
                rich_segments = [
                    (self._format_message("", level), self._resolve_color(level), None, False, None),
                ] + rich_segments
            self._log_signal.emit("", level, inline, final, None, rich_segments, False)
            return
        if rich_segments is None and isinstance(s, str) and self._URL_RE.search(s):
            default_fg = self._resolve_message_color(level, color)
            link_segments = self._build_link_segments(s, default_fg)
            if timestamp:
                link_segments = [
                    (self._format_message("", level), self._resolve_color(level), None, False, None),
                ] + link_segments
            self._log_signal.emit("", level, inline, final, None, link_segments, False)
            return
        self._log_signal.emit(formatted, level, inline, final, color, segments, timestamp)

    def log_badge(
        self,
        badge: str,
        badge_bg: str,
        message: "str | list[tuple[str, bool]]",
        message_fg: str,
        *,
        timestamp: bool = True,
        level: int = logging.INFO,
    ) -> None:
        """Emit a colored badge + message line.

        *message* may be a plain ``str``, or a ``list[tuple[str, bool]]`` of
        ``(text, bold)`` pairs to allow selective bold emphasis within the
        message text::

            console.log_badge("REC", "#16a34a",
                              [("Recording", True), (" in progress", False)],
                              "#283618")
        """
        segments: list[tuple] = [
            (f" {badge} ", "#ffffff", badge_bg, True),
            ("  ", None, None, False),
        ]
        if isinstance(message, str):
            segments.append((message, message_fg, None, False))
        elif isinstance(message, tuple) and len(message) == 2 and not isinstance(message[0], (list, tuple)):
            text, bold = message
            segments.append((str(text), message_fg, None, bool(bold)))
        else:
            for text, bold in message:
                segments.append((text, message_fg, None, bold))
        self.log("", level=level, segments=segments, timestamp=timestamp)

    def clear(self):
        self._widget.clear()
        self._inline_active = False

    def eventFilter(self, obj, event):
        try:
            if obj is self._viewport:
                if event.type() == QEvent.Type.MouseButtonRelease:
                    if event.button() != Qt.MouseButton.LeftButton:
                        return super().eventFilter(obj, event)
                    pos = event.position().toPoint()
                    cursor = self._widget.cursorForPosition(pos)
                    char_format = cursor.charFormat()
                    if char_format.isAnchor():
                        href = char_format.anchorHref()
                        if href:
                            QDesktopServices.openUrl(self._resolve_link_target(href))
                            return True
                elif event.type() == QEvent.Type.MouseMove:
                    pos = event.position().toPoint()
                    cursor = self._widget.cursorForPosition(pos)
                    char_format = cursor.charFormat()
                    if char_format.isAnchor() and char_format.anchorHref():
                        self._viewport.setCursor(Qt.CursorShape.PointingHandCursor)
                    else:
                        self._viewport.unsetCursor()
        except RuntimeError:
            return False
        return super().eventFilter(obj, event)

    # Convenience wrappers
    def debug(self, msg: object, **k):   self.log(msg, level=logging.DEBUG, **k)
    def info(self, msg: object, **k):    self.log(msg, level=logging.INFO, **k)
    def warning(self, msg: object, **k): self.log(msg, level=logging.WARNING, **k)
    def error(self, msg: object, **k):   self.log(msg, level=logging.ERROR, **k)
    def exception(self, msg: object, *, show_traceback: bool = True, show_summary: bool = True, **k):
        exc = k.pop("exc", None)
        if exc is None and isinstance(msg, BaseException):
            exc = msg
            msg = f"{type(exc).__name__}: {exc}"

        if exc is not None:
            summary = str(msg)
            tb_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
            self._log_to_python(summary, logging.ERROR, (type(exc), exc, exc.__traceback__))
            if show_summary:
                self._log_signal.emit(self._format_message(summary, logging.ERROR), logging.ERROR, False, False, None, None, True)
            if show_traceback:
                self._log_signal.emit(tb_text, logging.ERROR, False, False, None, None, False)
            return

        self.log(msg, level=logging.ERROR, exception=True, **k)


# ============================================================
# MessageBox console
# ============================================================
class MessageBoxConsole(BaseLogger):
    ICONS = {
        logging.INFO: QMessageBox.Information,
        logging.WARNING: QMessageBox.Warning,
        logging.ERROR: QMessageBox.Critical,
        logging.CRITICAL: QMessageBox.Critical
    }

    def __init__(self, parent=None, logger: logging.Logger = None, formatter: str = None):
        super().__init__(logger, formatter)
        self._parent = parent

    def log(self,
            msg: object,
            level: int = logging.INFO,
            exception: bool = False,
            title: str = "Info",
            icon=None,
            block: bool = False,
            parent=None,
            **_):
        s = str(msg)
        formatted = self._format_message(s, level)
        self._log_to_python(s, level, exception)
        icon = icon or self.ICONS.get(level, QMessageBox.Information)
        parent_widget = parent if parent is not None else self._parent
        box = QMessageBox(icon, title, formatted, parent=parent_widget)
        box.setWindowFlags(box.windowFlags() | Qt.WindowStaysOnTopHint)
        box.exec() if block else box.open()

    # Convenience
    def info(self, msg: object, title: str = "Info", parent=None, **k):
        self.log(msg, level=logging.INFO, title=title, icon=QMessageBox.Information, parent=parent, **k)

    def debug(self, msg: object, title: str = "Debug", parent=None, **k):
        self.log(msg, level=logging.DEBUG, title=title, icon=QMessageBox.Information, parent=parent, **k)

    def warning(self, msg: object, title: str = "Warning", parent=None, **k):
        self.log(msg, level=logging.WARNING, title=title, icon=QMessageBox.Warning, parent=parent, **k)

    def error(self, msg: object, title: str = "Error", parent=None, **k):
        self.log(msg, level=logging.ERROR, title=title, icon=QMessageBox.Critical, parent=parent, **k)

    def exception(self, msg: object, title: str = "Exception", parent=None, **k):
        exc = k.pop("exc", None)
        if exc is None and isinstance(msg, BaseException):
            exc = msg
            msg = f"{type(exc).__name__}: {exc}"

        if exc is not None:
            tb_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
            formatted = self._format_message(f"{msg}\n{tb_text}", logging.ERROR)
            self._log_to_python(str(msg), logging.ERROR, (type(exc), exc, exc.__traceback__))
            icon = QMessageBox.Critical
            parent_widget = parent if parent is not None else self._parent
            box = QMessageBox(icon, title, formatted, parent=parent_widget)
            box.setWindowFlags(box.windowFlags() | Qt.WindowStaysOnTopHint)
            box.exec() if k.get("block", False) else box.open()
            return

        self.log(msg, level=logging.ERROR, exception=True, title=title, icon=QMessageBox.Critical, parent=parent, **k)