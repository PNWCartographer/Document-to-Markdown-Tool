"""
Searchable PDF converter.

Takes a scanned or image-based PDF and adds an invisible OCR text layer
using ocrmypdf, making it full-text searchable, copyable, and accessible.
The original visual appearance is preserved.

Uses a custom RapidOCR plugin to route OCR through ONNX Runtime instead
of Tesseract, enabling GPU acceleration on all platforms.

Supports:
- Ensemble OCR (RapidOCR + Tesseract merged by confidence)
- Background removal for colored/noisy scans
- Auto-chunking for documents >30 pages (parallel via ProcessPoolExecutor)
- Sidecar RAG chunk generation from extracted text

This module bypasses the normal text-extraction → text-writing pipeline.
The output is a PDF file written directly by ocrmypdf.
"""

import json
import os
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput, output_dir_for, _safe_stem
from .logger import ConversionLogger


# ---------------------------------------------------------------------------
# Ghostscript binary discovery
# ---------------------------------------------------------------------------

_GHOSTSCRIPT_SEARCH_PATHS = [
    # Windows (64-bit)
    r"C:\Program Files\gs",
    r"C:\Program Files (x86)\gs",
    # Chocolatey
    os.path.join(os.environ.get("ProgramData", ""), "chocolatey", "bin"),
]


def _find_ghostscript_binary() -> Optional[str]:
    """Find the Ghostscript binary on this system."""
    # Check PATH first
    for name in ("gswin64c", "gswin32c", "gs"):
        found = shutil.which(name)
        if found:
            return found

    # Windows: search common install directories
    if sys.platform == "win32":
        for base_dir in _GHOSTSCRIPT_SEARCH_PATHS:
            if not os.path.isdir(base_dir):
                continue
            for root, dirs, files in os.walk(base_dir):
                for fname in ("gswin64c.exe", "gswin32c.exe"):
                    candidate = os.path.join(root, fname)
                    if os.path.isfile(candidate):
                        return candidate

    return None


def ghostscript_available() -> bool:
    """Check if Ghostscript is installed and accessible."""
    return _find_ghostscript_binary() is not None


def _ensure_ghostscript_on_path() -> None:
    """Add Ghostscript bin directory to PATH if not already there."""
    gs = _find_ghostscript_binary()
    if gs and shutil.which("gswin64c") is None and shutil.which("gs") is None:
        gs_dir = os.path.dirname(gs)
        os.environ["PATH"] = gs_dir + os.pathsep + os.environ.get("PATH", "")


def ocrmypdf_available() -> bool:
    """Check if ocrmypdf is importable."""
    try:
        import ocrmypdf  # noqa: F401
        return True
    except Exception:
        return False


def is_available() -> bool:
    """Check if the Searchable PDF pipeline is fully available."""
    return ocrmypdf_available() and ghostscript_available()


# ---------------------------------------------------------------------------
# Auto-chunking constants
# ---------------------------------------------------------------------------

_CHUNK_THRESHOLD = 30   # pages — split documents larger than this


# ---------------------------------------------------------------------------
# Module-level chunk worker (must be top-level for Windows spawn mode)
# ---------------------------------------------------------------------------

def _process_chunk(
    source_chunk: str,
    output_chunk: str,
    plugin_path: str,
    language: str,
    deskew: bool,
    clean: bool,
    optimize: int,
    output_type: str,
    ensemble: bool,
    bg_removal: bool,
    mode: Optional[str],
    sidecar: Optional[str] = None,
) -> tuple[int, str]:
    """Process a single PDF chunk through ocrmypdf. Runs in a worker process."""
    import ocrmypdf as _ocrmypdf
    from . import ocrmypdf_rapidocr as _plugin

    _plugin.ENSEMBLE_MODE = ensemble
    _plugin.BACKGROUND_REMOVAL = bg_removal
    _ensure_ghostscript_on_path()

    ocr_kwargs: dict = dict(
        language=[language],
        deskew=deskew,
        clean=clean,
        mode=mode,
        optimize=optimize,
        output_type=output_type,
        plugins=[plugin_path],
        progress_bar=False,
        jobs=1,
    )
    if sidecar:
        ocr_kwargs["sidecar"] = sidecar

    try:
        result = _ocrmypdf.ocr(
            source_chunk,
            output_chunk,
            **ocr_kwargs,
        )
        return (result, output_chunk)
    except _ocrmypdf.PriorOcrFoundError:
        shutil.copy2(source_chunk, output_chunk)
        return (_ocrmypdf.ExitCode.already_done_ocr, output_chunk)
    except Exception as e:
        return (-1, str(e))


