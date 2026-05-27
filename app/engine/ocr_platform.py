"""
Platform-aware OCR engine routing.

Routes OCR requests to the best available engine based on the current platform:
  - Windows/Linux: RapidOCR (ONNX Runtime + CUDA/DirectML/CPU) -> Tesseract fallback
  - macOS: Apple Vision (Neural Engine) -> RapidOCR (CoreML) -> Tesseract fallback

All engines run locally. No network activity during OCR processing.
"""

import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class OcrEngineInfo:
    """Information about an available OCR engine."""
    name: str           # "rapidocr", "tesseract", "apple_vision"
    display_name: str   # "RapidOCR", "Tesseract", "Apple Vision"
    available: bool
    provider: str = ""  # ONNX provider or platform API, empty if N/A
    is_primary: bool = False


# Cached results — detect once per process
_cached_engines: Optional[list[OcrEngineInfo]] = None


def get_available_engines() -> list[OcrEngineInfo]:
    """Detect all available OCR engines on this platform.

    Results are cached after first call. Engines are returned in priority
    order (first = best choice for this platform).
    """
    global _cached_engines
    if _cached_engines is not None:
        return list(_cached_engines)

    engines: list[OcrEngineInfo] = []

    # macOS: check Apple Vision first (fastest on Apple Silicon)
    if sys.platform == "darwin":
        av = _check_apple_vision()
        if av and av.available:
            engines.append(av)

    # RapidOCR (all platforms)
    rapid = _check_rapidocr()
    if rapid and rapid.available:
        engines.append(rapid)

    # Tesseract (all platforms, universal fallback)
    tess = _check_tesseract()
    if tess and tess.available:
        engines.append(tess)

    # Mark the first available engine as primary
    if engines:
        engines[0].is_primary = True

    _cached_engines = engines
    return list(engines)


def get_best_engine_name() -> str:
    """Return the internal name of the best available OCR engine.

    Returns one of: "apple_vision", "rapidocr", "tesseract", "none".
    """
    for engine in get_available_engines():
        if engine.available:
            return engine.name
    return "none"


def get_engine_choices() -> list[str]:
    """Return display names for the OCR Engine dropdown.

    Always starts with "Auto". Adds "Ensemble" when both RapidOCR and
    Tesseract are available (ensemble requires two engines).
    """
    choices = ["Auto"]
    engines = get_available_engines()

    for e in engines:
        if e.available and e.display_name not in choices:
            choices.append(e.display_name)

    # Ensemble requires at least RapidOCR + Tesseract
    has_rapid = any(e.name == "rapidocr" and e.available for e in engines)
    has_tess = any(e.name == "tesseract" and e.available for e in engines)
    if has_rapid and has_tess:
        choices.append("Ensemble")

    return choices


def map_engine_setting(setting_value: str) -> str:
    """Map an OCR Engine dropdown value to the run_ocr prefer_engine parameter.

    Returns one of: "rapidocr", "tesseract", "apple_vision", "ensemble".
    "Auto" maps to the best available engine.
    """
    mapping = {
        "Auto": get_best_engine_name(),
        "RapidOCR": "rapidocr",
        "Tesseract": "tesseract",
        "Apple Vision": "apple_vision",
        "Ensemble": "ensemble",
    }
    return mapping.get(setting_value, get_best_engine_name())


# ---------------------------------------------------------------------------
# Engine availability checks
# ---------------------------------------------------------------------------

def _check_rapidocr() -> OcrEngineInfo:
    """Check if RapidOCR (ONNX Runtime) is available."""
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        # Determine best ONNX provider
        provider = "CPU"
        try:
            import onnxruntime
            providers = onnxruntime.get_available_providers()
            if "CUDAExecutionProvider" in providers:
                provider = "CUDA"
            elif "DmlExecutionProvider" in providers:
                provider = "DirectML"
            elif "CoreMLExecutionProvider" in providers:
                provider = "CoreML"
        except Exception:
            pass
        return OcrEngineInfo(
            name="rapidocr",
            display_name="RapidOCR",
            available=True,
            provider=provider,
        )
    except Exception:
        return OcrEngineInfo(
            name="rapidocr",
            display_name="RapidOCR",
            available=False,
        )


def _check_tesseract() -> OcrEngineInfo:
    """Check if Tesseract OCR binary is installed and accessible."""
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return OcrEngineInfo(
            name="tesseract",
            display_name="Tesseract",
            available=True,
        )
    except Exception:
        return OcrEngineInfo(
            name="tesseract",
            display_name="Tesseract",
            available=False,
        )


def _check_apple_vision() -> Optional[OcrEngineInfo]:
    """Check if Apple Vision Framework OCR is available (macOS only).

    Returns None on non-macOS platforms.
    """
    if sys.platform != "darwin":
        return None
    try:
        import ocrmac  # noqa: F401
        return OcrEngineInfo(
            name="apple_vision",
            display_name="Apple Vision",
            available=True,
            provider="Neural Engine",
        )
    except ImportError:
        # ocrmac not installed — Apple Vision not available, skip silently
        return None
