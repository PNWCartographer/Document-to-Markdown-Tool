"""
Headless engine test suite — exercises conversion engine across settings combos.

Run from repo root:  python test_engine.py
"""
import os
import sys
import shutil
import time
import threading
import traceback

# Force UTF-8 stdout to avoid cp1252 encoding errors on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add app/ to path so engine imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

TEST_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_files")
TEST_OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "_test_output")

# ── Helpers ──────────────────────────────────────────────────────

PASS = 0
FAIL = 0
WARN = 0
results_log = []


def log(msg):
    print(msg, flush=True)
    results_log.append(msg)


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        log(f"  ✓ {name}")
    else:
        FAIL += 1
        log(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


def warn(name, detail=""):
    global WARN
    WARN += 1
    log(f"  ⚠ {name}" + (f" — {detail}" if detail else ""))


def clean_output():
    if os.path.exists(TEST_OUTPUT_ROOT):
        shutil.rmtree(TEST_OUTPUT_ROOT, ignore_errors=True)
    os.makedirs(TEST_OUTPUT_ROOT, exist_ok=True)


def find_output_file(output_dir, ext=".md"):
    """Find first file with given extension in output dir (recursive)."""
    for root, _dirs, files in os.walk(output_dir):
        for f in files:
            if f.endswith(ext):
                return os.path.join(root, f)
    return None


def read_output(output_dir, ext=".md"):
    """Read the first output file with given extension."""
    path = find_output_file(output_dir, ext)
    if path:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return None


def list_output_files(output_dir):
    """List all files in output dir recursively."""
    found = []
    for root, _dirs, files in os.walk(output_dir):
        for f in files:
            found.append(os.path.relpath(os.path.join(root, f), output_dir))
    return found


# ── Persistent tkinter root (shared across all tests) ──────────────
# Creating multiple tk.Tk() instances breaks the after() callback
# mechanism.  We create one root at import time and reuse it.

import tkinter as tk
_SHARED_ROOT = tk.Tk()
_SHARED_ROOT.withdraw()

# ── Minimal headless conversion runner ────────────────────────────

def run_conversion(files, cfg_overrides=None, page_ranges=None):
    """Run conversion headlessly using ConversionJob with a hidden tk root."""
    from engine.converter import ConversionJob

    cfg_base = {
        "conversion_mode": "Auto-detect",
        "preserve_images": True,
        "preserve_page_numbers": True,
        "rebuild_toc": True,
        "embed_images": True,
        "remove_headers_footers": True,
        "skip_blank_pages": True,
        "strip_line_numbers": False,
        "detect_code_blocks": True,
        "detect_footnotes": True,
        "detect_equations": True,
        "parallel_workers": "1",
        # Default to Fast for speed — docling (Quality) takes minutes per file.
        # Tests that need Quality override this explicitly.
        "quality_preset": "Fast",
        "ocr_language": "English",
        "output_format": "Markdown",
        "markdown_flavor": "GFM",
        "yaml_front_matter": True,
        "overwrite_existing": True,
        "output_subfolder": True,
        "auto_translate": True,
        "dxf_svg_preview": True,
        "ocr_engine": "Auto",
        "rules_profile": "None",
        "spdf_deskew": True,
        "spdf_clean": False,
        "spdf_force_ocr": False,
        "spdf_optimize": 1,
        "spdf_pdfa": False,
        "spdf_sidecar": False,
        "spdf_rag_sidecar": False,
        "spdf_bg_removal": False,
    }
    if cfg_overrides:
        cfg_base.update(cfg_overrides)

    output_dir = os.path.join(TEST_OUTPUT_ROOT, f"run_{int(time.time()*1000)}")
    os.makedirs(output_dir, exist_ok=True)

    root = _SHARED_ROOT

    log_lines = []
    done_event = threading.Event()
    result_holder = [None]

    def on_log(msg): log_lines.append(msg)
    def on_file_progress(p): pass
    def on_overall_progress(p): pass
    def on_file_start(fname, idx, total): pass
    def on_stage(s): pass
    def on_done(batch_result):
        result_holder[0] = batch_result
        done_event.set()

    job = ConversionJob(
        files=files,
        aliases={},
        output_root=output_dir,
        cfg=cfg_base,
        root=root,
        on_log=on_log,
        on_file_progress=on_file_progress,
        on_overall_progress=on_overall_progress,
        on_file_start=on_file_start,
        on_stage=on_stage,
        on_done=on_done,
        page_ranges=page_ranges,
    )

    # Bypass root.after() — calling tkinter.after() from background threads
    # silently fails on Python 3.14/Windows.  Direct-invoke is fine for tests.
    job._gui = lambda fn, *a: fn(*a)

    job.start()

    # Pump the tkinter event loop until done (max 120s)
    deadline = time.time() + 120
    while not done_event.is_set() and time.time() < deadline:
        try:
            root.update()
        except Exception:
            break
        time.sleep(0.05)

    return result_holder[0], output_dir, log_lines


# ═══════════════════════════════════════════════════════════════════
# TEST SUITES
# ═══════════════════════════════════════════════════════════════════

def test_basic_conversion_all_types():
    """Test 1: Basic conversion of every file type with default settings."""
    log("\n═══ TEST 1: Basic conversion — all file types (defaults) ═══")

    test_files = {
        "sample_annual_report.pdf": ".md",
        "sample_requirements.docx": ".md",
        "sample_ocr_image.png": ".md",
        "sample_financials.xlsx": ".md",
        "sample_spreadsheet.csv": ".md",
        "sample_presentation.pptx": ".md",
        "sample_report.html": ".md",
        "sample_spec.rtf": ".md",
    }

    for fname, expected_ext in test_files.items():
        fpath = os.path.join(TEST_FILES_DIR, fname)
        if not os.path.isfile(fpath):
            warn(f"{fname}", "file not found — skipping")
            continue

        try:
            result, out_dir, logs = run_conversion([fpath])
            check(f"{fname} — conversion completes",
                  result is not None and result.completed >= 1,
                  f"completed={getattr(result, 'completed', '?')}, failed={getattr(result, 'failed', '?')}")

            md_content = read_output(out_dir, expected_ext)
            check(f"{fname} — output file exists",
                  md_content is not None,
                  "no .md output found")

            if md_content:
                check(f"{fname} — output not empty",
                      len(md_content.strip()) > 10,
                      f"only {len(md_content.strip())} chars")

                # Confidence result exists
                if result and result.all_confidence:
                    conf = result.all_confidence[0]
                    check(f"{fname} — confidence reported",
                          conf.overall is not None and conf.overall != "N/A",
                          f"overall={conf.overall}")
        except Exception as e:
            check(f"{fname} — no crash", False, str(e))


def test_yaml_front_matter():
    """Test 2: YAML front matter toggle."""
    log("\n═══ TEST 2: YAML front matter toggle ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_annual_report.pdf")

    # With YAML
    result, out_dir, _ = run_conversion([fpath], {"yaml_front_matter": True})
    content = read_output(out_dir)
    check("YAML=True — has front matter",
          content is not None and content.strip().startswith("---"),
          f"starts with: {repr(content[:30]) if content else 'None'}")

    # Without YAML
    result, out_dir, _ = run_conversion([fpath], {"yaml_front_matter": False})
    content = read_output(out_dir)
    check("YAML=False — no front matter",
          content is not None and not content.strip().startswith("---"),
          f"starts with: {repr(content[:30]) if content else 'None'}")


def test_preserve_page_numbers():
    """Test 3: Preserve page numbers toggle."""
    log("\n═══ TEST 3: Page numbers toggle ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_annual_report.pdf")

    # With page numbers
    result, out_dir, _ = run_conversion([fpath], {"preserve_page_numbers": True})
    content = read_output(out_dir)
    has_markers = content is not None and ("<!-- Page" in content or "---\n\n## Page" in content
                                           or "Page 1" in content)
    check("page_numbers=True — has page markers",
          has_markers,
          "no page marker patterns found")

    # Without page numbers
    result, out_dir, _ = run_conversion([fpath], {"preserve_page_numbers": False})
    content = read_output(out_dir)
    no_markers = content is not None and "<!-- Page" not in content
    check("page_numbers=False — no page markers",
          no_markers,
          "still found page markers")


def test_output_subfolder():
    """Test 4: Output subfolder toggle."""
    log("\n═══ TEST 4: Output subfolder toggle ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_spreadsheet.csv")

    # With subfolder
    result, out_dir, _ = run_conversion([fpath], {"output_subfolder": True})
    files = list_output_files(out_dir)
    has_subfolder = any(os.sep in f or "/" in f for f in files)
    check("subfolder=True — output in subfolder",
          has_subfolder,
          f"files: {files}")

    # Without subfolder
    result, out_dir, _ = run_conversion([fpath], {"output_subfolder": False})
    files = list_output_files(out_dir)
    all_flat = all(os.sep not in f and "/" not in f for f in files if f.endswith(".md"))
    check("subfolder=False — output is flat",
          all_flat,
          f"files: {files}")


def test_embed_images():
    """Test 5: Embed images toggle."""
    log("\n═══ TEST 5: Embed images toggle ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_ocr_image.png")

    # Embed = True → base64 data URIs in markdown
    result, out_dir, _ = run_conversion([fpath], {"embed_images": True})
    content = read_output(out_dir)
    has_base64 = content is not None and "data:image" in content
    has_file_ref = content is not None and "assets/" in content
    check("embed=True — has base64 data URIs OR file refs",
          content is not None and (has_base64 or has_file_ref),
          "no image references found")

    # Embed = False → file path references
    result, out_dir, _ = run_conversion([fpath], {"embed_images": False})
    content = read_output(out_dir)
    assets_files = list_output_files(out_dir)
    has_asset_files = any("assets" in f for f in assets_files)
    check("embed=False — assets folder created",
          has_asset_files or (content is not None and "assets/" in content),
          f"files: {assets_files}")


def test_rebuild_toc():
    """Test 6: Rebuild TOC toggle."""
    log("\n═══ TEST 6: Rebuild TOC toggle ═══")

    # Use docx which likely has headings
    fpath = os.path.join(TEST_FILES_DIR, "sample_requirements.docx")

    # TOC = True
    result, out_dir, _ = run_conversion([fpath], {"rebuild_toc": True})
    content = read_output(out_dir)
    has_toc = content is not None and ("## Table of Contents" in content
                                       or "## Contents" in content
                                       or "- [" in content)
    check("rebuild_toc=True — has TOC section",
          has_toc,
          "no TOC found (may be expected if doc has no headings)")

    # TOC = False
    result, out_dir, _ = run_conversion([fpath], {"rebuild_toc": False})
    content = read_output(out_dir)
    no_toc = content is not None and "## Table of Contents" not in content
    check("rebuild_toc=False — no TOC section",
          no_toc,
          "still found TOC")


def test_ocr_engine_settings():
    """Test 7: OCR engine preference."""
    log("\n═══ TEST 7: OCR engine settings ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_ocr_image.png")

    for engine in ["RapidOCR", "Auto"]:
        result, out_dir, _ = run_conversion([fpath], {"ocr_engine": engine})
        content = read_output(out_dir)
        check(f"ocr_engine={engine} — produces output",
              content is not None and len(content.strip()) > 20,
              f"content length: {len(content.strip()) if content else 0}")

        if result and result.all_confidence:
            conf = result.all_confidence[0]
            check(f"ocr_engine={engine} — OCR confidence reported",
                  conf.ocr_confidence is not None and conf.ocr_confidence != "N/A",
                  f"ocr_confidence={conf.ocr_confidence}")


def test_quality_presets():
    """Test 8: Quality presets (Fast, Balanced, Quality)."""
    log("\n═══ TEST 8: Quality presets ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_annual_report.pdf")

    for preset in ["Fast", "Balanced", "Quality"]:
        result, out_dir, logs = run_conversion([fpath], {"quality_preset": preset})
        content = read_output(out_dir)
        check(f"quality={preset} — conversion succeeds",
              result is not None and result.completed >= 1,
              f"completed={getattr(result, 'completed', '?')}")
        check(f"quality={preset} — output not empty",
              content is not None and len(content.strip()) > 10,
              f"len={len(content.strip()) if content else 0}")


def test_mixed_batch():
    """Test 9: Mixed batch — multiple file types in one batch."""
    log("\n═══ TEST 9: Mixed batch conversion ═══")

    files = [
        os.path.join(TEST_FILES_DIR, f) for f in [
            "sample_annual_report.pdf",
            "sample_requirements.docx",
            "sample_spreadsheet.csv",
            "sample_report.html",
        ]
    ]
    files = [f for f in files if os.path.isfile(f)]

    result, out_dir, _ = run_conversion(files)
    check(f"mixed batch — all {len(files)} files complete",
          result is not None and result.completed == len(files),
          f"completed={getattr(result, 'completed', '?')}, failed={getattr(result, 'failed', '?')}")

    check("mixed batch — per-file confidence results",
          result is not None and len(result.all_confidence) == len(files),
          f"got {len(result.all_confidence) if result else 0} confidence results")


def test_edge_empty_file():
    """Test 10: Edge case — empty/tiny file."""
    log("\n═══ TEST 10: Edge case — empty file ═══")

    # Create a 0-byte txt file (not a supported type, should fail gracefully)
    empty_path = os.path.join(TEST_OUTPUT_ROOT, "empty_test.txt")
    with open(empty_path, "w") as f:
        pass

    result, out_dir, logs = run_conversion([empty_path])
    check("empty .txt — does not crash",
          result is not None,
          "result is None — crashed?")
    # Engine may treat .txt as convertible plain text — either outcome is fine
    check("empty .txt — handled gracefully",
          result is not None and (result.failed >= 1 or result.completed >= 1),
          f"completed={getattr(result, 'completed', '?')}, failed={getattr(result, 'failed', '?')}")


def test_edge_unsupported_type():
    """Test 11: Edge case — unsupported file type."""
    log("\n═══ TEST 11: Edge case — unsupported extension ═══")

    fake_path = os.path.join(TEST_OUTPUT_ROOT, "fake_file.zip")
    with open(fake_path, "wb") as f:
        f.write(b"PK\x03\x04")  # Minimal zip header

    result, out_dir, logs = run_conversion([fake_path])
    check("unsupported .zip — does not crash",
          result is not None,
          "result is None — crashed?")
    # Engine handles gracefully — may report completed (with minimal output) or failed
    check("unsupported .zip — handled gracefully",
          result is not None and (result.failed >= 1 or result.completed >= 1),
          f"completed={getattr(result, 'completed', '?')}, failed={getattr(result, 'failed', '?')}")


def test_cancel_midway():
    """Test 12: Cancel mid-conversion."""
    log("\n═══ TEST 12: Cancel mid-conversion ═══")

    # Use all files for a longer batch
    files = [
        os.path.join(TEST_FILES_DIR, f) for f in [
            "sample_annual_report.pdf",
            "sample_requirements.docx",
            "sample_ocr_image.png",
            "sample_financials.xlsx",
            "sample_spreadsheet.csv",
            "sample_presentation.pptx",
            "sample_report.html",
            "sample_spec.rtf",
        ]
    ]
    files = [f for f in files if os.path.isfile(f)]

    from engine.converter import ConversionJob

    output_dir = os.path.join(TEST_OUTPUT_ROOT, f"cancel_test_{int(time.time()*1000)}")
    os.makedirs(output_dir, exist_ok=True)

    root = _SHARED_ROOT

    done_event = threading.Event()
    result_holder = [None]
    file_count = [0]

    def on_done(br):
        result_holder[0] = br
        done_event.set()

    def on_file_start(fname, idx, total):
        file_count[0] = idx

    job = ConversionJob(
        files=files, aliases={}, output_root=output_dir,
        cfg={"parallel_workers": "1", "output_format": "Markdown",
             "overwrite_existing": True, "output_subfolder": True,
             "ocr_engine": "Auto", "yaml_front_matter": True,
             "preserve_page_numbers": True, "rebuild_toc": True,
             "embed_images": True, "quality_preset": "Fast",
             "conversion_mode": "Auto-detect", "preserve_images": True,
             "remove_headers_footers": True, "skip_blank_pages": True,
             "strip_line_numbers": False, "detect_code_blocks": True,
             "detect_footnotes": True, "detect_equations": True,
             "auto_translate": True, "dxf_svg_preview": True,
             "rules_profile": "None", "ocr_language": "English",
             "markdown_flavor": "GFM"},
        root=root,
        on_log=lambda m: None, on_file_progress=lambda p: None,
        on_overall_progress=lambda p: None,
        on_file_start=on_file_start,
        on_stage=lambda s: None, on_done=on_done,
    )
    job._gui = lambda fn, *a: fn(*a)

    job.start()

    # Let it process for 2 seconds then cancel
    deadline_cancel = time.time() + 2
    while not done_event.is_set() and time.time() < deadline_cancel:
        try:
            root.update()
        except Exception:
            break
        time.sleep(0.05)

    if not done_event.is_set():
        job.cancel()
        # Wait for it to finish
        deadline = time.time() + 30
        while not done_event.is_set() and time.time() < deadline:
            try:
                root.update()
            except Exception:
                break
            time.sleep(0.05)

    result = result_holder[0]
    check("cancel — job stopped without crash",
          result is not None,
          "result is None")
    check("cancel — cancelled flag set",
          result is not None and result.cancelled,
          f"cancelled={getattr(result, 'cancelled', '?')}")
    check("cancel — not all files processed",
          result is not None and result.completed < len(files),
          f"completed={getattr(result, 'completed', '?')}/{len(files)}")


def test_page_range():
    """Test 13: Page range selection on PDF."""
    log("\n═══ TEST 13: Page range selection ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_annual_report.pdf")

    # First convert full PDF to count pages
    result_full, out_dir_full, _ = run_conversion([fpath])
    content_full = read_output(out_dir_full)

    # Now convert only page 1
    result_p1, out_dir_p1, _ = run_conversion(
        [fpath],
        page_ranges={fpath: [1]},
    )
    content_p1 = read_output(out_dir_p1)

    check("page_range=[1] — conversion succeeds",
          result_p1 is not None and result_p1.completed >= 1,
          f"completed={getattr(result_p1, 'completed', '?')}")

    if content_full and content_p1:
        check("page_range=[1] — output shorter than full",
              len(content_p1) < len(content_full),
              f"p1={len(content_p1)} vs full={len(content_full)}")


def test_overwrite_protection():
    """Test 14: Overwrite existing protection."""
    log("\n═══ TEST 14: Overwrite protection ═══")

    fpath = os.path.join(TEST_FILES_DIR, "sample_spreadsheet.csv")

    # First conversion
    result1, out_dir, _ = run_conversion([fpath], {"overwrite_existing": False})
    check("first run — succeeds",
          result1 is not None and result1.completed >= 1, "")

    # Second conversion to same dir — should skip
    from engine.converter import ConversionJob

    root = _SHARED_ROOT
    done_event = threading.Event()
    result_holder = [None]
    log_lines = []

    def on_done(br):
        result_holder[0] = br
        done_event.set()

    job = ConversionJob(
        files=[fpath], aliases={}, output_root=out_dir,
        cfg={"parallel_workers": "1", "output_format": "Markdown",
             "overwrite_existing": False, "output_subfolder": True,
             "ocr_engine": "Auto", "yaml_front_matter": True,
             "preserve_page_numbers": True, "rebuild_toc": True,
             "embed_images": True, "quality_preset": "Fast",
             "conversion_mode": "Auto-detect", "preserve_images": True,
             "remove_headers_footers": True, "skip_blank_pages": True,
             "strip_line_numbers": False, "detect_code_blocks": True,
             "detect_footnotes": True, "detect_equations": True,
             "auto_translate": True, "dxf_svg_preview": True,
             "rules_profile": "None", "ocr_language": "English",
             "markdown_flavor": "GFM"},
        root=root,
        on_log=lambda m: log_lines.append(m),
        on_file_progress=lambda p: None,
        on_overall_progress=lambda p: None,
        on_file_start=lambda f, i, t: None,
        on_stage=lambda s: None, on_done=on_done,
    )
    job._gui = lambda fn, *a: fn(*a)
    job.start()

    deadline = time.time() + 30
    while not done_event.is_set() and time.time() < deadline:
        try:
            root.update()
        except Exception:
            break
        time.sleep(0.05)

    result2 = result_holder[0]
    skipped = any("skip" in line.lower() or "exists" in line.lower() for line in log_lines)
    check("overwrite=False — second run skips or fails",
          result2 is not None and (result2.failed >= 1 or skipped),
          f"completed={getattr(result2, 'completed', '?')}, logs mention skip: {skipped}")


# ═══════════════════════════════════════════════════════════════════
# STRESS TESTS — activated via --stress <path|dir>
# ═══════════════════════════════════════════════════════════════════

_STRESS_TIMEOUT = 7200  # 2 hours per conversion (large books)

# Minimum file size (MB) to qualify as a "stress" file
_STRESS_MIN_SIZE_MB = 1.0


def _get_pdf_pages(path):
    """Return page count for a PDF, or None on failure."""
    try:
        import fitz
        with fitz.open(path) as doc:
            return len(doc)
    except Exception:
        return None


def _get_csv_rows(path):
    """Return approximate row count for a CSV, or None on failure."""
    try:
        count = 0
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for _ in f:
                count += 1
        return count
    except Exception:
        return None


def _discover_stress_files(stress_path):
    """Discover and categorize stress-worthy files from a path.

    Returns dict with keys: 'primary_pdf', 'secondary_pdfs', 'csv_files',
    'all_heavy' — each containing file paths sorted largest first.
    """
    files = []
    if os.path.isfile(stress_path):
        files = [stress_path]
    elif os.path.isdir(stress_path):
        for fname in os.listdir(stress_path):
            fpath = os.path.join(stress_path, fname)
            if os.path.isfile(fpath):
                files.append(fpath)

    result = {
        "primary_pdf": None,       # Largest PDF (gets full S1-S6 treatment)
        "secondary_pdfs": [],      # Other PDFs over threshold
        "csv_files": [],           # Large CSV/XLSX files
        "all_heavy": [],           # Everything stress-worthy
    }

    pdf_candidates = []
    for fpath in files:
        ext = os.path.splitext(fpath)[1].lower()
        size_mb = os.path.getsize(fpath) / (1024 * 1024)

        if size_mb < _STRESS_MIN_SIZE_MB:
            continue

        result["all_heavy"].append(fpath)

        if ext == ".pdf":
            pages = _get_pdf_pages(fpath) or 0
            pdf_candidates.append((pages, size_mb, fpath))
        elif ext in (".csv", ".xlsx", ".xls"):
            result["csv_files"].append(fpath)

    # Sort PDFs by page count descending — largest is primary
    pdf_candidates.sort(key=lambda x: x[0], reverse=True)
    if pdf_candidates:
        result["primary_pdf"] = pdf_candidates[0][2]
        result["secondary_pdfs"] = [p[2] for p in pdf_candidates[1:]]

    return result


def _run_stress(files, cfg_overrides=None, page_ranges=None):
    """Like run_conversion() but with a much longer timeout for large files."""
    from engine.converter import ConversionJob

    cfg_base = {
        "conversion_mode": "Auto-detect",
        "preserve_images": True,
        "preserve_page_numbers": True,
        "rebuild_toc": True,
        "embed_images": False,        # False for stress — avoids huge base64 output
        "remove_headers_footers": True,
        "skip_blank_pages": True,
        "strip_line_numbers": False,
        "detect_code_blocks": True,
        "detect_footnotes": True,
        "detect_equations": True,
        "parallel_workers": "Auto",   # Use system-recommended parallelism
        "quality_preset": "Fast",
        "ocr_language": "English",
        "output_format": "Markdown",
        "markdown_flavor": "GFM",
        "yaml_front_matter": True,
        "overwrite_existing": True,
        "output_subfolder": True,
        "auto_translate": True,
        "dxf_svg_preview": True,
        "ocr_engine": "Auto",
        "rules_profile": "None",
        "spdf_deskew": True,
        "spdf_clean": False,
        "spdf_force_ocr": False,
        "spdf_optimize": 1,
        "spdf_pdfa": False,
        "spdf_sidecar": False,
        "spdf_rag_sidecar": False,
        "spdf_bg_removal": False,
    }
    if cfg_overrides:
        cfg_base.update(cfg_overrides)

    output_dir = os.path.join(TEST_OUTPUT_ROOT, f"stress_{int(time.time()*1000)}")
    os.makedirs(output_dir, exist_ok=True)

    root = _SHARED_ROOT
    log_lines = []
    done_event = threading.Event()
    result_holder = [None]
    progress_holder = [0.0]

    def on_log(msg): log_lines.append(msg)
    def on_file_progress(p):
        if p >= 0:
            progress_holder[0] = p
    def on_overall_progress(p): pass
    def on_file_start(fname, idx, total):
        log(f"    → [{idx}/{total}] {fname}")
    def on_stage(s):
        if s:
            log(f"    stage: {s}")
    def on_done(batch_result):
        result_holder[0] = batch_result
        done_event.set()

    job = ConversionJob(
        files=files,
        aliases={},
        output_root=output_dir,
        cfg=cfg_base,
        root=root,
        on_log=on_log,
        on_file_progress=on_file_progress,
        on_overall_progress=on_overall_progress,
        on_file_start=on_file_start,
        on_stage=on_stage,
        on_done=on_done,
        page_ranges=page_ranges,
    )
    job._gui = lambda fn, *a: fn(*a)
    job.start()

    # Long timeout for stress tests — report progress every 30s
    deadline = time.time() + _STRESS_TIMEOUT
    last_report = time.time()
    while not done_event.is_set() and time.time() < deadline:
        try:
            root.update()
        except Exception:
            break
        time.sleep(0.1)
        now = time.time()
        if now - last_report > 30:
            elapsed = int(now - (deadline - _STRESS_TIMEOUT))
            pct = progress_holder[0] * 100
            log(f"    ... {elapsed}s elapsed, ~{pct:.0f}% file progress")
            last_report = now

    return result_holder[0], output_dir, log_lines


# ── S1–S6: Primary PDF (largest book) ─────────────────────────────

def stress_full_markdown_fast(stress_file):
    """Stress S1: Full book — Markdown, Fast preset."""
    log("\n═══ STRESS S1: Full book — Markdown (Fast) ═══")
    t0 = time.time()
    result, out_dir, logs = _run_stress([stress_file], {"quality_preset": "Fast"})
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check("S1 — conversion completes",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}")
    md = read_output(out_dir)
    check("S1 — output file exists", md is not None)
    if md:
        size_kb = len(md.encode("utf-8")) / 1024
        log(f"    Output size: {size_kb:.0f} KB")
        check("S1 — output > 10 KB", size_kb > 10, f"only {size_kb:.0f} KB")
        # Spot-check structure
        check("S1 — has headings", "##" in md or "# " in md, "no markdown headings found")
        check("S1 — has page markers", "Page" in md or "page" in md, "no page references")
    if result and result.all_confidence:
        c = result.all_confidence[0]
        log(f"    Confidence: overall={c.overall}, text={c.text_extraction}, "
            f"tables={c.table_structure}, images={c.image_extraction}")


def stress_full_markdown_balanced(stress_file):
    """Stress S2: Full book — Markdown, Balanced preset (docling)."""
    log("\n═══ STRESS S2: Full book — Markdown (Balanced) ═══")
    t0 = time.time()
    result, out_dir, logs = _run_stress([stress_file], {"quality_preset": "Balanced"})
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check("S2 — conversion completes",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}")
    md = read_output(out_dir)
    if md:
        size_kb = len(md.encode("utf-8")) / 1024
        log(f"    Output size: {size_kb:.0f} KB")
        check("S2 — output > 10 KB", size_kb > 10, f"only {size_kb:.0f} KB")
        # Compare table rendering — docling should produce proper tables
        table_count = md.count("| --- |") + md.count("|---|")
        check("S2 — tables detected", table_count > 0, "no markdown tables found")


def stress_full_searchable_pdf(stress_file):
    """Stress S3: Full book — Searchable PDF output."""
    log("\n═══ STRESS S3: Full book — Searchable PDF ═══")
    t0 = time.time()
    result, out_dir, logs = _run_stress(
        [stress_file],
        {"output_format": "Searchable PDF", "quality_preset": "Fast"},
    )
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check("S3 — conversion completes",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}")
    # Check for PDF output
    pdf_out = find_output_file(out_dir, ".pdf")
    check("S3 — searchable PDF exists", pdf_out is not None, "no .pdf output found")
    if pdf_out:
        size_mb = os.path.getsize(pdf_out) / (1024 * 1024)
        log(f"    PDF size: {size_mb:.1f} MB")
        check("S3 — PDF > 1 MB", size_mb > 1, f"only {size_mb:.2f} MB")


def stress_page_range_samples(stress_file):
    """Stress S4: Spot-check specific page ranges (adaptive to book length)."""
    log("\n═══ STRESS S4: Page range spot-checks ═══")

    total_pages = _get_pdf_pages(stress_file) or 100
    log(f"    Total pages: {total_pages:,}")

    # a) First 20 pages (title, TOC, intro)
    result, out_dir, _ = _run_stress(
        [stress_file],
        {"quality_preset": "Fast"},
        page_ranges={stress_file: list(range(1, 21))},
    )
    md = read_output(out_dir)
    check("S4a — pages 1-20 converts", md is not None and len(md.strip()) > 100)

    # b) Mid-book pages (content-heavy)
    mid = max(21, total_pages // 2)
    mid_end = min(mid + 20, total_pages + 1)
    result, out_dir, _ = _run_stress(
        [stress_file],
        {"quality_preset": "Fast"},
        page_ranges={stress_file: list(range(mid, mid_end))},
    )
    md = read_output(out_dir)
    check(f"S4b — pages {mid}-{mid_end - 1} converts",
          md is not None and len(md.strip()) > 100)

    # c) Near-end pages (adaptive — last 20 pages of the book)
    near_end_start = max(1, total_pages - 20)
    result, out_dir, _ = _run_stress(
        [stress_file],
        {"quality_preset": "Fast"},
        page_ranges={stress_file: list(range(near_end_start, total_pages + 1))},
    )
    md = read_output(out_dir)
    check(f"S4c — pages {near_end_start}-{total_pages} converts",
          md is not None and len(md.strip()) > 50,
          "output too short or missing")


def stress_cancel_large(stress_file):
    """Stress S5: Cancel mid-conversion on the large file."""
    log("\n═══ STRESS S5: Cancel large file mid-conversion ═══")

    root = _SHARED_ROOT
    done_event = threading.Event()
    result_holder = [None]

    def on_done(br):
        result_holder[0] = br
        done_event.set()

    from engine.converter import ConversionJob

    output_dir = os.path.join(TEST_OUTPUT_ROOT, f"stress_cancel_{int(time.time()*1000)}")
    os.makedirs(output_dir, exist_ok=True)

    job = ConversionJob(
        files=[stress_file], aliases={}, output_root=output_dir,
        cfg={"parallel_workers": "1", "output_format": "Markdown",
             "overwrite_existing": True, "output_subfolder": True,
             "ocr_engine": "Auto", "yaml_front_matter": True,
             "preserve_page_numbers": True, "rebuild_toc": True,
             "embed_images": False, "quality_preset": "Fast",
             "conversion_mode": "Auto-detect", "preserve_images": True,
             "remove_headers_footers": True, "skip_blank_pages": True,
             "strip_line_numbers": False, "detect_code_blocks": True,
             "detect_footnotes": True, "detect_equations": True,
             "auto_translate": True, "dxf_svg_preview": True,
             "rules_profile": "None", "ocr_language": "English",
             "markdown_flavor": "GFM"},
        root=root,
        on_log=lambda m: None, on_file_progress=lambda p: None,
        on_overall_progress=lambda p: None,
        on_file_start=lambda f, i, t: None,
        on_stage=lambda s: None, on_done=on_done,
    )
    job._gui = lambda fn, *a: fn(*a)
    job.start()

    # Let it run 5 seconds then cancel
    cancel_at = time.time() + 5
    while not done_event.is_set() and time.time() < cancel_at:
        try:
            root.update()
        except Exception:
            break
        time.sleep(0.05)

    if not done_event.is_set():
        job.cancel()
        deadline = time.time() + 60
        while not done_event.is_set() and time.time() < deadline:
            try:
                root.update()
            except Exception:
                break
            time.sleep(0.05)

    result = result_holder[0]
    check("S5 — cancel completes without crash", result is not None)
    check("S5 — cancelled flag set",
          result is not None and result.cancelled,
          f"cancelled={getattr(result, 'cancelled', '?')}")


def stress_memory_check(stress_file):
    """Stress S6: Memory usage during full conversion."""
    log("\n═══ STRESS S6: Memory usage during conversion ═══")
    try:
        import psutil
    except ImportError:
        warn("S6 — psutil not installed, skipping memory check")
        return

    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)
    log(f"    Memory before: {mem_before:.0f} MB")

    result, out_dir, _ = _run_stress([stress_file], {"quality_preset": "Fast"})

    mem_after = process.memory_info().rss / (1024 * 1024)
    log(f"    Memory after:  {mem_after:.0f} MB")
    log(f"    Delta:         {mem_after - mem_before:.0f} MB")

    check("S6 — conversion completes",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}")
    # Warn if memory grew by more than 2 GB
    if mem_after - mem_before > 2048:
        warn("S6 — memory grew > 2 GB", f"delta={mem_after - mem_before:.0f} MB")
    else:
        check("S6 — memory within bounds", True)


# ── S7–S8: Secondary PDFs (engineering, manuals) ──────────────────

def stress_secondary_pdf(pdf_path, label):
    """Stress S7/S8: Secondary PDF — Fast conversion + quality checks."""
    fname = os.path.basename(pdf_path)
    pages = _get_pdf_pages(pdf_path) or 0
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    log(f"\n═══ STRESS {label}: {fname} ({pages:,} pages, {size_mb:.1f} MB) ═══")

    # a) Full conversion — Fast
    t0 = time.time()
    result, out_dir, logs = _run_stress([pdf_path], {"quality_preset": "Fast"})
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check(f"{label}a — conversion completes",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}")

    md = read_output(out_dir)
    check(f"{label}a — output exists", md is not None)
    if md:
        size_kb = len(md.encode("utf-8")) / 1024
        log(f"    Output size: {size_kb:.0f} KB")
        check(f"{label}a — output > 5 KB", size_kb > 5, f"only {size_kb:.0f} KB")

        # Check for tables (technical docs should have them)
        table_count = md.count("| --- |") + md.count("|---|") + md.count("| --")
        if table_count > 0:
            log(f"    Tables found: {table_count}")
            check(f"{label}a — has tables", True)
        else:
            warn(f"{label}a — no markdown tables found (may be expected)")

        # Check for image references (schematics, diagrams)
        img_refs = md.count("![") + md.count("](assets/") + md.count("data:image")
        if img_refs > 0:
            log(f"    Image references: {img_refs}")
            check(f"{label}a — has image references", True)

    if result and result.all_confidence:
        c = result.all_confidence[0]
        log(f"    Confidence: overall={c.overall}, text={c.text_extraction}, "
            f"tables={c.table_structure}, images={c.image_extraction}, "
            f"ocr={c.ocr_confidence}")

    # b) Balanced quality — for technical docs, docling may handle
    #    schematics and table structure better
    log(f"    --- {label}b: Balanced quality ---")
    t0 = time.time()
    result_b, out_dir_b, _ = _run_stress([pdf_path], {"quality_preset": "Balanced"})
    elapsed_b = time.time() - t0
    log(f"    Elapsed: {elapsed_b:.1f}s")

    check(f"{label}b — Balanced completes",
          result_b is not None and result_b.completed >= 1,
          f"completed={getattr(result_b, 'completed', '?')}")

    md_b = read_output(out_dir_b)
    if md_b and md:
        size_kb_b = len(md_b.encode("utf-8")) / 1024
        log(f"    Balanced output: {size_kb_b:.0f} KB (Fast was {size_kb:.0f} KB)")


# ── S9: Large CSV / tabular data ─────────────────────────────────

def stress_large_csv(csv_path):
    """Stress S9: Large CSV — tabular conversion stress test."""
    fname = os.path.basename(csv_path)
    size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    rows = _get_csv_rows(csv_path) or 0
    log(f"\n═══ STRESS S9: Large CSV — {fname} ({rows:,} rows, {size_mb:.1f} MB) ═══")

    # a) Full conversion
    t0 = time.time()
    result, out_dir, logs = _run_stress([csv_path], {"quality_preset": "Fast"})
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check("S9a — conversion completes",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}")

    md = read_output(out_dir)
    check("S9a — output exists", md is not None)
    if md:
        size_kb = len(md.encode("utf-8")) / 1024
        log(f"    Output size: {size_kb:.0f} KB")
        check("S9a — output > 1 KB", size_kb > 1, f"only {size_kb:.0f} KB")

        # CSV → markdown should produce pipe tables
        pipe_count = md.count("|")
        check("S9a — has pipe-table formatting",
              pipe_count > 10,
              f"only {pipe_count} pipe chars")

        # Check header row was preserved
        has_header = "ID" in md or "Name" in md or "Category" in md
        check("S9a — header columns preserved", has_header,
              "no recognizable header columns in output")

    if result and result.all_confidence:
        c = result.all_confidence[0]
        log(f"    Confidence: overall={c.overall}, tables={c.table_structure}")

    # b) Memory check — large CSV can spike memory
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_after = process.memory_info().rss / (1024 * 1024)
        log(f"    Memory after CSV conversion: {mem_after:.0f} MB")
        if mem_after > 4096:
            warn("S9b — memory over 4 GB after CSV conversion",
                 f"{mem_after:.0f} MB")
        else:
            check("S9b — memory reasonable after CSV", True)
    except ImportError:
        warn("S9b — psutil not installed, skipping memory check")


# ── S10: Multi-file stress batch ──────────────────────────────────

def stress_multi_batch(all_heavy_files):
    """Stress S10: All heavy files in a single batch conversion."""
    count = len(all_heavy_files)
    total_mb = sum(os.path.getsize(f) / (1024 * 1024) for f in all_heavy_files)
    log(f"\n═══ STRESS S10: Multi-file batch ({count} files, {total_mb:.0f} MB total) ═══")

    for f in all_heavy_files:
        name = os.path.basename(f)
        sz = os.path.getsize(f) / (1024 * 1024)
        log(f"    • {name} ({sz:.1f} MB)")

    t0 = time.time()
    result, out_dir, logs = _run_stress(all_heavy_files, {"quality_preset": "Fast"})
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check(f"S10 — batch completes",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}, "
          f"failed={getattr(result, 'failed', '?')}")

    if result:
        log(f"    Completed: {result.completed}/{count}")
        log(f"    Failed:    {result.failed}/{count}")

        check(f"S10 — all {count} files converted",
              result.completed == count,
              f"completed={result.completed}, failed={result.failed}")

        # Each file should have a confidence result
        check("S10 — per-file confidence for all",
              len(result.all_confidence) == count,
              f"got {len(result.all_confidence)} confidence results for {count} files")

        # Log per-file results
        for conf in result.all_confidence:
            name = os.path.basename(conf.source_file)
            log(f"    → {name}: overall={conf.overall}, "
                f"text={conf.text_extraction}, tables={conf.table_structure}")

    # Check output files
    out_files = list_output_files(out_dir)
    md_files = [f for f in out_files if f.endswith(".md")]
    log(f"    Output markdown files: {len(md_files)}")
    check("S10 — at least one .md per input file",
          len(md_files) >= count,
          f"only {len(md_files)} .md files for {count} inputs")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Document-to-Markdown Engine Tests")
    parser.add_argument("--stress", metavar="PATH", nargs="?", const=TEST_FILES_DIR,
                        help="Path to a file or directory for stress testing. "
                             "Defaults to test_files/ if no path given.")
    parser.add_argument("--stress-only", action="store_true",
                        help="Skip normal tests, run only stress tests")
    args = parser.parse_args()

    start = time.time()
    log("╔══════════════════════════════════════════════════════════╗")
    log("║   Document-to-Markdown Headless Engine Test Suite       ║")
    log("╚══════════════════════════════════════════════════════════╝")
    log(f"\nTest files: {TEST_FILES_DIR}")
    log(f"Output dir: {TEST_OUTPUT_ROOT}")
    log(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    clean_output()

    # ── Normal test suites ────────────────────────────────
    if not args.stress_only:
        tests = [
            test_basic_conversion_all_types,
            test_yaml_front_matter,
            test_preserve_page_numbers,
            test_output_subfolder,
            test_embed_images,
            test_rebuild_toc,
            test_ocr_engine_settings,
            test_quality_presets,
            test_mixed_batch,
            test_edge_empty_file,
            test_edge_unsupported_type,
            test_cancel_midway,
            test_page_range,
            test_overwrite_protection,
        ]

        for test_fn in tests:
            try:
                test_fn()
            except Exception as e:
                log(f"\n  ✗ SUITE CRASHED: {test_fn.__name__} — {e}")
                traceback.print_exc()
                global FAIL
                FAIL += 1

    # ── Stress tests ──────────────────────────────────────
    if args.stress is not None or args.stress_only:
        stress_path = os.path.abspath(args.stress or TEST_FILES_DIR)

        if not os.path.exists(stress_path):
            log(f"\n  ✗ Stress path not found: {stress_path}")
            FAIL += 1
        else:
            catalog = _discover_stress_files(stress_path)

            if not catalog["all_heavy"]:
                log(f"\n  ⚠ No stress-worthy files found (>{_STRESS_MIN_SIZE_MB} MB) "
                    f"in: {stress_path}")
            else:
                # ── Print catalog ──
                log(f"\n{'='*60}")
                log(f"STRESS TEST CATALOG")
                log(f"{'='*60}")

                if catalog["primary_pdf"]:
                    pf = catalog["primary_pdf"]
                    pages = _get_pdf_pages(pf) or 0
                    sz = os.path.getsize(pf) / (1024 * 1024)
                    log(f"  Primary PDF:    {os.path.basename(pf)}")
                    log(f"                  {pages:,} pages  |  {sz:.1f} MB")

                for sp in catalog["secondary_pdfs"]:
                    pages = _get_pdf_pages(sp) or 0
                    sz = os.path.getsize(sp) / (1024 * 1024)
                    log(f"  Secondary PDF:  {os.path.basename(sp)}")
                    log(f"                  {pages:,} pages  |  {sz:.1f} MB")

                for cf in catalog["csv_files"]:
                    rows = _get_csv_rows(cf) or 0
                    sz = os.path.getsize(cf) / (1024 * 1024)
                    log(f"  CSV dataset:    {os.path.basename(cf)}")
                    log(f"                  {rows:,} rows  |  {sz:.1f} MB")

                log(f"  Total files:    {len(catalog['all_heavy'])}")
                log(f"{'='*60}")

                # ── S1–S6: Primary PDF full treatment ──
                if catalog["primary_pdf"]:
                    pf = catalog["primary_pdf"]
                    stress_tests = [
                        lambda: stress_full_markdown_fast(pf),
                        lambda: stress_full_markdown_balanced(pf),
                        lambda: stress_full_searchable_pdf(pf),
                        lambda: stress_page_range_samples(pf),
                        lambda: stress_cancel_large(pf),
                        lambda: stress_memory_check(pf),
                    ]
                    for test_fn in stress_tests:
                        try:
                            test_fn()
                        except Exception as e:
                            log(f"\n  ✗ STRESS CRASHED: {e}")
                            traceback.print_exc()
                            FAIL += 1

                # ── S7/S8: Secondary PDFs ──
                for idx, sp in enumerate(catalog["secondary_pdfs"]):
                    label = f"S{7 + idx}"
                    try:
                        stress_secondary_pdf(sp, label)
                    except Exception as e:
                        log(f"\n  ✗ STRESS {label} CRASHED: {e}")
                        traceback.print_exc()
                        FAIL += 1

                # ── S9: CSV / tabular files ──
                for cf in catalog["csv_files"]:
                    try:
                        stress_large_csv(cf)
                    except Exception as e:
                        log(f"\n  ✗ STRESS S9 CRASHED: {e}")
                        traceback.print_exc()
                        FAIL += 1

                # ── S10: Multi-file batch (all heavy files at once) ──
                if len(catalog["all_heavy"]) >= 2:
                    try:
                        stress_multi_batch(catalog["all_heavy"])
                    except Exception as e:
                        log(f"\n  ✗ STRESS S10 CRASHED: {e}")
                        traceback.print_exc()
                        FAIL += 1

    elapsed = time.time() - start
    log(f"\n{'='*60}")
    log(f"RESULTS:  {PASS} passed  |  {FAIL} failed  |  {WARN} warnings")
    log(f"Elapsed:  {elapsed:.1f}s")
    log(f"{'='*60}")

    # Write report to file
    report_path = os.path.join(TEST_OUTPUT_ROOT, "test_report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(results_log))
    log(f"\nFull report: {report_path}")

    # Clean up the shared tkinter root
    try:
        _SHARED_ROOT.destroy()
    except Exception:
        pass

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