# ---------------------------------------------------------------------------
# Main converter
# ---------------------------------------------------------------------------

def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    use_subfolder: bool = True,
    overwrite: bool = False,
    deskew: bool = True,
    clean: bool = False,
    force_ocr: bool = False,
    optimize_level: int = 1,
    pdfa: bool = False,
    sidecar: bool = False,
    rag_sidecar: bool = False,
    bg_removal: bool = False,
    ensemble: bool = False,
    language: str = "eng",
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> ConversionOutput:
    """
    Convert a PDF to a Searchable PDF with an invisible OCR text layer.

    Returns a ConversionOutput for confidence reporting and logging.
    The actual PDF output is written directly by ocrmypdf.
    """
    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence
    output.engine_used = "ocrmypdf+rapidocr"
    if ensemble:
        output.engine_used = "ocrmypdf+ensemble (rapidocr+tesseract)"

    def log_info(msg):
        if logger:
            logger.info(msg)

    def log_warn(msg):
        if logger:
            logger.warning(msg)
        confidence.add_warning(msg)

    def progress(p):
        if progress_callback:
            progress_callback(p)

    log_info(f"Searchable PDF converter started | file={os.path.basename(source_file)}")
    progress(0.02)

    # --- Validate environment ---
    if not ocrmypdf_available():
        log_warn("ocrmypdf is not installed. Cannot create Searchable PDF.")
        confidence.overall = "Failed"
        output.add_section(body="*ocrmypdf is not installed. Install with: pip install ocrmypdf*")
        return output

    if not ghostscript_available():
        log_warn("Ghostscript is not installed. ocrmypdf requires Ghostscript.")
        confidence.overall = "Failed"
        output.add_section(
            body="*Ghostscript is not installed. Searchable PDF requires Ghostscript.*"
        )
        return output

    _ensure_ghostscript_on_path()

    # --- Validate input ---
    ext = os.path.splitext(source_file)[1].lower()
    if ext != ".pdf":
        log_warn(f"Searchable PDF only supports PDF input files (got {ext}).")
        confidence.overall = "Failed"
        output.add_section(
            body=f"*Searchable PDF output requires a PDF input file. Got: {ext}*"
        )
        return output

    progress(0.05)

    # --- Determine output path ---
    stem = alias if alias else _safe_stem(source_file)
    out_dir = output_dir_for(source_file, output_root, alias, use_subfolder)
    os.makedirs(out_dir, exist_ok=True)
    output_pdf = os.path.join(out_dir, stem + ".pdf")

    if not overwrite and os.path.exists(output_pdf):
        raise FileExistsError(f"Output file already exists: {output_pdf}")

    sidecar_path = None
    if sidecar:
        sidecar_path = os.path.join(out_dir, stem + "_sidecar.txt")

    log_info(f"Output: {output_pdf}")
    if sidecar_path:
        log_info(f"Sidecar text: {sidecar_path}")
    progress(0.08)

    # --- Set plugin flags ---
    from . import ocrmypdf_rapidocr as _plugin
    _plugin.ENSEMBLE_MODE = ensemble
    _plugin.BACKGROUND_REMOVAL = bg_removal

    if ensemble:
        log_info("Ensemble OCR enabled (RapidOCR + Tesseract)")
    if bg_removal:
        log_info("Background removal preprocessing enabled")

    # --- Check page count for auto-chunking ---
    page_count = _get_page_count(source_file)
    if page_count is not None:
        log_info(f"Page count: {page_count}")

    output_type = "pdfa" if pdfa else "pdf"
    ocr_mode = "force" if force_ocr else None

    plugin_path = os.path.join(os.path.dirname(__file__), "ocrmypdf_rapidocr.py")

    log_info(
        f"ocrmypdf settings | deskew={deskew} clean={clean} mode={ocr_mode} "
        f"optimize={optimize_level} output_type={output_type} language={language}"
    )
    progress(0.10)

    # --- Run ocrmypdf (auto-chunk if large) ---
    if page_count is not None and page_count > _CHUNK_THRESHOLD:
        log_info(f"Auto-chunking enabled ({page_count} pages > {_CHUNK_THRESHOLD})")
        _convert_chunked(
            source_file, output_pdf, plugin_path, language,
            deskew, clean, ocr_mode, optimize_level, output_type,
            sidecar_path, ensemble, bg_removal,
            page_count, confidence, log_info, log_warn, progress,
        )
    else:
        _convert_single(
            source_file, output_pdf, plugin_path, language,
            deskew, clean, ocr_mode, optimize_level, output_type,
            sidecar_path, confidence, log_info, log_warn, progress,
        )

    # --- Sidecar RAG ---
    if rag_sidecar and sidecar_path and os.path.isfile(sidecar_path):
        rag_path = os.path.join(out_dir, stem + "_rag.jsonl")
        _generate_rag_from_sidecar(sidecar_path, rag_path, source_file, confidence)
        log_info(f"RAG chunks: {rag_path}")

    output_size = os.path.getsize(output_pdf) if os.path.exists(output_pdf) else 0
    log_info(
        f"Searchable PDF created | size={output_size:,} bytes | "
        f"confidence={confidence.overall}"
    )
    progress(1.0)
    return output


