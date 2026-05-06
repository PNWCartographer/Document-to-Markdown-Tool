"""
OCR abstraction layer.

Primary:  PaddleOCR  (deep learning, no external binary, Apache 2.0)
Fallback: pytesseract + Tesseract binary

Both paths accept a PIL Image and return an OcrResult with extracted text,
per-line confidence scores, and an aggregate confidence label.

Lazy imports — neither engine is loaded until first use. This avoids slow
startup times and allows the tool to run without OCR dependencies installed
(converters will call is_available() before attempting OCR).
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Windows DLL search path fix — must run before any torch/paddle import.
# Windows Store Python sandbox restricts DLL loading; add torch's lib dir
# explicitly so shm.dll and other torch libs resolve correctly.
# ---------------------------------------------------------------------------
def _add_torch_dll_dir() -> None:
    if sys.platform != "win32":
        return
    try:
        import torch
        lib_dir = os.path.join(os.path.dirname(torch.__file__), "lib")
        if os.path.isdir(lib_dir):
            os.add_dll_directory(lib_dir)
    except Exception:
        pass

_add_torch_dll_dir()

# ---------------------------------------------------------------------------
# Tesseract binary discovery — check common Windows install paths and PATH
# before pytesseract is imported so the env var is set early.
# ---------------------------------------------------------------------------
_TESSERACT_SEARCH_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.join(os.path.expanduser("~"), r"AppData\Local\Tesseract-OCR\tesseract.exe"),
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
_paddle_engine = None
_paddle_available: Optional[bool] = None
_tesseract_available: Optional[bool] = None


@dataclass
class OcrResult:
    text: str = ""
    lines: list[str] = field(default_factory=list)
    confidences: list[float] = field(default_factory=list)  # 0.0–1.0 per line
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


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------

def paddle_available() -> bool:
    global _paddle_available
    if _paddle_available is not None:
        return _paddle_available
    try:
        import paddleocr  # noqa: F401
        _paddle_available = True
    except Exception:
        # Catches ImportError, OSError (DLL load failures), and any other
        # runtime error that can occur when the paddle/torch stack is broken.
        _paddle_available = False
    return _paddle_available


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
    return paddle_available() or tesseract_available()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_ocr(
    image,                      # PIL.Image.Image
    language: str = "en",
    prefer_engine: str = "paddle",
) -> OcrResult:
    """
    Run OCR on a PIL Image.

    Parameters
    ----------
    image : PIL.Image.Image
    language : str
        Language code. "en" for English. PaddleOCR uses its own codes;
        Tesseract uses ISO 639-2 (e.g. "eng"). This function translates.
    prefer_engine : str
        "paddle" or "tesseract". Falls back to the other if unavailable.
    """
    if prefer_engine == "paddle" and paddle_available():
        return _run_paddle(image, language)
    if tesseract_available():
        return _run_tesseract(image, language)
    if paddle_available():
        return _run_paddle(image, language)

    result = OcrResult(engine_used="none", confidence_label="Failed")
    result.text = "[OCR unavailable — install PaddleOCR or Tesseract]"
    return result


# ---------------------------------------------------------------------------
# PaddleOCR engine
# ---------------------------------------------------------------------------

_PADDLE_LANG_MAP = {
    "en": "en",
    "fr": "fr",
    "de": "german",
    "es": "es",
    "it": "it",
    "pt": "pt",
    "zh": "ch",
    "ja": "japan",
    "ko": "korean",
    "ar": "ar",
    "ru": "ru",
}


def _get_paddle_engine(language: str):
    global _paddle_engine
    if _paddle_engine is None:
        from paddleocr import PaddleOCR
        lang = _PADDLE_LANG_MAP.get(language, "en")
        _paddle_engine = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            show_log=False,
        )
    return _paddle_engine


def _run_paddle(image, language: str) -> OcrResult:
    import numpy as np

    result = OcrResult(engine_used="paddleocr")
    try:
        engine = _get_paddle_engine(language)
        img_array = np.array(image.convert("RGB"))
        raw = engine.ocr(img_array, cls=True)

        lines = []
        confidences = []

        if raw and raw[0]:
            for line in raw[0]:
                if line and len(line) >= 2:
                    text_info = line[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        text = str(text_info[0])
                        conf = float(text_info[1])
                    else:
                        text = str(text_info)
                        conf = 0.5
                    if text.strip():
                        lines.append(text)
                        confidences.append(conf)

        result.lines = lines
        result.confidences = confidences
        result.text = "\n".join(lines)
        result.aggregate_confidence()

    except Exception as e:
        result.text = f"[PaddleOCR error: {e}]"
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

        for i, word in enumerate(data["text"]):
            if not word.strip():
                continue
            conf = float(data["conf"][i])
            if conf < 0:
                continue
            line_num = data["line_num"][i]
            lines.setdefault(line_num, []).append(word)
            confidences.setdefault(line_num, []).append(conf / 100.0)

        result.lines = [" ".join(words) for words in lines.values()]
        flat_conf = [c for confs in confidences.values() for c in confs]
        result.confidences = flat_conf
        result.text = "\n".join(result.lines)
        result.aggregate_confidence()

    except Exception as e:
        result.text = f"[Tesseract error: {e}]"
        result.confidence_label = "Failed"

    return result
