"""
OCR abstraction layer.

Primary:  RapidOCR  (ONNX Runtime, Apache 2.0 — runs PaddleOCR models via ONNX)
Fallback: pytesseract + Tesseract binary

Both paths accept a PIL Image and return an OcrResult with extracted text,
per-line confidence scores, and an aggregate confidence label.

Lazy imports — neither engine is loaded until first use. This avoids slow
startup times and allows the tool to run without OCR dependencies installed
(converters will call is_available() before attempting OCR).
"""

import os
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Tesseract binary discovery — check common install paths and PATH
# before pytesseract is imported so the env var is set early.
# ---------------------------------------------------------------------------
_TESSERACT_SEARCH_PATHS = [
    # Windows
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "Tesseract-OCR", "tesseract.exe"),
    # Linux
    "/usr/bin/tesseract",
    "/usr/local/bin/tesseract",
    # macOS (Homebrew Intel + Apple Silicon)
    "/usr/local/bin/tesseract",
    "/opt/homebrew/bin/tesseract",
]

def _configure_tesseract() -> None:
    """Set pytesseract.tesseract_cmd to the first found binary."""
    import shutil
    # Already on PATH — nothing to do
    if shutil.which("tesseract"):
        return
    for path in _TESSERACT_SEARCH_PATHS:
        if os.path.isfile(path):
            try:
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = path
            except ImportError:
                pass
            return

_configure_tesseract()

# Cached engine instances (initialized once per process)
_rapidocr_engine = None
_rapidocr_available: Optional[bool] = None
_tesseract_available: Optional[bool] = None


@dataclass
class OcrTextRegion:
    """A single detected text region with spatial info."""
    text: str = ""
    confidence: float = 0.0
    # Bounding box: list of 4 (x, y) points (polygon vertices)
    bbox: list = field(default_factory=list)
    # Centroid for spatial sorting
    cx: float = 0.0
    cy: float = 0.0


@dataclass
class OcrResult:
    text: str = ""
    lines: list[str] = field(default_factory=list)
    confidences: list[float] = field(default_factory=list)  # 0.0–1.0 per line
    regions: list[OcrTextRegion] = field(default_factory=list)  # spatial data
    engine_used: str = ""
    confidence_label: str = "N/A"   # High | Medium | Low | Failed

    def aggregate_confidence(self) -> None:
        """Derive confidence_label from per-line confidence scores."""
        if not self.confidences:
            self.confidence_label = "Low" if self.text.strip() else "Failed"
            return
        avg = sum(self.confidences) / len(self.confidences)
        if avg >= 0.85:
            self.confidence_label = "High"
        elif avg >= 0.65:
            self.confidence_label = "Medium"
        elif avg > 0.0:
            self.confidence_label = "Low"
        else:
            self.confidence_label = "Failed"

    def text_sorted_spatially(self) -> str:
        """Return text sorted top-to-bottom, left-to-right by region centroid."""
        if not self.regions:
            return self.text
        sorted_regions = sorted(self.regions, key=lambda r: (r.cy, r.cx))
        return "\n".join(r.text for r in sorted_regions if r.text.strip())


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------

def rapidocr_available() -> bool:
    """Check if RapidOCR (ONNX Runtime) is installed and importable."""
    global _rapidocr_available
    if _rapidocr_available is not None:
        return _rapidocr_available
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        _rapidocr_available = True
    except Exception:
        _rapidocr_available = False
    return _rapidocr_available


def tesseract_available() -> bool:
    global _tesseract_available
    if _tesseract_available is not None:
        return _tesseract_available
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        _tesseract_available = True
    except Exception:
        _tesseract_available = False
    return _tesseract_available


def any_ocr_available() -> bool:
    return rapidocr_available() or tesseract_available()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_ocr(
    image,                      # PIL.Image.Image
    language: str = "en",
    prefer_engine: str = "rapidocr",
) -> OcrResult:
    """
    Run OCR on a PIL Image.

    Parameters
    ----------
    image : PIL.Image.Image
    language : str
        Language code. "en" for English. RapidOCR uses PaddleOCR model
        codes; Tesseract uses ISO 639-2 (e.g. "eng"). This function
        translates internally.
    prefer_engine : str
        "rapidocr", "tesseract", or legacy "paddle" (mapped to "rapidocr").
        Falls back to the other engine if the preferred one is unavailable.
    """
    # Map legacy "paddle" preference to "rapidocr"
    if prefer_engine == "paddle":
        prefer_engine = "rapidocr"

    if prefer_engine == "ensemble":
        if rapidocr_available() and tesseract_available():
            return _run_ensemble(image, language)
        # Fall through to single-engine if only one is available

    if prefer_engine == "rapidocr" and rapidocr_available():
        return _run_rapidocr(image, language)
    if prefer_engine == "tesseract" and tesseract_available():
        return _run_tesseract(image, language)

    # Preferred engine unavailable — try the other
    if rapidocr_available():
        return _run_rapidocr(image, language)
    if tesseract_available():
        return _run_tesseract(image, language)

    result = OcrResult(engine_used="none", confidence_label="Failed")
    result.text = "[OCR unavailable — install RapidOCR or Tesseract]"
    return result


# ---------------------------------------------------------------------------
# RapidOCR engine (replaces PaddleOCR)
# ---------------------------------------------------------------------------

_rapidocr_lock = __import__("threading").Lock()


def _get_rapidocr_engine():
    """Lazy-initialize the RapidOCR engine (one instance per process)."""
    global _rapidocr_engine
    with _rapidocr_lock:
        if _rapidocr_engine is None:
            from rapidocr_onnxruntime import RapidOCR
            _rapidocr_engine = RapidOCR()
        return _rapidocr_engine