# ---------------------------------------------------------------------------
# Single-document conversion (no chunking)
# ---------------------------------------------------------------------------

def _convert_single(
    source_file, output_pdf, plugin_path, language,
    deskew, clean, ocr_mode, optimize_level, output_type,
    sidecar_path, confidence, log_info, log_warn, progress,
):
    import ocrmypdf

    try:
        result = ocrmypdf.ocr(
            source_file,
            output_pdf,
            language=[language],
            deskew=deskew,
            clean=clean,
            mode=ocr_mode,
            optimize=optimize_level,
            output_type=output_type,
            sidecar=sidecar_path,
            plugins=[plugin_path],
            progress_bar=False,
            jobs=1,
        )
        progress(0.90)
        _populate_confidence(result, confidence, log_info, log_warn)

    except ocrmypdf.PriorOcrFoundError:
        log_info("PDF already contains OCR text. Use 'Force OCR' to re-process.")
        confidence.add_note("PDF already has an OCR text layer — no processing needed.")
        confidence.text_extraction = "High"
        confidence.ocr_confidence = "N/A"
        confidence.overall = "High"
        if source_file != output_pdf:
            shutil.copy2(source_file, output_pdf)

    except ocrmypdf.EncryptedPdfError:
        log_warn("PDF is encrypted. Cannot add OCR text layer.")
        confidence.overall = "Failed"

    except ocrmypdf.InputFileError as e:
        log_warn(f"ocrmypdf input error: {e}")
        confidence.overall = "Failed"

    except ocrmypdf.MissingDependencyError as e:
        log_warn(f"Missing dependency for ocrmypdf: {e}")
        confidence.overall = "Failed"

    except Exception as e:
        log_warn(f"ocrmypdf failed: {e}")
        confidence.overall = "Failed"


# ---------------------------------------------------------------------------
# Chunked conversion (parallel, for large documents)
# ---------------------------------------------------------------------------

def _get_page_count(source_file: str) -> Optional[int]:
    try:
        import pikepdf
        with pikepdf.open(source_file) as pdf:
            return len(pdf.pages)
    except Exception:
        return None


