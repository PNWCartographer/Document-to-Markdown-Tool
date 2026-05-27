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
from .output_formats import write_output as write_alt_format, output_path_for
from .rules_engine import load_profiles, get_profile_by_name
from . import license_manager
from . import searchable_pdf


# Language display names → ISO 639-1 codes used by ocr_engine
_LANG_MAP = {
    "English":    "en",
    "French":     "fr",
    "German":     "de",
    "Spanish":    "es",
    "Italian":    "it",
    "Portuguese": "pt",
    "Dutch":      "nl",
    "Auto-detect": "en",   # fallback; RapidOCR handles multi-language on its own
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
        page_ranges: dict[str, list[int]] | None = None,  # per-file page selections
    ):
        self._files = list(files)
        self._aliases = dict(aliases)
        self._output_root = output_root
        self._cfg = dict(cfg)
        self._page_ranges = page_ranges or {}
        self._root = root

        self._on_log = on_log
        self._on_file_progress = on_file_progress
        self._on_overall_progress = on_overall_progress
        self._on_file_start = on_file_start
        self._on_stage = on_stage
        self._on_done = on_done

        self._cancel_event = threading.Event()
        self._write_lock = threading.Lock()
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

        # Resolve worker count
        workers_cfg = self._cfg.get("parallel_workers", "1")
        if workers_cfg == "Auto":
            from . import system_info
            workers = system_info.detect_system().recommended_workers
        else:
            try:
                workers = max(1, int(workers_cfg))
            except (ValueError, TypeError):
                workers = 1

        if workers > 1 and total > 1:
            completed, failed, results = self._run_parallel(
                total, workers, app_logger, results,
            )
        else:
            completed, failed, results = self._run_sequential(
                total, app_logger, results,
            )

        # Build batch result (shared by both sequential and parallel paths)
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
    # Sequential processing (workers=1, default)
    # ------------------------------------------------------------------

    def _run_sequential(self, total, app_logger, results):
        completed = 0
        failed = 0

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

            use_subfolder = self._cfg.get("output_subfolder", True)
            out_dir = output_dir_for(source_file, self._output_root, alias, use_subfolder)

            logger = ConversionLogger(
                source_file=source_file,
                gui_callback=lambda line: self._gui(self._on_log, line),
            )
            logger.start()

            try:
                fmt = self._cfg.get("output_format", "Markdown")

                if fmt == "Searchable PDF":
                    self._gui(self._on_stage, "Creating searchable PDF…")
                    output = self._convert_searchable_pdf(
                        source_file, alias, use_subfolder, logger,
                    )
                else:
                    output = self._convert_file(source_file, alias, logger)
                    self._gui(self._on_stage, "Writing output…")
                    self._write_output(output, use_subfolder)

                if output.confidence:
                    write_confidence_report(output.confidence)
                    results.append(output.confidence)

                # Write per-file artifacts to the output folder
                logger.end()
                self._write_per_file_artifacts(
                    output, logger, out_dir, use_subfolder)
                logger.flush()
                completed += 1
                license_manager.increment_conversion_count(1)
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

        return completed, failed, results

    # ------------------------------------------------------------------
    # Parallel processing (workers>1)
    # ------------------------------------------------------------------

    def _run_parallel(self, total, workers, app_logger, results):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        completed = 0
        failed = 0

        self._gui(self._on_log, f"Parallel mode: {workers} workers")
        self._gui(self._on_stage, f"Converting {total} files ({workers} workers)…")

        use_subfolder = self._cfg.get("output_subfolder", True)
        finished_count = 0

        def convert_one(idx, source_file):
            """Convert a single file — runs on a worker thread."""
            if self._cancel_event.is_set():
                return None, None, "cancelled"

            alias = self._aliases.get(source_file, "")
            logger = ConversionLogger(
                source_file=source_file,
                gui_callback=lambda line: self._gui(self._on_log, line),
            )
            logger.start()

            try:
                fmt = self._cfg.get("output_format", "Markdown")

                if fmt == "Searchable PDF":
                    with self._write_lock:
                        output = self._convert_searchable_pdf(
                            source_file, alias, use_subfolder, logger,
                        )
                else:
                    output = self._convert_file(source_file, alias, logger)
                    with self._write_lock:
                        self._write_output(output, use_subfolder)

                if output.confidence:
                    write_confidence_report(output.confidence)

                logger.end()
                out_dir = output_dir_for(source_file, self._output_root,
                                         alias, use_subfolder)
                self._write_per_file_artifacts(
                    output, logger, out_dir, use_subfolder)
                logger.flush()
                license_manager.increment_conversion_count(1)
                return output.confidence, source_file, "ok"

            except FileExistsError as e:
                logger.warning(f"Skipped — output already exists: {e}")
                logger.end()
                logger.flush()
                return None, source_file, "skipped"

            except Exception as e:
                logger.error(f"Conversion failed: {e}")
                logger.end()
                logger.flush()
                return None, source_file, f"failed: {e}"

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(convert_one, idx, sf): (idx, sf)
                for idx, sf in enumerate(self._files)
            }

            for future in as_completed(futures):
                if self._cancel_event.is_set():
                    break

                idx, sf = futures[future]
                filename = os.path.basename(sf)
                finished_count += 1

                try:
                    conf, src, status = future.result()
                except Exception as e:
                    status = f"failed: {e}"
                    conf = None

                if status == "ok":
                    completed += 1
                    if conf:
                        results.append(conf)
                    self._gui(self._on_log, f"   ✓ Done — {filename}")
                elif status == "skipped":
                    self._gui(self._on_log, f"   ⚠ Skipped — {filename}")
                elif status == "cancelled":
                    pass
                else:
                    failed += 1
                    self._gui(self._on_log, f"   ✗ {status} — {filename}")
                    app_logger.error(f"Failed: {sf} | {status}")

                self._gui(self._on_overall_progress, finished_count / total)
                self._gui(self._on_file_start, filename, finished_count, total)

        return completed, failed, results

    # ------------------------------------------------------------------
    # Output writer helper (shared by sequential & parallel)
    # ------------------------------------------------------------------

    def _write_output(self, output, use_subfolder):
        """Write conversion output in the configured format."""
        fmt = self._cfg.get("output_format", "Markdown")
        overwrite = self._cfg.get("overwrite_existing", False)
        inc_pages = self._cfg.get("preserve_page_numbers", False)
        inc_toc = self._cfg.get("rebuild_toc", False)
        front_matter = self._cfg.get("yaml_front_matter", False)
        flavor = self._cfg.get("markdown_flavor", "GFM")

        profile_name = self._cfg.get("rules_profile", "None")
        rules_profile = None
        if profile_name and profile_name != "None":
            profiles = load_profiles()
            rules_profile = get_profile_by_name(profiles, profile_name)

        if fmt == "Markdown":
            write_markdown(
                output,
                output_root=self._output_root,
                use_subfolder=use_subfolder,
                include_confidence_summary=True,
                include_page_numbers=inc_pages,
                rebuild_toc=inc_toc,
                overwrite=overwrite,
                yaml_front_matter=front_matter,
                markdown_flavor=flavor,
                rules_profile=rules_profile,
            )
        else:
            write_alt_format(
                output,
                output_root=self._output_root,
                fmt=fmt,
                use_subfolder=use_subfolder,
                include_confidence=True,
                include_page_numbers=inc_pages,
                rebuild_toc=inc_toc,
                overwrite=overwrite,
            )

    # ------------------------------------------------------------------
    # Searchable PDF helper
    # ------------------------------------------------------------------

    def _convert_searchable_pdf(
        self, source_file: str, alias: str, use_subfolder: bool,
        logger: ConversionLogger,
    ) -> ConversionOutput:
        """Run the Searchable PDF pipeline (ocrmypdf + RapidOCR plugin)."""
        cfg = self._cfg
        lang = _LANG_MAP.get(cfg.get("ocr_language", "English"), "en")

        # Map 2-letter code to 3-letter for ocrmypdf/Tesseract compat
        _LANG_3 = {
            "en": "eng", "fr": "fra", "de": "deu", "es": "spa",
            "it": "ita", "pt": "por", "nl": "nld",
        }
        lang3 = _LANG_3.get(lang, "eng")

        def progress(p: float):
            self._gui(self._on_file_progress, p)

        return searchable_pdf.convert(
            source_file=source_file,
            alias=alias,
            output_root=self._output_root,
            use_subfolder=use_subfolder,
            overwrite=cfg.get("overwrite_existing", False),
            deskew=cfg.get("spdf_deskew", True),
            clean=cfg.get("spdf_clean", False),
            force_ocr=cfg.get("spdf_force_ocr", False),
            optimize_level=cfg.get("spdf_optimize", 1),
            pdfa=cfg.get("spdf_pdfa", False),
            sidecar=cfg.get("spdf_sidecar", False),
            language=lang3,
            logger=logger,
            progress_callback=progress,
        )

    # ------------------------------------------------------------------
    # Per-file artifact writer
    # ------------------------------------------------------------------

    @staticmethod
    def _write_per_file_artifacts(
        output: ConversionOutput,
        logger: ConversionLogger,
        out_dir: str,
        use_subfolder: bool,
    ) -> None:
        """
        Write confidence_report.txt and conversion_log.txt into the
        per-file output folder alongside the converted output.
        """
        if not out_dir or not use_subfolder:
            return  # only meaningful with subfolder structure
        try:
            os.makedirs(out_dir, exist_ok=True)

            # confidence_report.txt
            if output.confidence:
                report_path = os.path.join(out_dir, "confidence_report.txt")
                with open(report_path, "w", encoding="utf-8") as fh:
                    fh.write(output.confidence.to_report_text())

            # conversion_log.txt
            entries = logger.entries()
            if entries:
                log_path = os.path.join(out_dir, "conversion_log.txt")
                with open(log_path, "w", encoding="utf-8") as fh:
                    fh.write(f"Conversion Log — {os.path.basename(output.source_file)}\n")
                    fh.write(f"{'=' * 60}\n\n")
                    for entry in entries:
                        fh.write(entry + "\n")
        except OSError:
            pass

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

        # New settings
        auto_translate = cfg.get("auto_translate", True)
        dxf_svg_preview = cfg.get("dxf_svg_preview", True)
        ocr_engine_pref = cfg.get("ocr_engine", "Auto")

        # Map OCR engine setting → run_ocr prefer_engine parameter
        from .ocr_platform import map_engine_setting
        prefer_engine = map_engine_setting(ocr_engine_pref)

        # Quality preset overrides for PDF conversion
        quality = cfg.get("quality_preset", "Quality")
        # Map quality preset → OCR render DPI scale
        _DPI_MAP = {"Fast": 2.0, "Balanced": 3.0, "Quality": 4.0}
        ocr_dpi_scale = _DPI_MAP.get(quality, 4.0)

        if quality == "Fast" and ext == ".pdf":
            # Fast: force pymupdf-only path, skip OCR
            mode = "Standard"
            if logger:
                logger.info("Quality preset: Fast — using standard extraction only, skipping OCR.")
        elif quality == "Balanced" and ext == ".pdf":
            if logger:
                logger.info("Quality preset: Balanced — standard pipeline, medium OCR resolution.")

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
                remove_headers_footers=cfg.get("remove_headers_footers", True),
                skip_blank_pages=cfg.get("skip_blank_pages", True),
                strip_line_numbers=cfg.get("strip_line_numbers", False),
                detect_code_blocks=cfg.get("detect_code_blocks", True),
                detect_footnotes=cfg.get("detect_footnotes", True),
                detect_equations=cfg.get("detect_equations", True),
                auto_translate=auto_translate,
                prefer_engine=prefer_engine,
                ocr_dpi_scale=ocr_dpi_scale,
                page_range=self._page_ranges.get(source_file),
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
                remove_headers_footers=cfg.get("remove_headers_footers", True),
                skip_blank_pages=cfg.get("skip_blank_pages", True),
                strip_line_numbers=cfg.get("strip_line_numbers", False),
                detect_code_blocks=cfg.get("detect_code_blocks", True),
                detect_footnotes=cfg.get("detect_footnotes", True),
                detect_equations=cfg.get("detect_equations", True),
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

        elif ext == ".pptx":
            stage("Parsing presentation…")
            from . import pptx_converter
            return pptx_converter.convert(
                source_file,
                alias=alias,
                output_root=self._output_root,
                preserve_images=preserve_images,
                use_subfolder=use_subfolder,
                logger=logger,
                progress_callback=progress,
            )

        elif ext == ".epub":
            stage("Reading e-book…")
            from . import epub_converter
            return epub_converter.convert(
                source_file,
                alias=alias,
                output_root=self._output_root,
                preserve_images=preserve_images,
                use_subfolder=use_subfolder,
                rebuild_toc=rebuild_toc,
                logger=logger,
                progress_callback=progress,
            )

        elif ext in (".html", ".htm"):
            stage("Parsing HTML…")
            from . import html_converter
            return html_converter.convert(
                source_file,
                alias=alias,
                output_root=self._output_root,
                preserve_images=preserve_images,
                use_subfolder=use_subfolder,
                logger=logger,
                progress_callback=progress,
            )

        elif ext == ".dxf":
            stage("Parsing DXF drawing…")
            from . import dxf_converter
            return dxf_converter.convert(
                source_file,
                alias=alias,
                output_root=self._output_root,
                preserve_images=preserve_images,
                use_subfolder=use_subfolder,
                render_svg=dxf_svg_preview,
                logger=logger,
                progress_callback=progress,
            )

        elif ext == ".rtf":
            stage("Parsing RTF document…")
            from . import rtf_converter
            return rtf_converter.convert(
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
                auto_translate=auto_translate,
                prefer_engine=prefer_engine,
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
