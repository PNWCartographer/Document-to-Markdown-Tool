"""
Image converter.

Pipeline:
  1. Load image with Pillow
  2. Save ORIGINAL image to assets/ (full color, for Markdown output)
  3. Preprocess with OpenCV for OCR (inversion, upscale, CLAHE, denoise,
     deskew, threshold) — used only as OCR input, not saved
  4. Run OCR via ocr_engine (RapidOCR primary, Tesseract fallback)
  5. Detect language of OCR'd text
  6. Translate non-English text if possible (offline via Argos Translate)
  7. Produce ConversionOutput with original image + spatially-sorted
     extracted text + translation table

Handles: .png .jpg .jpeg .bmp .tiff .tif .webp .gif
"""

import os
import re
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput, rows_to_markdown_table
from .logger import ConversionLogger
from . import ocr_engine
from . import language_tools

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp", ".gif"}


def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    language: str = "en",
    preserve_images: bool = True,
    use_subfolder: bool = True,
    auto_translate: bool = True,
    prefer_engine: str = "rapidocr",
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
    pil_image = None
    try:
        from PIL import Image
        pil_image = Image.open(source_file)
        pil_image.load()
        log_info(f"Loaded image | size={pil_image.size} mode={pil_image.mode}")
    except Exception as e:
        log_warn(f"Pillow failed to open image: {e}")
        if pil_image is not None:
            pil_image.close()
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        return output

    progress(0.15)

    # ------------------------------------------------------------------
    # 2. Save ORIGINAL image to assets (full color, for output)
    # ------------------------------------------------------------------
    asset_rel_path = None
    if preserve_images and output_root:
        asset_rel_path = _save_original_asset(
            pil_image, source_file, alias, output_root, logger, use_subfolder)
        if asset_rel_path:
            output.asset_paths.append(asset_rel_path)

    progress(0.25)

    # ------------------------------------------------------------------
    # 3. Preprocess for OCR (used as OCR input only, not saved)
    # ------------------------------------------------------------------
    processed_pil = _preprocess(pil_image, logger)
    progress(0.40)

    # ------------------------------------------------------------------
    # 4. OCR
    # ------------------------------------------------------------------
    stem = alias if alias else os.path.splitext(os.path.basename(source_file))[0]

    if not ocr_engine.any_ocr_available():
        log_warn("No OCR engine available. Image saved without text extraction.")
        if processed_pil is not pil_image:
            processed_pil.close()
        pil_image.close()
        confidence.text_extraction = "N/A"
        confidence.ocr_confidence = "N/A"
        _build_image_only_section(output, stem, asset_rel_path)
        _finalize_confidence(confidence, "N/A")
        progress(1.0)
        return output

    log_info("Running OCR...")
    ocr_result = ocr_engine.run_ocr(processed_pil, language=language,
                                     prefer_engine=prefer_engine)
    log_info(f"OCR complete | engine={ocr_result.engine_used} "
             f"confidence={ocr_result.confidence_label} "
             f"regions={len(ocr_result.regions)}")
    if processed_pil is not pil_image:
        processed_pil.close()
    progress(0.70)

    # ------------------------------------------------------------------
    # 5. Language detection + translation
    # ------------------------------------------------------------------
    detected_lang = language
    translation_pairs = []

    extracted_text = ocr_result.text_sorted_spatially()

    if extracted_text.strip() and language_tools.langdetect_available():
        detected_lang, lang_score = language_tools.detect_language(
            extracted_text, fallback=language)
        if detected_lang != language and lang_score > 0.5:
            lang_name = language_tools.language_name(detected_lang)
            log_info(f"Language detected: {lang_name} ({detected_lang}) "
                     f"confidence={lang_score:.2f}")

            # Attempt translation to English (if enabled)
            if detected_lang != "en" and auto_translate and language_tools.argos_available():
                log_info(f"Translating {lang_name} → English (offline)...")
                translation_pairs = language_tools.translate_lines(
                    ocr_result.lines, detected_lang, "en",
                    auto_install=True)
                translated_count = sum(1 for _, t in translation_pairs if t)
                log_info(f"Translated {translated_count}/{len(translation_pairs)} lines")
            elif detected_lang != "en" and auto_translate:
                log_info("Argos Translate not available — preserving original text")
            elif detected_lang != "en":
                log_info("Auto-translate disabled — preserving original text")

    progress(0.85)

    # ------------------------------------------------------------------
    # 6. Assemble Markdown section
    # ------------------------------------------------------------------
    _build_section(output, stem, asset_rel_path, ocr_result, source_file,
                   detected_lang=detected_lang, translation_pairs=translation_pairs)
    _finalize_confidence(confidence, ocr_result.confidence_label)
    confidence.derive_overall()
    pil_image.close()
    progress(1.0)
    log_info("Image conversion complete.")
    return output


# ---------------------------------------------------------------------------
# Preprocessing
# ---------------------------------------------------------------------------