def _convert_chunked(
    source_file, output_pdf, plugin_path, language,
    deskew, clean, ocr_mode, optimize_level, output_type,
    sidecar_path, ensemble, bg_removal,
    page_count, confidence, log_info, log_warn, progress,
):
    import pikepdf
    from . import system_info

    info = system_info.detect_system()
    chunk_size = info.recommended_chunk_size

    num_chunks = (page_count + chunk_size - 1) // chunk_size
    max_workers = min(info.recommended_workers, num_chunks, 4)
    max_workers = max(1, max_workers)

    log_info(f"Splitting into {num_chunks} chunks of ~{chunk_size} pages, "
             f"{max_workers} parallel workers")

    tmp_dir = tempfile.mkdtemp(prefix="spdf_chunks_")
    chunk_inputs = []
    chunk_outputs = []

    try:
        # Split source PDF into chunks
        with pikepdf.open(source_file) as src_pdf:
            for i in range(num_chunks):
                start = i * chunk_size
                end = min(start + chunk_size, page_count)

                chunk_pdf = pikepdf.new()
                for pg_idx in range(start, end):
                    chunk_pdf.pages.append(src_pdf.pages[pg_idx])

                chunk_in = os.path.join(tmp_dir, f"chunk_{i:03d}_in.pdf")
                chunk_out = os.path.join(tmp_dir, f"chunk_{i:03d}_out.pdf")
                chunk_pdf.save(chunk_in)
                chunk_pdf.close()

                chunk_inputs.append(chunk_in)
                chunk_outputs.append(chunk_out)

        progress(0.15)
        log_info(f"Split complete: {num_chunks} chunks")

        # Process chunks in parallel
        completed = 0
        chunk_results = [None] * num_chunks
        sidecar_parts = [] if sidecar_path else None

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i in range(num_chunks):
                chunk_sidecar = os.path.join(tmp_dir, f"chunk_{i:03d}_sidecar.txt") if sidecar_path else None
                fut = executor.submit(
                    _process_chunk,
                    chunk_inputs[i],
                    chunk_outputs[i],
                    plugin_path,
                    language,
                    deskew,
                    clean,
                    optimize_level,
                    output_type,
                    ensemble,
                    bg_removal,
                    ocr_mode,
                    chunk_sidecar,
                )
                futures[fut] = i

            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    exit_code, result_path = fut.result()
                    chunk_results[idx] = exit_code
                    if exit_code == -1:
                        log_warn(f"Chunk {idx} failed: {result_path}")
                except Exception as e:
                    log_warn(f"Chunk {idx} worker error: {e}")
                    chunk_results[idx] = -1

                completed += 1
                progress(0.15 + 0.65 * (completed / num_chunks))

        progress(0.80)

        # Merge output chunks
        log_info("Merging output chunks...")
        merged = pikepdf.new()
        for chunk_out in chunk_outputs:
            if os.path.isfile(chunk_out):
                with pikepdf.open(chunk_out) as cpdf:
                    for page in cpdf.pages:
                        merged.pages.append(page)

        merged.save(output_pdf)
        merged.close()

        # Merge sidecar text files if requested
        if sidecar_path:
            sidecar_texts = []
            for i in range(num_chunks):
                sc = os.path.join(tmp_dir, f"chunk_{i:03d}_sidecar.txt")
                if os.path.isfile(sc):
                    sidecar_texts.append(Path(sc).read_text(encoding="utf-8"))
            if sidecar_texts:
                Path(sidecar_path).write_text(
                    "\f".join(sidecar_texts), encoding="utf-8"
                )

        progress(0.90)

        # Aggregate confidence
        _populate_chunked_confidence(chunk_results, confidence, log_info, log_warn)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Sidecar RAG generation
# ---------------------------------------------------------------------------