def _run_rapidocr(image, language: str) -> OcrResult:
    """Run OCR using RapidOCR (ONNX Runtime backend)."""
    import numpy as np

    result = OcrResult(engine_used="rapidocr")
    try:
        engine = _get_rapidocr_engine()
        img_array = np.array(image.convert("RGB"))

        # RapidOCR inference — hold the lock for thread safety.
        with _rapidocr_lock:
            raw, _elapse = engine(img_array)

        lines = []
        confidences = []
        regions = []

        if raw:
            for item in raw:
                # Each item: [bbox_ndarray, text_str, confidence_float]
                if not item or len(item) < 3:
                    continue
                bbox = item[0]      # ndarray or list of 4 [x,y] points
                text = str(item[1])
                conf = float(item[2])

                # Guard against NaN or out-of-range confidence
                if not (0.0 <= conf <= 1.0):
                    conf = 0.5

                if text.strip():
                    lines.append(text)
                    confidences.append(conf)

                    # Convert bbox to list of [x,y] pairs for OcrTextRegion
                    bbox_list = bbox.tolist() if hasattr(bbox, "tolist") else list(bbox)
                    cx = sum(p[0] for p in bbox_list) / len(bbox_list) if bbox_list else 0
                    cy = sum(p[1] for p in bbox_list) / len(bbox_list) if bbox_list else 0
                    regions.append(OcrTextRegion(
                        text=text, confidence=conf,
                        bbox=bbox_list, cx=cx, cy=cy,
                    ))

        result.lines = lines
        result.confidences = confidences
        result.regions = regions
        result.text = "\n".join(lines)
        result.aggregate_confidence()

    except Exception as e:
        result.text = f"[RapidOCR error: {e}]"
        result.confidence_label = "Failed"

    return result


# ---------------------------------------------------------------------------
# Tesseract fallback
# ---------------------------------------------------------------------------

_TESSERACT_LANG_MAP = {
    "en": "eng",
    "fr": "fra",
    "de": "deu",
    "es": "spa",
    "it": "ita",
    "pt": "por",
    "zh": "chi_sim",
    "ja": "jpn",
    "ko": "kor",
    "ar": "ara",
    "ru": "rus",
}


def _run_tesseract(image, language: str) -> OcrResult:
    import pytesseract

    result = OcrResult(engine_used="tesseract")
    lang = _TESSERACT_LANG_MAP.get(language, "eng")

    try:
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            output_type=pytesseract.Output.DICT,
        )
        lines: dict[int, list[str]] = {}
        confidences: dict[int, list[float]] = {}
        regions = []

        for i, word in enumerate(data["text"]):
            if not word.strip():
                continue
            conf = float(data["conf"][i])
            if conf < 0:
                continue
            line_num = data["line_num"][i]
            lines.setdefault(line_num, []).append(word)
            confidences.setdefault(line_num, []).append(conf / 100.0)

            left = float(data["left"][i])
            top_val = float(data["top"][i])
            w = float(data["width"][i])
            h = float(data["height"][i])
            bbox = [[left, top_val], [left + w, top_val],
                    [left + w, top_val + h], [left, top_val + h]]
            regions.append(OcrTextRegion(
                text=word, confidence=conf / 100.0,
                bbox=bbox, cx=left + w / 2, cy=top_val + h / 2,
            ))

        result.lines = [" ".join(words) for words in lines.values()]
        flat_conf = [c for confs in confidences.values() for c in confs]
        result.confidences = flat_conf
        result.regions = regions
        result.text = "\n".join(result.lines)
        result.aggregate_confidence()

    except Exception as e:
        result.text = f"[Tesseract error: {e}]"
        result.confidence_label = "Failed"

    return result


# ---------------------------------------------------------------------------
# Ensemble mode
# ---------------------------------------------------------------------------

def _run_ensemble(image, language: str) -> OcrResult:
    """Run both RapidOCR and Tesseract, merge word-by-word by confidence."""
    from .ocr_ensemble import WordBox, normalize_bbox, merge_word_results, words_to_text

    result_a = _run_rapidocr(image, language) if rapidocr_available() else None
    result_b = _run_tesseract(image, language) if tesseract_available() else None

    if result_a and not result_b:
        return result_a
    if result_b and not result_a:
        return result_b
    if not result_a and not result_b:
        return OcrResult(engine_used="none", confidence_label="Failed",
                         text="[OCR unavailable — install RapidOCR or Tesseract]")

    def regions_to_wordboxes(regions, engine):
        boxes = []
        for r in regions:
            if not r.text.strip():
                continue
            try:
                l, t, r2, b = normalize_bbox(r.bbox)
            except (ValueError, IndexError):
                continue
            boxes.append(WordBox(
                text=r.text, confidence=r.confidence,
                left=l, top=t, right=r2, bottom=b, engine=engine,
            ))
        return boxes

    words_a = regions_to_wordboxes(result_a.regions, "rapidocr")
    words_b = regions_to_wordboxes(result_b.regions, "tesseract")

    merged = merge_word_results(words_a, words_b)
    text_lines, confidences = words_to_text(merged)

    merged_regions = [
        OcrTextRegion(
            text=w.text, confidence=w.confidence,
            bbox=[[w.left, w.top], [w.right, w.top],
                  [w.right, w.bottom], [w.left, w.bottom]],
            cx=w.cx, cy=w.cy,
        )
        for w in merged if w.text.strip()
    ]

    result = OcrResult(engine_used="ensemble (rapidocr+tesseract)")
    result.lines = text_lines
    result.confidences = confidences
    result.regions = merged_regions
    result.text = "\n".join(text_lines)
    result.aggregate_confidence()
    return result
