"""
ocrmypdf plugin that provides RapidOCR as the OCR engine.

Routes OCR through ONNX Runtime instead of Tesseract, enabling GPU
acceleration via CUDA (NVIDIA), DirectML (AMD/Intel on Windows),
CoreML (macOS), or CPU fallback.

Supports ensemble mode (RapidOCR + Tesseract merged by confidence)
and background removal preprocessing for colored/noisy scans.

Usage with ocrmypdf Python API:
    from app.engine import ocrmypdf_rapidocr
    ocrmypdf.ocr(input_pdf, output_pdf, plugins=[ocrmypdf_rapidocr])
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Set

import ocrmypdf

log = logging.getLogger(__name__)

# Module-level flags — set by searchable_pdf.py before calling ocrmypdf.ocr()
ENSEMBLE_MODE = False
BACKGROUND_REMOVAL = False


@ocrmypdf.hookimpl
def get_ocr_engine(options=None):
    return RapidOcrEngine()


class RapidOcrEngine(ocrmypdf.OcrEngine):

    @staticmethod
    def version() -> str:
        try:
            from importlib.metadata import version as pkg_version
            return pkg_version("rapidocr-onnxruntime")
        except Exception:
            return "unknown"

    @staticmethod
    def creator_tag(options) -> str:
        tag = f"RapidOCR (ONNX Runtime) {RapidOcrEngine.version()}"
        if ENSEMBLE_MODE:
            tag += " + Tesseract (ensemble)"
        return tag

    def __str__(self) -> str:
        return f"RapidOCR {self.version()}"

    @staticmethod
    def languages(options) -> Set[str]:
        return {
            "eng", "fra", "deu", "spa", "ita", "por", "nld",
            "chi_sim", "chi_tra", "jpn", "kor", "ara", "rus",
        }

    @staticmethod
    def get_orientation(
        input_file: Path, options,
    ) -> ocrmypdf.OrientationConfidence:
        return ocrmypdf.OrientationConfidence(angle=0, confidence=0.0)

    @staticmethod
    def generate_hocr(
        input_file: Path,
        output_hocr: Path,
        output_text: Path,
        options,
    ) -> None:
        from PIL import Image
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR

        img = Image.open(input_file)
        width, height = img.size
        img_array = np.array(img.convert("RGB"))

        if BACKGROUND_REMOVAL:
            img_array = _remove_background(img_array)

        engine = RapidOCR()
        raw, _ = engine(img_array)

        if ENSEMBLE_MODE:
            word_elements, lines_text = _generate_ensemble_hocr(
                img, img_array, raw, width, height,
            )
        else:
            word_elements, lines_text = _generate_rapidocr_hocr(
                raw, width, height,
            )

        hocr = _build_hocr(width, height, word_elements)
        output_hocr.write_text(hocr, encoding="utf-8")
        output_text.write_text("\n".join(lines_text), encoding="utf-8")

    @staticmethod
    def generate_pdf(
        input_file: Path,
        output_pdf: Path,
        output_text: Path,
        options,
    ) -> None:
        raise NotImplementedError("Use generate_hocr instead")


# ---------------------------------------------------------------------------
# RapidOCR-only hOCR generation (default path)
# ---------------------------------------------------------------------------

def _generate_rapidocr_hocr(raw, width, height):
    lines_text = []
    word_elements = []
    word_id = 0

    if raw:
        for item in raw:
            if not item or len(item) < 3:
                continue
            bbox = item[0]
            text = str(item[1]).strip()
            conf = float(item[2])
            if not text:
                continue
            if not (0.0 <= conf <= 1.0):
                conf = 0.5

            bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else list(bbox)
            left = max(0, int(min(p[0] for p in bbox_list)))
            top = max(0, int(min(p[1] for p in bbox_list)))
            right = min(width, int(max(p[0] for p in bbox_list)))
            bottom = min(height, int(max(p[1] for p in bbox_list)))

            if right <= left or bottom <= top:
                continue

            wconf = int(conf * 100)
            word_id += 1
            word_elements.append(
                f'       <span class="ocrx_word" id="word_{word_id}" '
                f'title="bbox {left} {top} {right} {bottom}; '
                f'x_wconf {wconf}">{_hocr_escape(text)}</span>'
            )
            lines_text.append(text)

    return word_elements, lines_text


# ---------------------------------------------------------------------------
# Ensemble hOCR generation (RapidOCR + Tesseract merged)
# ---------------------------------------------------------------------------

def _generate_ensemble_hocr(img, img_array, rapid_raw, width, height):
    from .ocr_ensemble import WordBox, normalize_bbox, merge_word_results

    rapid_words = []
    if rapid_raw:
        for item in rapid_raw:
            if not item or len(item) < 3:
                continue
            bbox = item[0]
            text = str(item[1]).strip()
            conf = float(item[2])
            if not text:
                continue
            if not (0.0 <= conf <= 1.0):
                conf = 0.5
            try:
                l, t, r, b = normalize_bbox(bbox)
            except (ValueError, IndexError):
                continue
            rapid_words.append(WordBox(
                text=text, confidence=conf,
                left=l, top=t, right=r, bottom=b, engine="rapidocr",
            ))

    tess_words = _run_tesseract_words(img)

    merged = merge_word_results(rapid_words, tess_words)

    word_elements = []
    lines_text = []
    word_id = 0

    for w in merged:
        left = max(0, int(w.left))
        top = max(0, int(w.top))
        right = min(width, int(w.right))
        bottom = min(height, int(w.bottom))
        if right <= left or bottom <= top:
            continue

        wconf = int(w.confidence * 100)
        word_id += 1
        word_elements.append(
            f'       <span class="ocrx_word" id="word_{word_id}" '
            f'title="bbox {left} {top} {right} {bottom}; '
            f'x_wconf {wconf}">{_hocr_escape(w.text)}</span>'
        )
        lines_text.append(w.text)

    return word_elements, lines_text


def _run_tesseract_words(img):
    """Run Tesseract on a PIL image and return WordBox list."""
    from .ocr_ensemble import WordBox
    try:
        import pytesseract
        data = pytesseract.image_to_data(
            img, output_type=pytesseract.Output.DICT,
        )
        words = []
        for i, word in enumerate(data["text"]):
            if not word.strip():
                continue
            conf = float(data["conf"][i])
            if conf < 0:
                continue
            left = float(data["left"][i])
            top_val = float(data["top"][i])
            w = float(data["width"][i])
            h = float(data["height"][i])
            words.append(WordBox(
                text=word, confidence=conf / 100.0,
                left=left, top=top_val, right=left + w, bottom=top_val + h,
                engine="tesseract",
            ))
        return words
    except Exception as e:
        log.warning("Tesseract unavailable for ensemble: %s", e)
        return []


# ---------------------------------------------------------------------------
# Background removal preprocessing
# ---------------------------------------------------------------------------

def _remove_background(img_array):
    """Remove colored backgrounds from a scan using adaptive thresholding."""
    import cv2
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=25, C=10,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
    result = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2RGB)
    return result


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _hocr_escape(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _build_hocr(page_width: int, page_height: int, word_elements: list[str]) -> str:
    words_block = "\n".join(word_elements)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<!DOCTYPE html PUBLIC "
        '"-//W3C//DTD XHTML 1.0 Transitional//EN"\n'
        '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">\n'
        "<head>\n"
        '  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n'
        "  <title>RapidOCR Output</title>\n"
        "</head>\n"
        "<body>\n"
        f'  <div class="ocr_page" id="page_1" '
        f'title="bbox 0 0 {page_width} {page_height}">\n'
        f'    <div class="ocr_carea" id="block_1" '
        f'title="bbox 0 0 {page_width} {page_height}">\n'
        f'      <p class="ocr_par" id="par_1">\n'
        f"{words_block}\n"
        f"      </p>\n"
        f"    </div>\n"
        f"  </div>\n"
        "</body>\n"
        "</html>\n"
    )
