"""
Language detection and offline translation.

Provides two services for the conversion pipeline:

  1. **Language detection** — identifies the language of OCR'd text
     using fast-langdetect (FastText-based, ~1MB, 95% accuracy).

  2. **Offline translation** — translates text line-by-line using
     Argos Translate (fully offline, pip-installable, ~30 languages).

Both are optional — the module degrades gracefully if either
dependency is missing.  All processing is local.

Cross-platform: Windows, Linux, macOS.
"""

import os
from typing import Optional


# ── Language detection ────────────────────────────────────────

_LANGDETECT_AVAILABLE: Optional[bool] = None


def langdetect_available() -> bool:
    """Check if fast-langdetect is installed."""
    global _LANGDETECT_AVAILABLE
    if _LANGDETECT_AVAILABLE is None:
        try:
            from fast_langdetect import detect  # noqa: F401
            _LANGDETECT_AVAILABLE = True
        except ImportError:
            _LANGDETECT_AVAILABLE = False
    return _LANGDETECT_AVAILABLE


def detect_language(text: str, fallback: str = "en") -> tuple[str, float]:
    """
    Detect the language of *text*.

    Returns (language_code, confidence) where language_code is an
    ISO 639-1 two-letter code (e.g. "en", "ja", "de") and confidence
    is 0.0–1.0.

    Falls back to *fallback* if detection fails or text is too short.
    """
    if not langdetect_available():
        return fallback, 0.0

    # Need at least ~20 characters for reliable detection
    clean = text.strip()
    if len(clean) < 20:
        return fallback, 0.0

    try:
        from fast_langdetect import detect
        result = detect(clean, low_memory=True)
        lang = result.get("lang", fallback)
        score = result.get("score", 0.0)
        return lang, score
    except Exception:
        return fallback, 0.0


# ── Language code / name mapping ──────────────────────────────

_LANG_NAMES = {
    "en": "English",    "fr": "French",     "de": "German",
    "es": "Spanish",    "it": "Italian",    "pt": "Portuguese",
    "nl": "Dutch",      "ru": "Russian",    "zh": "Chinese",
    "ja": "Japanese",   "ko": "Korean",     "ar": "Arabic",
    "hi": "Hindi",      "tr": "Turkish",    "pl": "Polish",
    "sv": "Swedish",    "da": "Danish",     "fi": "Finnish",
    "el": "Greek",      "he": "Hebrew",     "hu": "Hungarian",
    "id": "Indonesian", "cs": "Czech",      "sk": "Slovak",
    "uk": "Ukrainian",  "fa": "Persian",    "th": "Thai",
    "vi": "Vietnamese", "ro": "Romanian",   "bg": "Bulgarian",
}


def language_name(code: str) -> str:
    """Return a human-readable name for a language code."""
    return _LANG_NAMES.get(code, code.upper())


# ── Offline translation (Argos Translate) ─────────────────────

_ARGOS_AVAILABLE: Optional[bool] = None
_INSTALLED_PAIRS: Optional[set] = None


def argos_available() -> bool:
    """Check if argostranslate is installed."""
    global _ARGOS_AVAILABLE
    if _ARGOS_AVAILABLE is None:
        try:
            import argostranslate.translate  # noqa: F401
            _ARGOS_AVAILABLE = True
        except ImportError:
            _ARGOS_AVAILABLE = False
    return _ARGOS_AVAILABLE


def _get_installed_pairs() -> set[tuple[str, str]]:
    """Return set of (from_code, to_code) for installed language packages."""
    global _INSTALLED_PAIRS
    if _INSTALLED_PAIRS is not None:
        return _INSTALLED_PAIRS
    pairs = set()
    try:
        import argostranslate.translate
        for lang in argostranslate.translate.get_installed_languages():
            for translation in lang.translations_from:
                pairs.add((lang.code, translation.to_lang.code))
    except Exception:
        pass
    _INSTALLED_PAIRS = pairs
    return pairs


def install_language_pair(from_code: str, to_code: str) -> bool:
    """
    Download and install a language pair if not already present.

    Returns True if the pair is available after the call.
    Language packs are ~100-300MB each, downloaded once and cached.
    """
    global _INSTALLED_PAIRS
    if not argos_available():
        return False

    # Check if already installed
    if (from_code, to_code) in _get_installed_pairs():
        return True

    try:
        import argostranslate.package

        # Update package index
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()

        # Find the matching package
        pkg = None
        for p in available:
            if p.from_code == from_code and p.to_code == to_code:
                pkg = p
                break

        if pkg is None:
            return False

        # Download and install, ensuring temp file is cleaned up
        download_path = None
        try:
            download_path = pkg.download()
            argostranslate.package.install_from_path(download_path)
        finally:
            if download_path and os.path.isfile(download_path):
                try:
                    os.unlink(download_path)
                except OSError:
                    pass

        # Reset cache
        _INSTALLED_PAIRS = None
        return True

    except Exception:
        return False


def translate_text(
    text: str,
    from_code: str,
    to_code: str = "en",
    auto_install: bool = True,
    _depth: int = 0,
) -> Optional[str]:
    """
    Translate *text* from *from_code* to *to_code* using Argos Translate.

    Returns the translated string, or None if translation fails or
    the language pair is not available.

    If *auto_install* is True, attempts to download the language pack
    on first use (requires internet for the initial download only).
    """
    if not argos_available():
        return None

    if from_code == to_code:
        return text  # No translation needed

    # Ensure the language pair is installed
    if (from_code, to_code) not in _get_installed_pairs():
        if auto_install:
            if not install_language_pair(from_code, to_code):
                # Try pivot through English (only if not already recursing)
                if _depth >= 1:
                    return None
                if to_code != "en" and from_code != "en":
                    if install_language_pair(from_code, "en"):
                        intermediate = translate_text(text, from_code, "en",
                                                       auto_install=False,
                                                       _depth=_depth + 1)
                        if intermediate:
                            return translate_text(intermediate, "en", to_code,
                                                   auto_install=False,
                                                   _depth=_depth + 1)
                return None
        else:
            return None

    try:
        import argostranslate.translate
        return argostranslate.translate.translate(text, from_code, to_code)
    except Exception:
        return None


def translate_lines(
    lines: list[str],
    from_code: str,
    to_code: str = "en",
    auto_install: bool = True,
) -> list[tuple[str, Optional[str]]]:
    """
    Translate a list of text lines.

    Returns a list of (original, translated) tuples. If translation
    fails for a line, the translated value is None (original preserved).
    """
    if not argos_available() or from_code == to_code:
        return [(line, None) for line in lines]

    # Batch translate: join lines, translate, split back
    # This is more efficient than line-by-line for the model
    separator = "\n"
    batch = separator.join(lines)
    translated_batch = translate_text(batch, from_code, to_code,
                                       auto_install=auto_install)

    if translated_batch is None:
        return [(line, None) for line in lines]

    translated_lines = translated_batch.split(separator)

    # Safety check: if line count doesn't match, fall back to returning
    # the full translated block as a single entry rather than crashing
    if len(translated_lines) != len(lines):
        return [(lines[0], translated_batch.strip())] + [
            (line, None) for line in lines[1:]
        ]

    results = []
    for i, original in enumerate(lines):
        trans = translated_lines[i].strip()
        # Only include translation if it's meaningfully different
        if trans and trans.lower() != original.lower():
            results.append((original, trans))
        else:
            results.append((original, None))

    return results
