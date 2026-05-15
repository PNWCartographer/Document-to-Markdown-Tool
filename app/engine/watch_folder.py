"""
Watch-folder engine.

Monitors a directory for new files with supported extensions and
auto-converts them using the existing ConversionJob infrastructure.

Cross-platform: watchdog uses inotify (Linux), FSEvents (macOS),
ReadDirectoryChangesW (Windows).
"""

import os
import threading
import time
from typing import Callable, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from .converter import ConversionJob

_SUPPORTED_EXTS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv",
    ".pptx", ".epub",
    ".png", ".jpg", ".jpeg", ".tiff", ".bmp",
}

_SETTLE_SECONDS = 1.5


class _WatchHandler(FileSystemEventHandler):
    """Enqueue supported files when they appear in the watched folder."""

    def __init__(self, enqueue: Callable[[str], None]):
        super().__init__()
        self._enqueue = enqueue

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            self._enqueue(event.src_path)

    def on_moved(self, event):
        if isinstance(event, FileMovedEvent) and not event.is_directory:
            self._enqueue(event.dest_path)


class FolderWatcher:
    """
    Watches a directory and auto-converts new files.

    Parameters
    ----------
    watch_path : str
        Directory to monitor.
    output_path : str
        Root directory for conversion output.
    cfg : dict
        Settings dict (same format as app config).
    root : tk.Tk
        Tkinter root for scheduling GUI callbacks.
    on_file_queued : callback(path)
        Called when a file is detected and queued.
    on_file_started : callback(path)
        Called when conversion begins for a file.
    on_file_done : callback(path, success, message)
        Called when a file finishes (success=True/False).
    on_error : callback(message)
        Called on watcher-level errors.
    """

    def __init__(
        self,
        watch_path: str,
        output_path: str,
        cfg: dict,
        root,
        on_file_queued: Callable[[str], None],
        on_file_started: Callable[[str], None],
        on_file_done: Callable[[str, bool, str], None],
        on_error: Callable[[str], None],
    ):
        self._watch_path = watch_path
        self._output_path = output_path
        self._cfg = dict(cfg)
        self._root = root

        self._on_file_queued = on_file_queued
        self._on_file_started = on_file_started
        self._on_file_done = on_file_done
        self._on_error = on_error

        self._observer: Optional[Observer] = None
        self._queue: list[str] = []
        self._lock = threading.Lock()
        self._processing = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        self._completed = 0
        self._failed = 0

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()

    @property
    def completed_count(self) -> int:
        return self._completed

    @property
    def failed_count(self) -> int:
        return self._failed

    def start(self) -> None:
        if self.is_running:
            return

        if not os.path.isdir(self._watch_path):
            self._gui(self._on_error, f"Watch folder does not exist: {self._watch_path}")
            return

        os.makedirs(self._output_path, exist_ok=True)

        self._stop_event.clear()
        self._completed = 0
        self._failed = 0

        handler = _WatchHandler(self._enqueue_file)
        self._observer = Observer()
        self._observer.schedule(handler, self._watch_path, recursive=False)
        self._observer.start()

        self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        with self._lock:
            self._queue.clear()

    def _enqueue_file(self, path: str) -> None:
        ext = os.path.splitext(path)[1].lower()
        if ext not in _SUPPORTED_EXTS:
            return

        with self._lock:
            if path not in self._queue:
                self._queue.append(path)
        self._gui(self._on_file_queued, path)

    def _process_loop(self) -> None:
        while not self._stop_event.is_set():
            path = None
            with self._lock:
                if self._queue:
                    path = self._queue.pop(0)

            if path is None:
                time.sleep(0.5)
                continue

            if not self._wait_for_stable(path):
                continue

            self._convert_file(path)

    def _wait_for_stable(self, path: str) -> bool:
        """Wait until the file size stops changing (fully written)."""
        prev_size = -1
        for _ in range(20):
            if self._stop_event.is_set():
                return False
            try:
                size = os.path.getsize(path)
            except OSError:
                return False
            if size == prev_size and size > 0:
                return True
            prev_size = size
            time.sleep(_SETTLE_SECONDS)
        return True

    def _convert_file(self, path: str) -> None:
        filename = os.path.basename(path)
        self._gui(self._on_file_started, path)

        done_event = threading.Event()
        result_holder: list = []

        def on_done(batch_result):
            result_holder.append(batch_result)
            done_event.set()

        try:
            job = ConversionJob(
                files=[path],
                aliases={},
                output_root=self._output_path,
                cfg=self._cfg,
                root=self._root,
                on_log=lambda msg: None,
                on_file_progress=lambda f: None,
                on_overall_progress=lambda f: None,
                on_file_start=lambda name, idx, total: None,
                on_stage=lambda s: None,
                on_done=on_done,
            )
            job.start()

            done_event.wait(timeout=300)

            if result_holder:
                br = result_holder[0]
                if br.failed == 0:
                    self._completed += 1
                    self._gui(self._on_file_done, path, True, f"Converted: {filename}")
                else:
                    self._failed += 1
                    self._gui(self._on_file_done, path, False, f"Failed: {filename}")
            else:
                self._failed += 1
                self._gui(self._on_file_done, path, False, f"Timeout: {filename}")

        except Exception as e:
            self._failed += 1
            self._gui(self._on_file_done, path, False, f"Error: {filename} — {e}")

    def _gui(self, callback, *args) -> None:
        """Marshal a callback onto the tkinter main thread."""
        try:
            self._root.after(0, callback, *args)
        except Exception:
            pass