def _preprocess(pil_image, logger):
    """
    Apply enhanced OpenCV preprocessing for OCR.

    Pipeline:
      1. Color inversion check (white-on-dark → dark-on-white)
      2. Upscale small images (< 1000px) via Lanczos for OCR legibility
      3. Grayscale conversion
      4. CLAHE contrast enhancement (helps faded scans, colored backgrounds)
      5. Denoise
      6. Deskew
      7. Adaptive threshold

    Returns a PIL Image. Falls back to the original if OpenCV is unavailable.
    The returned image is used ONLY for OCR input — the original full-color
    image is saved separately for Markdown output.
    """
    try:
        import cv2
        import numpy as np
        from PIL import Image

        img = np.array(pil_image.convert("RGB"))

        # 1. Color inversion — detect white-on-dark drawings
        gray_check = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        mean_intensity = np.mean(gray_check)
        if mean_intensity < 127:
            img = cv2.bitwise_not(img)
            if logger:
                logger.info("Dark background detected — inverted colors for OCR.")

        # 2. Upscale small images for better OCR on tiny text
        h, w = img.shape[:2]
        if max(h, w) < 1000:
            scale = 2.0
            img = cv2.resize(img, None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_LANCZOS4)
            if logger:
                logger.info(f"Upscaled small image 2x for OCR ({w}x{h} → {img.shape[1]}x{img.shape[0]})")

        # 3. Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # 4. CLAHE contrast enhancement — improves text-background contrast
        #    on engineering drawings with colored backgrounds or faded scans
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 5. Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

        # 6. Deskew
        deskewed = _deskew(denoised)

        # 7. Adaptive threshold
        block_size = 31
        # Scale block size for high-res images to maintain effectiveness
        if deskewed.shape[0] > 3000 or deskewed.shape[1] > 3000:
            block_size = 51
        thresh = cv2.adaptiveThreshold(
            deskewed, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, 2
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
    try:
        import cv2
        import numpy as np
    except ImportError:
        return gray_array

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

def _save_original_asset(pil_image, source_file: str, alias: str, output_root: str, logger, use_subfolder: bool = True) -> Optional[str]:
    """
    Save the ORIGINAL full-color image to assets/ as PNG.

    This preserves graphical fidelity — wire colors, layer
    differentiation, component highlighting are all retained.
    The preprocessed (binarized) version is used for OCR only.
    """
    from .markdown_writer import assets_dir_for, assets_rel_prefix_for

    try:
        assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
        os.makedirs(assets_dir, exist_ok=True)

        stem = re.sub(r'[<>:"/\\|?*]', "_", os.path.splitext(os.path.basename(source_file))[0])
        asset_filename = f"{stem}.png"
        asset_path = os.path.join(assets_dir, asset_filename)

        # Save as PNG (lossless) to preserve line sharpness in drawings
        pil_image.save(asset_path, format="PNG")

        prefix = assets_rel_prefix_for(source_file, alias, use_subfolder)
        rel_path = f"{prefix}{asset_filename}"
        if logger:
            logger.info(f"Original image saved | path={asset_path}")
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
    detected_lang: str = "en",
    translation_pairs: list = None,
) -> None:
    parts = [f"## {stem}", ""]

    if asset_rel_path:
        parts.append(f"![{stem}]({asset_rel_path})")
        parts.append("")

    # Use spatially-sorted text for better reading order
    sorted_text = ocr_result.text_sorted_spatially()

    has_translation = translation_pairs and any(t for _, t in translation_pairs)

    if has_translation:
        # Show side-by-side original + translated text as a table
        lang_name = language_tools.language_name(detected_lang)
        parts.append(f"### Extracted Text (Original: {lang_name})")
        parts.append("")

        rows = []
        for original, translated in translation_pairs:
            if original.strip():
                rows.append([original.strip(), translated or "—"])
        if rows:
            table_md = rows_to_markdown_table(
                ["Original", "Translation (English)"], rows)
            parts.append(table_md)
            parts.append("")
            parts.append(f"*Translation: Argos Translate (offline) — "
                         f"review recommended for technical accuracy.*")
        parts.append("")

    elif sorted_text.strip():
        # No translation needed or available — show extracted text
        if detected_lang != "en":
            lang_name = language_tools.language_name(detected_lang)
            parts.append(f"### Extracted Text (Language: {lang_name})")
            parts.append("")
            parts.append("*Original text preserved — manual translation "
                         "may be needed.*")
        else:
            parts.append("### Extracted Text")
        parts.append("")
        parts.append(sorted_text.strip())
        parts.append("")

    parts.append(f"*OCR Engine: {ocr_result.engine_used} | "
                 f"Confidence: {ocr_result.confidence_label}*")

    if ocr_result.confidence_label in ("Low", "Failed"):
        parts.append("*Manual review recommended for rotated or small text.*")

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
