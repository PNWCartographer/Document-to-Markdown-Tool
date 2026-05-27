"""
Searchable PDF converter.

Takes a scanned or image-based PDF and adds an invisible OCR text layer
using ocrmypdf, making it full-text searchable, copyable, and accessible.
The original visual appearance is preserved.

Uses a custom RapidOCR plugin to route OCR through ONNX Runtime instead
of Tesseract, enabling GPU acceleration on all platforms.

This module bypasses the normal text-extraction → text-writing pipeline.
The output is a PDF file written directly by ocrmypdf.
"""

import os
import shutil
import sys
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
    except ImportError:
        return False


def is_available() -> bool:
    """Check if the Searchable PDF pipeline is fully available."""
    return ocrmypdf_available() and ghostscript_available()


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

    # --- Run ocrmypdf ---
    import ocrmypdf

    # Plugin path — ocrmypdf needs a file path or importable module name
    plugin_path = os.path.join(os.path.dirname(__file__), "ocrmypdf_rapidocr.py")

    output_type = "pdfa" if pdfa else "pdf"

    # ocrmypdf v17: force_ocr is legacy, use mode= instead
    if force_ocr:
        ocr_mode = "force"
    else:
        ocr_mode = None  # default: skip pages that already have text

    log_info(
        f"ocrmypdf settings | deskew={deskew} clean={clean} mode={ocr_mode} "
        f"optimize={optimize_level} output_type={output_type} language={language}"
    )
    progress(0.10)

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

        # Copy input to output since no processing was needed
        if source_file != output_pdf:
            shutil.copy2(source_file, output_pdf)

    except ocrmypdf.EncryptedPdfError:
        log_warn("PDF is encrypted. Cannot add OCR text layer.")
        confidence.overall = "Failed"
        output.add_section(
            body="*PDF is encrypted. Remove password protection and try again.*"
        )
        return output

    except ocrmypdf.InputFileError as e:
        log_warn(f"ocrmypdf input error: {e}")
        confidence.overall = "Failed"
        output.add_section(body=f"*Input file error: {e}*")
        return output

    except ocrmypdf.MissingDependencyError as e:
        log_warn(f"Missing dependency for ocrmypdf: {e}")
        confidence.overall = "Failed"
        output.add_section(body=f"*Missing dependency: {e}*")
        return output

    except Exception as e:
        log_warn(f"ocrmypdf failed: {e}")
        confidence.overall = "Failed"
        output.add_section(body=f"*Searchable PDF creation failed: {e}*")
        return output

    output_size = os.path.getsize(output_pdf) if os.path.exists(output_pdf) else 0
    log_info(
        f"Searchable PDF created | size={output_size:,} bytes | "
        f"confidence={confidence.overall}"
    )
    progress(1.0)
    return output


# ---------------------------------------------------------------------------
# Confidence population from ocrmypdf result
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