def _generate_rag_from_sidecar(
    sidecar_path: str,
    rag_path: str,
    source_file: str,
    confidence: ConfidenceResult,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> None:
    """Generate RAG JSONL chunks from sidecar text."""
    text = Path(sidecar_path).read_text(encoding="utf-8")
    pages = text.split("\f")

    stem = _safe_stem(source_file)
    source_name = os.path.basename(source_file)
    conf_level = confidence.overall or "N/A"

    chunks = []
    chunk_idx = 0

    for page_num, page_text in enumerate(pages, start=1):
        page_text = page_text.strip()
        if not page_text:
            continue

        words = page_text.split()
        if len(words) <= chunk_size:
            chunks.append(_make_rag_chunk(
                stem, chunk_idx, page_text, source_name,
                page_num, conf_level,
            ))
            chunk_idx += 1
        else:
            for wi in range(0, len(words), chunk_size - chunk_overlap):
                batch = words[wi:wi + chunk_size]
                if not batch:
                    break
                chunks.append(_make_rag_chunk(
                    stem, chunk_idx, " ".join(batch), source_name,
                    page_num, conf_level,
                ))
                chunk_idx += 1

    total = len(chunks)
    for ch in chunks:
        ch["metadata"]["total_chunks"] = total

    with open(rag_path, "w", encoding="utf-8") as fh:
        for ch in chunks:
            fh.write(json.dumps(ch, ensure_ascii=False) + "\n")


def _make_rag_chunk(stem, idx, text, source, page, confidence):
    return {
        "id": f"{stem}_chunk_{idx:04d}",
        "text": text,
        "metadata": {
            "source": source,
            "chunk_index": idx,
            "total_chunks": 0,
            "page": page,
            "confidence": confidence,
        },
    }


# ---------------------------------------------------------------------------
# Confidence population
# ---------------------------------------------------------------------------

def _populate_confidence(
    result, confidence: ConfidenceResult, log_info, log_warn,
) -> None:
    """Populate ConfidenceResult from ocrmypdf exit code."""
    import ocrmypdf

    if result == ocrmypdf.ExitCode.ok:
        confidence.text_extraction = "High"
        confidence.ocr_confidence = "High"
        confidence.overall = "High"
        confidence.add_note("Engine: ocrmypdf + RapidOCR (ONNX Runtime)")
        log_info("ocrmypdf completed successfully.")

    elif result == ocrmypdf.ExitCode.pdfa_conversion_failed:
        confidence.text_extraction = "High"
        confidence.ocr_confidence = "High"
        confidence.overall = "Medium"
        confidence.add_warning("PDF/A conversion failed but OCR text layer was added.")
        log_warn("PDF/A conversion failed. Output is a standard PDF with OCR layer.")

    elif result == ocrmypdf.ExitCode.already_done_ocr:
        confidence.text_extraction = "High"
        confidence.ocr_confidence = "N/A"
        confidence.overall = "High"
        confidence.add_note("PDF already had OCR text — no additional processing needed.")
        log_info("PDF already has OCR text layer.")

    elif result == ocrmypdf.ExitCode.some_pages_had_errors:
        confidence.text_extraction = "Medium"
        confidence.ocr_confidence = "Medium"
        confidence.overall = "Medium"
        confidence.manual_review_recommended = True
        confidence.add_warning("Some pages could not be OCR'd. Review the output.")
        log_warn("ocrmypdf: some pages had errors during OCR.")

    else:
        confidence.text_extraction = "Low"
        confidence.ocr_confidence = "Low"
        confidence.overall = "Low"
        confidence.manual_review_recommended = True
        confidence.add_warning(f"ocrmypdf returned exit code: {result}")
        log_warn(f"ocrmypdf returned unexpected exit code: {result}")

    confidence.table_structure = "N/A"
    confidence.document_order = "N/A"
    confidence.image_extraction = "N/A"
    confidence.image_placement = "N/A"


def _populate_chunked_confidence(
    chunk_results, confidence: ConfidenceResult, log_info, log_warn,
) -> None:
    """Aggregate confidence from multiple chunk results."""
    import ocrmypdf

    failed = sum(1 for r in chunk_results if r is None or r == -1)
    ok = sum(1 for r in chunk_results if r == ocrmypdf.ExitCode.ok)
    partial = sum(1 for r in chunk_results
                  if r == ocrmypdf.ExitCode.some_pages_had_errors)
    total = len(chunk_results)

    if failed == total:
        confidence.overall = "Failed"
        confidence.add_warning("All chunks failed processing.")
        log_warn("All chunks failed.")
    elif failed > 0 or partial > 0:
        confidence.text_extraction = "Medium"
        confidence.ocr_confidence = "Medium"
        confidence.overall = "Medium"
        confidence.manual_review_recommended = True
        confidence.add_warning(
            f"{ok}/{total} chunks OK, {partial} partial, {failed} failed."
        )
        log_warn(f"Chunked result: {ok} OK, {partial} partial, {failed} failed")
    else:
        confidence.text_extraction = "High"
        confidence.ocr_confidence = "High"
        confidence.overall = "High"
        confidence.add_note(
            f"All {total} chunks processed successfully. "
            f"Engine: ocrmypdf + RapidOCR (ONNX Runtime)"
        )
        log_info(f"All {total} chunks completed successfully.")

    confidence.table_structure = "N/A"
    confidence.document_order = "N/A"
    confidence.image_extraction = "N/A"
    confidence.image_placement = "N/A"
