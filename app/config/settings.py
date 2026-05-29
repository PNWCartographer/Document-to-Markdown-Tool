import json
import os
import tempfile

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
    "parallel_workers":       "Auto",
    "quality_preset":         "Quality",
    "ocr_language":           "English",
    "output_format":          "Markdown",
    "markdown_flavor":        "GFM",
    "yaml_front_matter":      True,
    "overwrite_existing":     False,
    "output_subfolder":       True,
    # Consumed by the GUI layer (gui/app.py), not the conversion engine.
    "low_confidence_action":  "Ask me",
    "auto_translate":         True,
    "dxf_svg_preview":        True,
    "ocr_engine":             "Auto",
    "rules_profile":          "None",
    "spdf_deskew":            True,
    "spdf_clean":             False,
    "spdf_force_ocr":         False,
    "spdf_optimize":          1,
    "spdf_pdfa":              False,
    "spdf_sidecar":           False,
    "spdf_rag_sidecar":       False,
    "spdf_bg_removal":        False,
    "theme":                  "system",
    "last_output_folder":     "",
    "_dep_check_done":        False,
    "_collapsed_sections": {
        "conversion": False,
        "content_handling": True,
        "ocr": False,
        "output": False,
        "searchable_pdf": False,
        "performance": False,
        "post_processing": True,
    },
}


def load() -> dict:
    if os.path.isfile(_PATH):
        try:
            with open(_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            out = dict(DEFAULTS)
            out.update({k: v for k, v in data.items() if k in DEFAULTS})
            # Ensure numeric settings stay as int
            for int_key in ("spdf_optimize",):
                try:
                    out[int_key] = int(out[int_key])
                except (ValueError, TypeError):
                    out[int_key] = DEFAULTS[int_key]
            # Migrate parallel_workers from old int default 1 → "Auto"
            if out["parallel_workers"] == 1:
                out["parallel_workers"] = "Auto"
            # Migrate renamed output format: "RAG Chunks" → "AI-Ready Chunks"
            if out.get("output_format") == "RAG Chunks":
                out["output_format"] = "AI-Ready Chunks"
            return out
        except Exception:
            pass
    return dict(DEFAULTS)


def save(cfg: dict) -> None:
    dir_path = os.path.dirname(_PATH)
    tmp_path = None
    try:
        fd = tempfile.NamedTemporaryFile(
            mode="w", suffix=".tmp", dir=dir_path,
            delete=False, encoding="utf-8",
        )
        tmp_path = fd.name
        try:
            json.dump({k: cfg[k] for k in DEFAULTS if k in cfg}, fd, indent=2)
            fd.flush()
            os.fsync(fd.fileno())
        finally:
            fd.close()
        os.replace(tmp_path, _PATH)
    except OSError:
        # Clean up temp file on failure if it still exists
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
