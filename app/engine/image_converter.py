"""
Image converter.

Pipeline:
  1. Load image with Pillow
  2. Preprocess with OpenCV (deskew, denoise, contrast normalization)
  3. Run OCR via ocr_engine (PaddleOCR primary, Tesseract fallback)
  4. Save preprocessed image to assets/
  5. Produce ConversionOutput with image reference + extracted text

Handles: .png .jpg .jpeg .bmp .tiff .tif .webp .gif
"""

import os
import re
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput
from .logger import ConversionLogger
from . import ocr_engine

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    language: str = "en",
    preserve_images: bool = True,
    use_subfolder: bool = True,
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> ConversionOutput:
    """
    Convert an image file to a ConversionOutput.

    Parameters
    ----------
    source_file : str
        Absolute path to the image file.
    output_root : str
        Root output folder — used to compute the assets/ path for saving the image.
    language : str
        OCR language code.
    preserve_images : bool
        When True, the preprocessed image is saved to assets/ and linked in Markdown.
    """
    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence
    output.engine_used = "pillow+opencv+ocr"

    def log_info(msg):
        if logger: logger.info(msg)
    def log_warn(msg):
        if logger: logger.warning(msg)
        confidence.add_warning(msg)
    def progress(p):
        if progress_callback: progress_callback(p)

    log_info(f"Image converter started | file={os.path.basename(source_file)}")
    progress(0.05)

    # ------------------------------------------------------------------
    # 1. Load image
    # ------------------------------------------------------------------
    try:
        from PIL import Image
        pil_image = Image.open(source_file)
        pil_image.load()
        log_info(f"Loaded image | size={pil_image.size} mode={pil_image.mode}")
    except Exception as e:
        log_warn(f"Pillow failed to open image: {e}")
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        return output

    progress(0.15)

    # ------------------------------------------------------------------
    # 2. Preprocess with OpenCV
    # ------------------------------------------------------------------
    processed_pil = _preprocess(pil_image, logger)
    progress(0.35)

    # ------------------------------------------------------------------
    # 3. Save preprocessed image to assets/
    # ------------------------------------------------------------------
    asset_rel_path = None
    if preserve_images and output_root:
        asset_rel_path = _save_asset(processed_pil, source_file, alias, output_root, logger, use_subfolder)
        if asset_rel_path:
            output.asset_paths.append(asset_rel_path)

    progress(0.45)

    # ------------------------------------------------------------------
    # 4. OCR
    # ------------------------------------------------------------------
    stem = alias if alias else os.path.splitext(os.path.basename(source_file))[0]

    if not ocr_engine.any_ocr_available():
        log_warn("No OCR engine available. Image saved without text extraction.")
        confidence.text_extraction = "N/A"
        confidence.ocr_confidence = "N/A"
        _build_image_only_section(output, stem, asset_rel_path)
        _finalize_confidence(confidence, "N/A")
        progress(1.0)
        return output

    log_info("Running OCR...")
    ocr_result = ocr_engine.run_ocr(processed_pil, language=language)
    log_info(f"OCR complete | engine={ocr_result.engine_used} confidence={ocr_result.confidence_label}")
    progress(0.85)

    # ------------------------------------------------------------------
    # 5. Assemble Markdown section
    # ------------------------------------------------------------------
    _build_section(output, stem, asset_rel_path, ocr_result, source_file)
    _finalize_confidence(confidence, ocr_result.confidence_label)
    confidence.derive_overall()
    progress(1.0)
    log_info("Image conversion complete.")
    return output


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _preprocess(pil_image, logger):
    """
    Apply OpenCV preprocessing: grayscale, denoise, deskew, threshold.
    Returns a PIL Image. Falls back to the original if OpenCV is unavailable.
    """
    try:
        import cv2
        import numpy as np
        from PIL import Image

        img = np.array(pil_image.convert("RGB"))
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=10)

        # Deskew
        deskewed = _deskew(denoised)

        # Adaptive threshold — improves OCR on low-contrast or uneven backgrounds
        thresh = cv2.adaptiveThreshold(
            deskewed, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 2
        )

        return Image.fromarray(thresh)

    except ImportError:
        if logger:
            logger.info("OpenCV not available — skipping preprocessing.")
        return pil_image
    except Exception as e:
        if logger:
            logger.warning(f"OpenCV preprocessing failed: {e} — using original image.")
        return pil_image


def _deskew(gray_array):
    """Correct image skew using OpenCV moments."""
    import cv2
    import numpy as np

    try:
        coords = np.column_stack(np.where(gray_array < 128))
        if len(coords) < 10:
            return gray_array
        angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5:
            return gray_array
        (h, w) = gray_array.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            gray_array, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception:
        return gray_array


# ---------------------------------------------------------------------------
# Asset saving
# ---------------------------------------------------------------------------

def _save_asset(pil_image, source_file: str, alias: str, output_root: str, logger, use_subfolder: bool = True) -> Optional[str]:
    """
    Save the processed image to assets/ and return the relative path for Markdown linking.
    """
    from .markdown_writer import assets_dir_for

    try:
        assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
        os.makedirs(assets_dir, exist_ok=True)

        stem = re.sub(r'[<>:"/\\|?*]', "_", os.path.splitext(os.path.basename(source_file))[0])
        asset_filename = f"{stem}_processed.png"
        asset_path = os.path.join(assets_dir, asset_filename)

        pil_image.save(asset_path, format="PNG")

        # Return relative path from the .md file location (sibling of assets/)
        rel_path = f"assets/{asset_filename}"
        if logger:
            logger.info(f"Image saved | path={asset_path}")
        return rel_path

    except Exception as e:
        if logger:
            logger.warning(f"Could not save image asset: {e}")
        return None


# ---------------------------------------------------------------------------
# Section assembly
# ---------------------------------------------------------------------------

def _build_image_only_section(output: ConversionOutput, stem: str, asset_rel_path: Optional[str]) -> None:
    parts = [f"## {stem}", ""]
    if asset_rel_path:
        parts.append(f"![{stem}]({asset_rel_path})")
    else:
        parts.append("*[Image could not be saved]*")
    parts += ["", "*OCR not available — no text extracted.*"]
    output.add_section(body="\n".join(parts))


def _build_section(
    output: ConversionOutput,
    stem: str,
    asset_rel_path: Optional[str],
    ocr_result,
    source_file: str,
) -> None:
    parts = [f"## {stem}", ""]

    if asset_rel_path:
        parts.append(f"![{stem}]({asset_rel_path})")
        parts.append("")

    if ocr_result.text.strip():
        parts += ["### Extracted Text", "", ocr_result.text.strip(), ""]

    parts.append(f"*Confidence: {ocr_result.confidence_label}*")

    if ocr_result.confidence_label in ("Low", "Failed"):
        parts.append("*Manual review recommended.*")

    output.add_section(body="\n".join(parts))


def _finalize_confidence(confidence: ConfidenceResult, ocr_label: str) -> None:
    confidence.ocr_confidence = ocr_label
    confidence.text_extraction = ocr_label if ocr_label != "N/A" else "N/A"
    confidence.table_structure = "N/A"
    confidence.document_order = "N/A"

    if ocr_label == "N/A":
        confidence.image_extraction = "High"
        confidence.image_placement = "High"
    elif ocr_label == "Failed":
        confidence.image_extraction = "High"
        confidence.image_placement = "High"
        confidence.add_warning("OCR failed — text could not be extracted from image.")
    else:
        confidence.image_extraction = "High"
        confidence.image_placement = "High"
        if ocr_label == "Low":
            confidence.add_warning("Low OCR confidence — extracted text may contain errors.")
