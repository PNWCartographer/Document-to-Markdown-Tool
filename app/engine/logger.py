"""
Unified application logger.

All logging — app-level events and per-file conversion detail — writes to a
single file at %APPDATA%/DocToMarkdown/app.log so output folders stay clean.

ConversionLogger collects entries during a single file conversion and feeds
them to the GUI log panel live via gui_callback. It also appends each entry
to the shared app log on flush().
"""

import datetime
import os
import sys
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Shared app-data directory and log path (cross-platform)
# ---------------------------------------------------------------------------

_MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB

if sys.platform == "win32":
    _APPDATA_DIR = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "DocToMarkdown",
    )
elif sys.platform == "darwin":
    _APPDATA_DIR = os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", "DocToMarkdown",
    )
else:
    _APPDATA_DIR = os.path.join(
        os.path.expanduser("~"), ".local", "share", "DocToMarkdown",
    )
APP_LOG_PATH = os.path.join(_APPDATA_DIR, "app.log")


def _ensure_appdata_dir() -> None:
    os.makedirs(_APPDATA_DIR, exist_ok=True)
    # Simple log rotation: if app.log exceeds 5 MB, rename to app.log.old
    try:
        if os.path.isfile(APP_LOG_PATH) and os.path.getsize(APP_LOG_PATH) > _MAX_LOG_SIZE:
            old_path = APP_LOG_PATH + ".old"
            try:
                os.replace(APP_LOG_PATH, old_path)
            except OSError:
                pass
    except OSError:
        pass


def appdata_dir() -> str:
    """Return (and ensure) the %APPDATA%/DocToMarkdown directory."""
    _ensure_appdata_dir()
    return _APPDATA_DIR


# ---------------------------------------------------------------------------
# ConversionLogger — per-file, feeds GUI + appends to unified log
# ---------------------------------------------------------------------------

class ConversionLogger:
    """
    Collects log entries during a single file conversion.

    Parameters
    ----------
    source_file : str
        Absolute path to the source document being converted.
    gui_callback : callable, optional
        Called with (str) for each new log line so the GUI panel stays live.
    """

    LEVELS = ("INFO", "WARNING", "ERROR")

    def __init__(
        self,
        source_file: str,
        gui_callback: Optional[Callable[[str], None]] = None,
    ):
        self._source = source_file
        self._gui_callback = gui_callback
        self._entries: list[str] = []
        self._start_time: Optional[datetime.datetime] = None
        self._end_time: Optional[datetime.datetime] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._start_time = datetime.datetime.now()
        self.info(f"Started conversion | file={os.path.basename(self._source)}")

    def end(self) -> None:
        self._end_time = datetime.datetime.now()
        elapsed = (
            (self._end_time - self._start_time).total_seconds()
            if self._start_time
            else 0.0
        )
        self.info(f"Conversion finished | elapsed={elapsed:.1f}s")

    def info(self, message: str) -> None:
        self._log("INFO", message)

    def warning(self, message: str) -> None:
        self._log("WARNING", message)

    def error(self, message: str) -> None:
        self._log("ERROR", message)

    def flush(self) -> None:
        """Append all collected entries to the unified app log."""
        _ensure_appdata_dir()
        try:
            with open(APP_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(f"--- Conversion: {os.path.basename(self._source)}")
                if self._start_time:
                    fh.write(f" | {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                fh.write(" ---\n")
                for entry in self._entries:
                    fh.write(entry + "\n")
        except OSError:
            pass

    def entries(self) -> list[str]:
        """Return all log entries collected so far (read-only copy)."""
        return list(self._entries)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(self, level: str, message: str) -> None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {level:<7} | {message}"
        self._entries.append(line)
        if self._gui_callback:
            try:
                self._gui_callback(line)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# AppLogger — app-level events (startup, batch start/finish)
# ---------------------------------------------------------------------------

class AppLogger:
    """Writes app-level events to the unified %APPDATA%/DocToMarkdown/app.log."""

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warning(self, message: str) -> None:
        self._write("WARNING", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def _write(self, level: str, message: str) -> None:
        _ensure_appdata_dir()
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {level:<7} | {message}\n"
        try:
            with open(APP_LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass
