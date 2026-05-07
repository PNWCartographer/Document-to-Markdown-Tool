"""
Conversion orchestrator.

ConversionJob runs all files on a background thread and pushes GUI updates
back to the main thread via root.after() callbacks. The GUI never blocks.

Usage (from app.py):
    job = ConversionJob(
        files=self._selected_files,
        aliases=self._file_aliases,
        output_root=self._output_path,
        cfg=self._cfg,
        root=self.root,
        on_log=self._log_write,
        on_file_progress=...,
        on_overall_progress=...,
        on_file_start=...,
        on_stage=...,
        on_done=...,
    )
    job.start()
    self._active_job = job

To cancel:
    job.cancel()
"""

import os
import threading
from typing import Callable, Optional

from .logger import ConversionLogger, AppLogger
from .confidence import ConfidenceResult, aggregate_confidence, write_confidence_report
from .markdown_writer import (
    ConversionOutput,
    write_markdown,
    output_dir_for,
)


# Language display names → ISO 639-1 codes used by ocr_engine
_LANG_MAP = {
    "English":    "en",
    "French":     "fr",
    "German":     "de",
    "Spanish":    "es",
    "Italian":    "it",
    "Portuguese": "pt",
    "Dutch":      "nl",
    "Auto-detect": "en",   # fallback; PaddleOCR handles multi-language on its own
}


class ConversionJob:
    """
    Manages a single batch conversion run on a background thread.

    All GUI callbacks are marshalled through root.after() so they
    execute on the main thread and are safe to touch tkinter widgets.
    """

    def __init__(
        self,
        files: list[str],
        aliases: dict[str, str],
        output_root: str,
        cfg: dict,
        root,                                           # tk.Tk root widget
        on_log: Callable[[str], None],
        on_file_progress: Callable[[float], None],      # 0.0–1.0
        on_overall_progress: Callable[[float], None],   # 0.0–1.0
        on_file_start: Callable[[str, int, int], None], # (filename, idx, total)
        on_stage: Callable[[str], None],                # stage description
        on_done: Callable[["BatchResult"], None],       # called on completion
    ):
        self._files = list(files)
        self._aliases = dict(aliases)
        self._output_root = output_root
        self._cfg = dict(cfg)
        self._root = root

        self._on_log = on_log
        self._on_file_progress = on_file_progress
        self._on_overall_progress = on_overall_progress
        self._on_file_start = on_file_start
        self._on_stage = on_stage
        self._on_done = on_done

        self._cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._cancel_event.set()

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Background thread entry point
    # ------------------------------------------------------------------

    def _run(self) -> None:
        total = len(self._files)
        results: list[ConfidenceResult] = []
        completed = 0
        failed = 0

        # App-level logger — writes to %APPDATA%\DocToMarkdown\app.log
        app_logger = AppLogger()
        app_logger.info(f"Batch started | files={total}")

        for idx, source_file in enumerate(self._files):
            if self._cancel_event.is_set():
                self._gui(self._on_log, "Conversion cancelled.")
                break

            filename = os.path.basename(source_file)
            alias = self._aliases.get(source_file, "")

            self._gui(self._on_file_start, filename, idx + 1, total)
            self._gui(self._on_overall_progress, idx / total)
            self._gui(self._on_file_progress, 0.0)
            self._gui(self._on_stage, "Initialising…")
            self._gui(self._on_log, f"── [{idx + 1}/{total}] {filename}")

            # Determine output dir
            use_subfolder = self._cfg.get("output_subfolder", True)
            out_dir = output_dir_for(source_file, self._output_root, alias, use_subfolder)

            # Per-file logger
            logger = ConversionLogger(
                source_file=source_file,
                gui_callback=lambda line: self._gui(self._on_log, line),
            )
            logger.start()

            try:
                output = self._convert_file(source_file, alias, logger)
                self._gui(self._on_stage, "Writing output…")

                # Write Markdown
                write_markdown(
                    output,
                    output_root=self._output_root,
                    use_subfolder=use_subfolder,
                    include_confidence_summary=True,
                    include_page_numbers=self._cfg.get("preserve_page_numbers", False),
                    rebuild_toc=self._cfg.get("rebuild_toc", False),
                    overwrite=self._cfg.get("overwrite_existing", False),
                )

                # Write confidence report to %APPDATA%\DocToMarkdown\
                if output.confidence:
                    write_confidence_report(output.confidence)
                    results.append(output.confidence)

                logger.end()
                logger.flush()

                completed += 1
                self._gui(self._on_log, f"   ✓ Done → {out_dir}")

            except FileExistsError as e:
                logger.warning(f"Skipped — output already exists: {e}")
                logger.end()
                logger.flush()
                self._gui(self._on_log, f"   ⚠ Skipped (file exists) — {filename}")
                app_logger.warning(f"Skipped (exists): {source_file}")

            except Exception as e:
                logger.error(f"Conversion failed: {e}")
                logger.end()
                logger.flush()
                failed += 1
                self._gui(self._on_log, f"   ✗ Failed — {filename}: {e}")
                app_logger.error(f"Failed: {source_file} | {e}")

            overall_frac = (idx + 1) / total
            self._gui(self._on_overall_progress, overall_frac)
            self._gui(self._on_file_progress, 1.0)
            self._gui(self._on_stage, "")

        # Build batch result
        batch_confidence = aggregate_confidence(results) if results else ConfidenceResult()
        batch_result = BatchResult(
            total=total,
            completed=completed,
            failed=failed,
            cancelled=self._cancel_event.is_set(),
            output_root=self._output_root,
            batch_confidence=batch_confidence,
            all_confidence=results,
        )

        app_logger.info(
            f"Batch finished | completed={completed} failed={failed} "
            f"cancelled={batch_result.cancelled}"
        )
        self._gui(self._on_done, batch_result)

    # ------------------------------------------------------------------
    # File type routing
    # ------------------------------------------------------------------

    def _convert_file(self, source_file: str, alias: str, logger: ConversionLogger) -> ConversionOutput:
        ext = os.path.splitext(source_file)[1].lower()
        cfg = self._cfg
        lang = _LANG_MAP.get(cfg.get("ocr_language", "English"), "en")
        mode = cfg.get("conversion_mode", "Auto-detect")
        preserve_images = cfg.get("preserve_images", True)
        rebuild_toc = cfg.get("rebuild_toc", False)
        preserve_pages = cfg.get("preserve_page_numbers", False)

        def progress(p: float):
            self._gui(self._on_file_progress, p)

        def stage(s: str):
            self._gui(self._on_stage, s)

        use_subfolder = self._cfg.get("output_subfolder", True)

        if ext == ".pdf":
            stage("Analyzing PDF…")
            from . import pdf_converter
            return pdf_converter.convert(
                source_file,
                alias=alias,
                output_root=self._output_root,
                conversion_mode=mode,
                language=lang,
                preserve_images=preserve_images,
                rebuild_toc=rebuild_toc,
                preserve_page_numbers=preserve_pages,
                use_subfolder=use_subfolder,
                embed_images=self._cfg.get("embed_images", True),
                logger=logger,
                progress_callback=progress,
            )

        elif ext in (".docx", ".doc"):
            stage("Parsing document…")
            from . import docx_converter
            return docx_converter.convert(
                source_file,
                alias=alias,
                output_root=self._output_root,
                language=lang,
                preserve_images=preserve_images,
                rebuild_toc=rebuild_toc,
                preserve_page_numbers=preserve_pages,
                use_subfolder=use_subfolder,
                logger=logger,
                progress_callback=progress,
            )

        elif ext in (".xlsx", ".xls"):
            stage("Reading spreadsheet…")
            from . import xlsx_converter
            return xlsx_converter.convert(
                source_file,
                alias=alias,
                logger=logger,
                progress_callback=progress,
            )

        elif ext == ".csv":
            stage("Parsing CSV…")
            from . import csv_converter
            return csv_converter.convert(
                source_file,
                alias=alias,
                logger=logger,
                progress_callback=progress,
            )

        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"):
            stage("Processing image…")
            from . import image_converter
            return image_converter.convert(
                source_file,
                alias=alias,
                output_root=self._output_root,
                language=lang,
                preserve_images=preserve_images,
                use_subfolder=use_subfolder,
                logger=logger,
                progress_callback=progress,
            )

        else:
            logger.warning(f"Unsupported file type: {ext}")
            output = ConversionOutput(source_file=source_file, alias=alias)
            output.confidence = ConfidenceResult(source_file=source_file)
            output.confidence.overall = "Failed"
            output.confidence.text_extraction = "Failed"
            output.confidence.add_warning(f"File type '{ext}' is not supported.")
            return output

    # ------------------------------------------------------------------
    # Thread-safe GUI dispatch
    # ------------------------------------------------------------------

    def _gui(self, fn: Callable, *args) -> None:
        """Schedule a callback on the main thread via root.after()."""
        try:
            self._root.after(0, fn, *args)
        except Exception:
            pass


class BatchResult:
    """Summary of a completed conversion batch."""

    def __init__(
        self,
        total: int,
        completed: int,
        failed: int,
        cancelled: bool,
        output_root: str,
        batch_confidence: ConfidenceResult,
        all_confidence: list[ConfidenceResult],
    ):
        self.total = total
        self.completed = completed
        self.failed = failed
        self.cancelled = cancelled
        self.output_root = output_root
        self.batch_confidence = batch_confidence
        self.all_confidence = all_confidence

    @property
    def status_text(self) -> str:
        if self.cancelled:
            return f"Cancelled — {self.completed} of {self.total} file(s) completed."
        if self.failed == 0:
            return f"Conversion complete — {self.completed} of {self.total} file(s) converted successfully."
        return (
            f"Conversion finished with errors — "
            f"{self.completed} succeeded, {self.failed} failed, "
            f"{self.total - self.completed - self.failed} skipped."
        )
