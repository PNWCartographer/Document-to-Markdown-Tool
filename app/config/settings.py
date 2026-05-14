import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

DEFAULTS: dict = {
    "conversion_mode":        "Auto-detect",
    "preserve_images":        True,
    "preserve_page_numbers":  True,
    "rebuild_toc":            True,
    "embed_images":           True,
    "remove_headers_footers": True,
    "skip_blank_pages":       True,
    "strip_line_numbers":     False,
    "detect_code_blocks":     True,
    "detect_footnotes":       True,
    "detect_equations":       True,
    "parallel_workers":       "1",
    "quality_preset":         "Quality",
    "ocr_language":           "English",
    "output_format":          "Markdown",
    "overwrite_existing":     False,
    "output_subfolder":       False,
    "low_confidence_action":  "Ask me",
    "theme":                  "dark",
}


def load() -> dict:
    if os.path.isfile(_PATH):
        try:
            with open(_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            out = dict(DEFAULTS)
            out.update({k: v for k, v in data.items() if k in DEFAULTS})
            return out
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    with open(_PATH, "w", encoding="utf-8") as fh:
        json.dump({k: cfg[k] for k in DEFAULTS if k in cfg}, fh, indent=2)
