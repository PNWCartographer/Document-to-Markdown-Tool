"""
Per-file conversion logger.

Writes a timestamped conversion_log.txt alongside each output .md file.
Also maintains an in-memory list of entries so the GUI log panel can be
populated without reading the file back from disk.
"""

import datetime
import os
from typing import Callable, Optional


class ConversionLogger:
    """
    Collects log entries during a single file conversion and writes them to
    <output_dir>/conversion_log.txt on flush().

    Parameters
    ----------
    source_file : str
        Absolute path to the source document being converted.
    output_dir : str
        Directory where conversion_log.txt will be written.
    gui_callback : callable, optional
        Called with (str) for each new log line so the GUI panel stays live.
    """

    LEVELS = ("INFO", "WARNING", "ERROR")

    def __init__(
        self,
        source_file: str,
        output_dir: str,
        gui_callback: Optional[Callable[[str], None]] = None,
    ):
        self._source = source_file
        self._output_dir = output_dir
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
        """Write all collected entries to conversion_log.txt."""
        os.makedirs(self._output_dir, exist_ok=True)
        log_path = os.path.join(self._output_dir, "conversion_log.txt")
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write(f"Conversion Log\n")
            fh.write(f"Source: {self._source}\n")
            if self._start_time:
                fh.write(f"Started: {self._start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            if self._end_time:
                fh.write(f"Finished: {self._end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            fh.write("-" * 60 + "\n")
            for entry in self._entries:
                fh.write(entry + "\n")

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


class AppLogger:
    """
    Application-level logger. Writes to a single app.log in the logs/ folder
    next to the output root. Used for startup, shutdown, and cross-file events.
    """

    def __init__(self, log_dir: str):
        self._log_dir = log_dir
        self._path = os.path.join(log_dir, "app.log")
        os.makedirs(log_dir, exist_ok=True)

    def info(self, message: str) -> None:
        self._write("INFO", message)

    def warning(self, message: str) -> None:
        self._write("WARNING", message)

    def error(self, message: str) -> None:
        self._write("ERROR", message)

    def _write(self, level: str, message: str) -> None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} | {level:<7} | {message}\n"
        try:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError:
            pass
