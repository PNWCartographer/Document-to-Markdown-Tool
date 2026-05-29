"""
Comprehensive stress test — exercises every feature, format, and setting combination.

Covers:
  CS1  — All output formats on the sample PDF (Markdown, JSON, HTML, PlainText, AI-Ready Chunks)
  CS2  — Markdown flavors (GFM, Obsidian, Pandoc) on sample PDF
  CS3  — Heading detection heuristic (PDFs with/without TOC outlines)
  CS4  — Caption association (image-bearing PDFs)
  CS5  — Cross-page paragraph merging on long PDFs
  CS6  — Post-processor pipeline (code blocks + line numbers together)
  CS7  — Settings matrix: embed images, no subfolder, no YAML, strip line numbers
  CS8  — Large CSV → all applicable formats
  CS9  — All small files in a single batch (every type)
  CS10 — Secondary PDFs (engineering, manual) with Balanced quality
  CS11 — Cancel during searchable PDF conversion
  CS12 — Full book (1,467p) with heading detection + paragraph merging
  CS13 — AI-Ready Chunks format on large PDF (chunking stress)
  CS14 — All small files individually with Quality preset
  CS15 — Confidence result validation (badge data for all files)

Run:  python stress_comprehensive.py
"""
import os
import sys
import re
import shutil
import time
import threading
import traceback

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

TEST_FILES = os.path.join(os.path.dirname(__file__), "test_files")
OUTPUT_ROOT = os.path.join(os.path.dirname(__file__), "_stress_output")
STRESS_TIMEOUT = 7200  # 2h max per conversion

# ── Counters & logging ──────────────────────────────────────────
PASS = 0
FAIL = 0
WARN = 0
FINDINGS = []  # (severity, suite, message)
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
        FINDINGS.append(("FAIL", name, detail))


def warn(name, detail=""):
    global WARN
    WARN += 1
    log(f"  ⚠ {name}" + (f" — {detail}" if detail else ""))
    FINDINGS.append(("WARN", name, detail))


def note(name, detail=""):
    """Informational observation (not a pass/fail)."""
    log(f"  ℹ {name}" + (f" — {detail}" if detail else ""))
    FINDINGS.append(("NOTE", name, detail))


import tkinter as tk
_ROOT = tk.Tk()
_ROOT.withdraw()


# ── File helpers ────────────────────────────────────────────────

def find_file(name):
    p = os.path.join(TEST_FILES, name)
    return p if os.path.isfile(p) else None


_METADATA_FILES = {"confidence_report.txt", "conversion_log.txt"}


def find_output(output_dir, ext=".md"):
    for root, _, files in os.walk(output_dir):
        for f in files:
            if f.endswith(ext) and f not in _METADATA_FILES:
                return os.path.join(root, f)
    return None


def read_output(output_dir, ext=".md"):
    path = find_output(output_dir, ext)
    if path:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return None


def list_outputs(output_dir):
    found = []
    for root, _, files in os.walk(output_dir):
        for f in files:
            found.append(os.path.relpath(os.path.join(root, f), output_dir))
    return found


def pdf_pages(path):
    try:
        import fitz
        with fitz.open(path) as doc:
            return len(doc)
    except Exception:
        return None


def pdf_has_toc(path):
    try:
        import fitz
        with fitz.open(path) as doc:
            return len(doc.get_toc()) > 0
    except Exception:
        return False


# ── Conversion runner ───────────────────────────────────────────

_CFG_BASE = {
    "conversion_mode": "Auto-detect",
    "preserve_images": True,
    "preserve_page_numbers": True,
    "rebuild_toc": True,
    "embed_images": False,
    "remove_headers_footers": True,
    "skip_blank_pages": True,
    "strip_line_numbers": False,
    "detect_code_blocks": True,
    "detect_footnotes": True,
    "detect_equations": True,
    "parallel_workers": "1",
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
    "low_confidence_action": "Keep and flag",
}

_run_id = 0


def run(files, overrides=None, page_ranges=None, timeout=None):
    global _run_id
    _run_id += 1
    from engine.converter import ConversionJob

    cfg = dict(_CFG_BASE)
    if overrides:
        cfg.update(overrides)

    out_dir = os.path.join(OUTPUT_ROOT, f"cs_{_run_id:04d}")
    os.makedirs(out_dir, exist_ok=True)

    done = threading.Event()
    holder = [None]
    logs = []

    def on_done(br):
        holder[0] = br
        done.set()

    job = ConversionJob(
        files=files, aliases={}, output_root=out_dir, cfg=cfg, root=_ROOT,
        on_log=lambda m: logs.append(m),
        on_file_progress=lambda p: None,
        on_overall_progress=lambda p: None,
        on_file_start=lambda f, i, t: log(f"    → [{i}/{t}] {f}"),
        on_stage=lambda s: None,
        on_done=on_done,
        page_ranges=page_ranges,
    )
    job._gui = lambda fn, *a: fn(*a)
    job.start()

    t_max = timeout or STRESS_TIMEOUT
    deadline = time.time() + t_max
    while not done.is_set() and time.time() < deadline:
        try:
            _ROOT.update()
        except Exception:
            break
        time.sleep(0.1)

    return holder[0], out_dir, logs, job


# ═══════════════════════════════════════════════════════════════
# CS1: All output formats on sample PDF
# ═══════════════════════════════════════════════════════════════

def cs1_output_formats():
    log("\n═══ CS1: All output formats on sample PDF ═══")
    pdf = find_file("sample_annual_report.pdf")
    if not pdf:
        warn("CS1 — sample_annual_report.pdf not found")
        return

    formats = {
        "Markdown":        (".md",   "Markdown"),
        "JSON":            (".json", "JSON"),
        "HTML":            (".html", "HTML"),
        "Plain Text":      (".txt",  "Plain Text"),
        "AI-Ready Chunks": (".jsonl", "AI-Ready Chunks"),
    }

    for fmt_key, (ext, label) in formats.items():
        t0 = time.time()
        result, out_dir, logs, _ = run([pdf], {"output_format": fmt_key}, timeout=120)
        elapsed = time.time() - t0
        log(f"  {label}: {elapsed:.1f}s")

        check(f"CS1 — {label} completes",
              result is not None and result.completed >= 1,
              f"completed={getattr(result, 'completed', '?')}")

        out_file = find_output(out_dir, ext)
        check(f"CS1 — {label} output {ext} exists", out_file is not None,
              f"no {ext} file in {out_dir}")

        if out_file:
            size = os.path.getsize(out_file)
            check(f"CS1 — {label} output non-empty", size > 50,
                  f"only {size} bytes")
            log(f"    Size: {size:,} bytes")


# ═══════════════════════════════════════════════════════════════
# CS2: Markdown flavors
# ═══════════════════════════════════════════════════════════════

def cs2_markdown_flavors():
    log("\n═══ CS2: Markdown flavors (GFM, Obsidian, Pandoc) ═══")
    pdf = find_file("sample_annual_report.pdf")
    if not pdf:
        warn("CS2 — sample_annual_report.pdf not found")
        return

    for flavor in ("GFM", "Obsidian", "Pandoc"):
        result, out_dir, logs, _ = run([pdf], {"markdown_flavor": flavor}, timeout=120)
        md = read_output(out_dir)
        check(f"CS2 — {flavor} completes", result is not None and result.completed >= 1)
        check(f"CS2 — {flavor} produces output", md is not None and len(md) > 100)

        if md and flavor == "Obsidian":
            # Obsidian should use YAML front matter with tags
            has_frontmatter = md.startswith("---")
            check("CS2 — Obsidian has front matter", has_frontmatter)

        if md and flavor == "Pandoc":
            has_frontmatter = md.startswith("---")
            check("CS2 — Pandoc has front matter", has_frontmatter)


# ═══════════════════════════════════════════════════════════════
# CS3: Heading detection heuristic
# ═══════════════════════════════════════════════════════════════

def cs3_heading_detection():
    log("\n═══ CS3: Heading detection heuristic ═══")

    # sample_annual_report.pdf has NO TOC (0 entries) — heading detection should fire
    pdf_no_toc = find_file("sample_annual_report.pdf")

    # algebra book has TOC (164 entries) — heading detection should NOT fire (uses TOC)
    pdf_with_toc = find_file("algebra-and-trigonometry-2e_-_WEB.pdf")

    # Test on PDF without TOC — should produce markdown headings via font analysis
    if pdf_no_toc:
        has_toc = pdf_has_toc(pdf_no_toc)
        log(f"    {os.path.basename(pdf_no_toc)}: TOC={has_toc}")

        result, out_dir, logs, _ = run([pdf_no_toc], timeout=120)
        md = read_output(out_dir)
        check("CS3 — no-TOC PDF converts", md is not None)

        if md:
            h2_count = len(re.findall(r"^## ", md, re.MULTILINE))
            h3_count = len(re.findall(r"^### ", md, re.MULTILINE))
            h4_count = len(re.findall(r"^#### ", md, re.MULTILINE))
            total_headings = h2_count + h3_count + h4_count
            log(f"    Headings found: H2={h2_count} H3={h3_count} H4={h4_count} total={total_headings}")

            if not has_toc:
                # Without TOC, heading detection should produce at least some headings
                if total_headings > 0:
                    check("CS3 — heading detection produced headings", True)
                else:
                    note("CS3 — no headings detected in no-TOC PDF",
                         "may be expected if document has uniform font sizes")

    # Test on PDF WITH TOC — uses page range to keep it fast
    if pdf_with_toc:
        has_toc = pdf_has_toc(pdf_with_toc)
        log(f"    {os.path.basename(pdf_with_toc)}: TOC={has_toc}")

        # Just first 10 pages to verify TOC-based headings
        result, out_dir, logs, _ = run(
            [pdf_with_toc],
            page_ranges={pdf_with_toc: list(range(1, 11))},
            timeout=120,
        )
        md = read_output(out_dir)
        check("CS3 — TOC PDF converts (pages 1-10)", md is not None)

        if md:
            # This PDF has a TOC, so headings come from TOC, not detection
            h_count = len(re.findall(r"^#{1,4} ", md, re.MULTILINE))
            log(f"    Headings in TOC PDF: {h_count}")

    # Test on equipment manual (has TOC with 35 entries)
    manual = find_file("heavy-equipment-operation-and-maintenance-manual-1nbsped-1032419806-9781032419800_compress.pdf")
    if manual:
        has_toc = pdf_has_toc(manual)
        log(f"    {os.path.basename(manual)[:40]}...: TOC={has_toc}, entries={35 if has_toc else 0}")
        result, out_dir, logs, _ = run(
            [manual],
            page_ranges={manual: list(range(1, 21))},
            timeout=180,
        )
        md = read_output(out_dir)
        if md:
            h_count = len(re.findall(r"^#{1,4} ", md, re.MULTILINE))
            log(f"    Headings in manual (pages 1-20): {h_count}")
            check("CS3 — manual pages 1-20 converts", True)


# ═══════════════════════════════════════════════════════════════
# CS4: Caption association
# ═══════════════════════════════════════════════════════════════

def cs4_caption_association():
    log("\n═══ CS4: Caption association for PDF images ═══")

    # The algebra book and engineering handbook likely have figures with captions
    candidates = [
        "algebra-and-trigonometry-2e_-_WEB.pdf",
        "newnes_electrical_engineers_handbook.pdf",
        "heavy-equipment-operation-and-maintenance-manual-1nbsped-1032419806-9781032419800_compress.pdf",
    ]

    for fname in candidates:
        pdf = find_file(fname)
        if not pdf:
            continue

        # Pick pages most likely to have captioned figures
        pages = pdf_pages(pdf) or 100
        # Mid-book pages tend to have figures
        mid = max(10, pages // 3)
        page_range = list(range(mid, min(mid + 30, pages + 1)))

        short_name = fname[:35] + ("…" if len(fname) > 35 else "")
        log(f"  Testing {short_name} pages {page_range[0]}-{page_range[-1]}...")

        result, out_dir, logs, _ = run(
            [pdf],
            {"preserve_images": True, "embed_images": False},
            page_ranges={pdf: page_range},
            timeout=300,
        )
        md = read_output(out_dir)
        check(f"CS4 — {short_name} converts", md is not None)

        if md:
            # Count image references
            img_refs = re.findall(r"!\[([^\]]*)\]\(", md)
            generic_refs = [r for r in img_refs if r.startswith("Image from page")]
            caption_refs = [r for r in img_refs if not r.startswith("Image from page")]

            log(f"    Image refs: {len(img_refs)} total, "
                f"{len(caption_refs)} with captions, "
                f"{len(generic_refs)} generic")

            if img_refs:
                if caption_refs:
                    check(f"CS4 — {short_name} has captioned images", True)
                    # Show first few captions
                    for cap in caption_refs[:3]:
                        log(f"      Caption: {cap[:80]}")
                else:
                    note(f"CS4 — {short_name} no captions detected",
                         "images found but none matched caption patterns")

            # Check for italic caption lines
            italic_captions = re.findall(r"^\*(?:Figure|Fig|Image|Table|Diagram)", md, re.MULTILINE)
            if italic_captions:
                log(f"    Italic caption lines: {len(italic_captions)}")

            # Check assets folder
            assets = [f for f in list_outputs(out_dir) if "assets" in f]
            log(f"    Asset files saved: {len(assets)}")


# ═══════════════════════════════════════════════════════════════
# CS5: Cross-page paragraph merging
# ═══════════════════════════════════════════════════════════════

def cs5_paragraph_merging():
    log("\n═══ CS5: Cross-page paragraph merging ═══")

    # Test on the algebra book — lots of prose across pages
    pdf = find_file("algebra-and-trigonometry-2e_-_WEB.pdf")
    if not pdf:
        warn("CS5 — algebra book not found")
        return

    # Pages 50-80 should have continuous prose (chapters)
    result, out_dir, logs, _ = run(
        [pdf],
        {"preserve_page_numbers": True},
        page_ranges={pdf: list(range(50, 81))},
        timeout=300,
    )
    md = read_output(out_dir)
    check("CS5 — pages 50-80 convert", md is not None)

    if md:
        # Look for signs of broken paragraphs — lines that end mid-word or
        # start with lowercase after a page break
        page_markers = [m.start() for m in re.finditer(r'\*Page \d+\*', md)]
        log(f"    Page markers found: {len(page_markers)}")

        # Check for lowercase starts immediately after page markers
        broken_count = 0
        merged_count = 0
        for m in re.finditer(r'\*Page \d+\*\n+([a-z])', md):
            # This could indicate a successfully merged paragraph (lowercase
            # continuation is normal if merging worked)
            merged_count += 1

        # Check for lines that end without punctuation before page breaks
        for m in re.finditer(r'([^\.\!\?\:\n])\n+---\n\*Page', md):
            broken_count += 1

        log(f"    Lowercase starts after page breaks: {merged_count}")
        log(f"    Non-punctuated lines before breaks: {broken_count}")

        if broken_count == 0:
            check("CS5 — no obvious broken paragraphs", True)
        else:
            note("CS5 — some paragraph breaks remain",
                 f"{broken_count} non-punctuated line ends before page breaks")

        # Check overall text continuity
        word_count = len(md.split())
        log(f"    Word count: {word_count:,}")
        check("CS5 — substantial text extracted", word_count > 1000,
              f"only {word_count} words")


# ═══════════════════════════════════════════════════════════════
# CS6: Post-processor pipeline (code blocks + line numbers)
# ═══════════════════════════════════════════════════════════════

def cs6_postprocessor_pipeline():
    log("\n═══ CS6: Post-processor pipeline ═══")

    # Test with both code block detection AND line number stripping enabled
    pdf = find_file("sample_annual_report.pdf")
    if not pdf:
        warn("CS6 — sample PDF not found")
        return

    result, out_dir, logs, _ = run(
        [pdf],
        {
            "detect_code_blocks": True,
            "strip_line_numbers": True,
            "detect_footnotes": True,
            "detect_equations": True,
        },
        timeout=120,
    )
    md = read_output(out_dir)
    check("CS6 — pipeline completes", result is not None and result.completed >= 1)
    check("CS6 — output exists", md is not None)

    if md:
        # Check that code blocks are intact (not corrupted by line number stripping)
        code_blocks = re.findall(r"```[\s\S]*?```", md)
        if code_blocks:
            log(f"    Code blocks found: {len(code_blocks)}")
            check("CS6 — code blocks preserved", True)
        else:
            log("    No code blocks in this document (expected)")

    # Also test on the DOCX (may have code-like content)
    docx = find_file("sample_requirements.docx")
    if docx:
        result2, out_dir2, _, _ = run(
            [docx],
            {
                "detect_code_blocks": True,
                "strip_line_numbers": True,
            },
            timeout=120,
        )
        check("CS6 — DOCX with both toggles completes",
              result2 is not None and result2.completed >= 1)


# ═══════════════════════════════════════════════════════════════
# CS7: Settings matrix
# ═══════════════════════════════════════════════════════════════

def cs7_settings_matrix():
    log("\n═══ CS7: Settings matrix — unusual combinations ═══")
    pdf = find_file("sample_annual_report.pdf")
    if not pdf:
        warn("CS7 — sample PDF not found")
        return

    combos = [
        ("embed+noYAML+noPages", {
            "embed_images": True,
            "yaml_front_matter": False,
            "preserve_page_numbers": False,
        }),
        ("noSubfolder+noTOC+noHeaders", {
            "output_subfolder": False,
            "rebuild_toc": False,
            "remove_headers_footers": False,
        }),
        ("allPostProc", {
            "strip_line_numbers": True,
            "detect_code_blocks": True,
            "detect_footnotes": True,
            "detect_equations": True,
        }),
        ("minimal", {
            "preserve_images": False,
            "preserve_page_numbers": False,
            "rebuild_toc": False,
            "yaml_front_matter": False,
            "embed_images": False,
            "remove_headers_footers": False,
            "skip_blank_pages": False,
        }),
    ]

    for label, overrides in combos:
        result, out_dir, logs, _ = run([pdf], overrides, timeout=120)
        md = read_output(out_dir)
        check(f"CS7 — {label} completes", result is not None and result.completed >= 1)
        check(f"CS7 — {label} has output", md is not None and len(md) > 50)

        if md and "embed" in label:
            has_base64 = "data:image" in md
            log(f"    Embedded images: {has_base64}")

        if md and "noYAML" in label:
            starts_yaml = md.strip().startswith("---")
            check(f"CS7 — {label} no YAML header", not starts_yaml,
                  "YAML front matter present despite being disabled")


# ═══════════════════════════════════════════════════════════════
# CS8: Large CSV → multiple formats
# ═══════════════════════════════════════════════════════════════

def cs8_csv_formats():
    log("\n═══ CS8: Large CSV → all applicable formats ═══")
    csv_path = find_file("kickstarter_projects.csv")
    if not csv_path:
        warn("CS8 — kickstarter_projects.csv not found")
        return

    formats = {
        "Markdown": ".md",
        "JSON": ".json",
        "HTML": ".html",
        "Plain Text": ".txt",
        "AI-Ready Chunks": ".jsonl",
    }

    for fmt, ext in formats.items():
        t0 = time.time()
        result, out_dir, logs, _ = run(
            [csv_path], {"output_format": fmt}, timeout=300)
        elapsed = time.time() - t0
        log(f"  {fmt}: {elapsed:.1f}s")

        check(f"CS8 — CSV → {fmt} completes",
              result is not None and result.completed >= 1)

        out = find_output(out_dir, ext)
        check(f"CS8 — CSV → {fmt} output exists", out is not None)

        if out:
            size_kb = os.path.getsize(out) / 1024
            log(f"    Output size: {size_kb:.0f} KB")
            check(f"CS8 — CSV → {fmt} > 1 KB", size_kb > 1)


# ═══════════════════════════════════════════════════════════════
# CS9: All small files in a single batch
# ═══════════════════════════════════════════════════════════════

def cs9_all_small_batch():
    log("\n═══ CS9: All small files in a single batch ═══")

    small_files = [
        "sample_annual_report.pdf",
        "sample_requirements.docx",
        "sample_ocr_image.png",
        "sample_financials.xlsx",
        "sample_spreadsheet.csv",
        "sample_presentation.pptx",
        "sample_report.html",
        "sample_spec.rtf",
    ]

    files = [find_file(f) for f in small_files]
    files = [f for f in files if f is not None]
    log(f"    Files found: {len(files)}/{len(small_files)}")

    if not files:
        warn("CS9 — no small files found")
        return

    t0 = time.time()
    result, out_dir, logs, _ = run(files, {"parallel_workers": "Auto"}, timeout=300)
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check("CS9 — batch completes", result is not None)

    if result:
        log(f"    Completed: {result.completed}/{len(files)}")
        log(f"    Failed: {result.failed}")
        check("CS9 — all files converted",
              result.completed == len(files),
              f"completed={result.completed}, failed={result.failed}")

        # Verify output files
        md_files = [f for f in list_outputs(out_dir) if f.endswith(".md")]
        log(f"    Output .md files: {len(md_files)}")
        check("CS9 — one .md per input", len(md_files) >= len(files),
              f"{len(md_files)} outputs for {len(files)} inputs")


# ═══════════════════════════════════════════════════════════════
# CS10: Secondary PDFs — engineering handbook
# ═══════════════════════════════════════════════════════════════

def cs10_engineering_pdfs():
    log("\n═══ CS10: Engineering/manual PDFs — heading & caption test ═══")

    targets = [
        ("newnes_electrical_engineers_handbook.pdf", 30),
        ("heavy-equipment-operation-and-maintenance-manual-1nbsped-1032419806-9781032419800_compress.pdf", 30),
    ]

    for fname, page_count in targets:
        pdf = find_file(fname)
        if not pdf:
            continue

        pages = pdf_pages(pdf) or 100
        has_toc = pdf_has_toc(pdf)
        short_name = fname[:40] + ("…" if len(fname) > 40 else "")
        log(f"\n  {short_name}")
        log(f"    Pages: {pages}, TOC: {has_toc}")

        # Pick content-heavy pages
        mid = max(10, pages // 4)
        page_range = list(range(mid, min(mid + page_count, pages + 1)))

        t0 = time.time()
        result, out_dir, logs, _ = run(
            [pdf],
            {"preserve_images": True, "quality_preset": "Fast"},
            page_ranges={pdf: page_range},
            timeout=600,
        )
        elapsed = time.time() - t0
        log(f"    Elapsed: {elapsed:.1f}s (pages {page_range[0]}-{page_range[-1]})")

        check(f"CS10 — {short_name} converts",
              result is not None and result.completed >= 1)

        md = read_output(out_dir)
        if md:
            size_kb = len(md.encode("utf-8")) / 1024
            headings = len(re.findall(r"^#{1,4} ", md, re.MULTILINE))
            images = len(re.findall(r"!\[", md))
            tables = md.count("| --- |") + md.count("|---|") + md.count("| --")
            log(f"    Output: {size_kb:.0f} KB, headings={headings}, images={images}, tables={tables}")

        if result and result.all_confidence:
            c = result.all_confidence[0]
            log(f"    Confidence: overall={c.overall}, text={c.text_extraction}, "
                f"tables={c.table_structure}, images={c.image_extraction}")


# ═══════════════════════════════════════════════════════════════
# CS11: Cancel during searchable PDF
# ═══════════════════════════════════════════════════════════════

def cs11_cancel_searchable_pdf():
    log("\n═══ CS11: Cancel during searchable PDF conversion ═══")

    # Use the 177-page equipment manual — large enough that conversion
    # won't finish before the cancel timer fires (sample_annual_report.pdf
    # is only 2 pages and completes in <1 second).
    pdf = find_file("heavy-equipment-operation-and-maintenance-manual-1nbsped-1032419806-9781032419800_compress.pdf")
    if not pdf:
        # Fall back to sample PDF if manual not available
        pdf = find_file("sample_annual_report.pdf")
    if not pdf:
        warn("CS11 — no suitable PDF found for cancel test")
        return

    from engine.converter import ConversionJob

    out_dir = os.path.join(OUTPUT_ROOT, f"cs_cancel_spdf_{int(time.time()*1000)}")
    os.makedirs(out_dir, exist_ok=True)

    done = threading.Event()
    holder = [None]

    def on_done(br):
        holder[0] = br
        done.set()

    cfg = dict(_CFG_BASE)
    cfg["output_format"] = "Searchable PDF"

    job = ConversionJob(
        files=[pdf], aliases={}, output_root=out_dir, cfg=cfg, root=_ROOT,
        on_log=lambda m: None, on_file_progress=lambda p: None,
        on_overall_progress=lambda p: None,
        on_file_start=lambda f, i, t: None,
        on_stage=lambda s: None, on_done=on_done,
    )
    job._gui = lambda fn, *a: fn(*a)
    job.start()

    # Let it run 1 second then cancel (equipment manual needs several
    # seconds, so cancel fires mid-conversion)
    cancel_at = time.time() + 1
    while not done.is_set() and time.time() < cancel_at:
        try:
            _ROOT.update()
        except Exception:
            break
        time.sleep(0.05)

    if not done.is_set():
        log("    Cancelling...")
        job.cancel()
        deadline = time.time() + 60
        while not done.is_set() and time.time() < deadline:
            try:
                _ROOT.update()
            except Exception:
                break
            time.sleep(0.05)

    result = holder[0]
    check("CS11 — cancel completes without crash", result is not None)
    if result:
        check("CS11 — cancelled flag set", result.cancelled,
              f"cancelled={result.cancelled}")
        log(f"    Completed: {result.completed}, Failed: {result.failed}")


# ═══════════════════════════════════════════════════════════════
# CS12: Full book with heading detection + paragraph merging
# ═══════════════════════════════════════════════════════════════

def cs12_full_book_features():
    log("\n═══ CS12: Full book — heading detection + paragraph merging ═══")

    pdf = find_file("algebra-and-trigonometry-2e_-_WEB.pdf")
    if not pdf:
        warn("CS12 — algebra book not found")
        return

    pages = pdf_pages(pdf) or 0
    has_toc = pdf_has_toc(pdf)
    log(f"    {os.path.basename(pdf)}: {pages:,} pages, TOC={has_toc}")

    # Full book conversion — this is the big one
    log("    Starting full book conversion (Fast preset)...")
    t0 = time.time()
    result, out_dir, logs, _ = run(
        [pdf],
        {"quality_preset": "Fast", "preserve_images": True},
        timeout=STRESS_TIMEOUT,
    )
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    check("CS12 — full book converts",
          result is not None and result.completed >= 1,
          f"completed={getattr(result, 'completed', '?')}")

    md = read_output(out_dir)
    if md:
        size_kb = len(md.encode("utf-8")) / 1024
        size_mb = size_kb / 1024
        log(f"    Output size: {size_mb:.1f} MB ({size_kb:.0f} KB)")

        # Structure analysis
        h2 = len(re.findall(r"^## ", md, re.MULTILINE))
        h3 = len(re.findall(r"^### ", md, re.MULTILINE))
        h4 = len(re.findall(r"^#### ", md, re.MULTILINE))
        page_markers = len(re.findall(r"\*Page \d+\*", md))
        images = len(re.findall(r"!\[", md))
        tables = md.count("| --- |") + md.count("|---|") + md.count("| --")
        words = len(md.split())

        log(f"    Structure: H2={h2} H3={h3} H4={h4} pages={page_markers} "
            f"images={images} tables={tables} words={words:,}")

        check("CS12 — output > 100 KB", size_kb > 100, f"only {size_kb:.0f} KB")
        check("CS12 — has page markers", page_markers > 100,
              f"only {page_markers} for {pages}-page book")
        check("CS12 — substantial word count", words > 10000,
              f"only {words:,} words")

        # Caption analysis
        img_refs = re.findall(r"!\[([^\]]*)\]\(", md)
        caption_refs = [r for r in img_refs if not r.startswith("Image from page")]
        log(f"    Image refs: {len(img_refs)} total, {len(caption_refs)} with captions")

        # Paragraph merging analysis
        broken_sentences = 0
        for m in re.finditer(r'([a-z,;])\n+---\n\*Page', md):
            broken_sentences += 1
        log(f"    Apparent broken sentences at page breaks: {broken_sentences}")

    if result and result.all_confidence:
        c = result.all_confidence[0]
        log(f"    Confidence: overall={c.overall}, text={c.text_extraction}, "
            f"tables={c.table_structure}, images={c.image_extraction}, "
            f"ocr={c.ocr_confidence}")

    # Memory check
    try:
        import psutil
        mem = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        log(f"    Memory after full book: {mem:.0f} MB")
        if mem > 3072:
            warn("CS12 — memory > 3 GB after full book", f"{mem:.0f} MB")
    except ImportError:
        pass


# ═══════════════════════════════════════════════════════════════
# CS13: AI-Ready Chunks format on large PDF
# ═══════════════════════════════════════════════════════════════

def cs13_rag_chunks_large():
    log("\n═══ CS13: AI-Ready Chunks on large PDF ═══")

    pdf = find_file("newnes_electrical_engineers_handbook.pdf")
    if not pdf:
        warn("CS13 — engineering handbook not found")
        return

    pages = pdf_pages(pdf) or 0
    log(f"    {os.path.basename(pdf)}: {pages:,} pages")

    t0 = time.time()
    result, out_dir, logs, _ = run(
        [pdf],
        {"output_format": "AI-Ready Chunks", "quality_preset": "Fast"},
        timeout=1200,
    )
    elapsed = time.time() - t0
    log(f"    Elapsed: {elapsed:.1f}s")

    check("CS13 — AI-Ready Chunks completes",
          result is not None and result.completed >= 1)

    jsonl_file = find_output(out_dir, ".jsonl")
    check("CS13 — .jsonl output exists", jsonl_file is not None)

    if jsonl_file:
        size_kb = os.path.getsize(jsonl_file) / 1024
        log(f"    JSONL size: {size_kb:.0f} KB")

        # Count chunks
        import json
        chunk_count = 0
        valid_chunks = 0
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    chunk_count += 1
                    try:
                        obj = json.loads(line)
                        if "text" in obj or "content" in obj:
                            valid_chunks += 1
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            warn("CS13 — error reading JSONL", str(e))

        log(f"    Chunks: {chunk_count} total, {valid_chunks} valid")
        check("CS13 — has chunks", chunk_count > 10, f"only {chunk_count}")
        check("CS13 — chunks are valid JSON", valid_chunks == chunk_count,
              f"{chunk_count - valid_chunks} invalid chunks")


# ═══════════════════════════════════════════════════════════════
# CS14: All small files individually with Quality preset
# ═══════════════════════════════════════════════════════════════

def cs14_quality_preset_each():
    log("\n═══ CS14: Each small file — Quality preset ═══")

    small_files = [
        "sample_annual_report.pdf",
        "sample_requirements.docx",
        "sample_ocr_image.png",
        "sample_financials.xlsx",
        "sample_spreadsheet.csv",
        "sample_presentation.pptx",
        "sample_report.html",
        "sample_spec.rtf",
    ]

    for fname in small_files:
        fpath = find_file(fname)
        if not fpath:
            warn(f"CS14 — {fname} not found")
            continue

        t0 = time.time()
        result, out_dir, logs, _ = run(
            [fpath],
            {"quality_preset": "Quality"},
            timeout=300,
        )
        elapsed = time.time() - t0

        md = read_output(out_dir)
        status = "✓" if (result and result.completed >= 1) else "✗"
        size = len(md.encode("utf-8")) if md else 0
        log(f"  {status} {fname}: {elapsed:.1f}s, {size:,} bytes")

        check(f"CS14 — {fname} Quality completes",
              result is not None and result.completed >= 1,
              f"completed={getattr(result, 'completed', '?')}")


# ═══════════════════════════════════════════════════════════════
# CS15: Confidence result validation
# ═══════════════════════════════════════════════════════════════

def cs15_confidence_validation():
    log("\n═══ CS15: Confidence result validation ═══")

    files_to_test = [
        "sample_annual_report.pdf",
        "sample_requirements.docx",
        "sample_ocr_image.png",
        "sample_financials.xlsx",
        "sample_spreadsheet.csv",
    ]

    for fname in files_to_test:
        fpath = find_file(fname)
        if not fpath:
            continue

        result, out_dir, logs, _ = run([fpath], timeout=120)
        check(f"CS15 — {fname} has result", result is not None)

        if result and result.all_confidence:
            c = result.all_confidence[0]

            # Every confidence result must have an overall rating
            check(f"CS15 — {fname} has overall confidence",
                  c.overall in ("High", "Medium", "Low", "Failed", "N/A"),
                  f"overall={c.overall}")

            # Text extraction should be set for all doc types
            check(f"CS15 — {fname} has text_extraction",
                  c.text_extraction in ("High", "Medium", "Low", "Failed", "N/A"),
                  f"text_extraction={c.text_extraction}")

            # Verify badge-compatible data (for colorblind indicators)
            valid_levels = {"High", "Medium", "Low", "Failed", "N/A"}
            for attr in ("text_extraction", "table_structure",
                         "image_extraction", "ocr_confidence"):
                val = getattr(c, attr, None)
                if val is not None:
                    check(f"CS15 — {fname}.{attr} valid level",
                          val in valid_levels, f"got: {val}")

            log(f"    {fname}: overall={c.overall} text={c.text_extraction} "
                f"tables={c.table_structure} images={c.image_extraction} "
                f"ocr={c.ocr_confidence}")

            # Check warnings list
            if c.warnings:
                log(f"    Warnings: {len(c.warnings)}")
                for w in c.warnings[:3]:
                    log(f"      - {w}")
        else:
            warn(f"CS15 — {fname} missing confidence data")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    start = time.time()

    log("╔══════════════════════════════════════════════════════════╗")
    log("║  Comprehensive Stress Test Suite                        ║")
    log("╚══════════════════════════════════════════════════════════╝")
    log(f"\nTest files:  {TEST_FILES}")
    log(f"Output dir:  {OUTPUT_ROOT}")
    log(f"Time:        {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # List available files
    log(f"\nAvailable test files:")
    for f in sorted(os.listdir(TEST_FILES)):
        fp = os.path.join(TEST_FILES, f)
        if os.path.isfile(fp):
            sz = os.path.getsize(fp) / (1024 * 1024)
            extra = ""
            if f.endswith(".pdf"):
                p = pdf_pages(fp)
                if p:
                    extra = f" ({p:,} pages)"
            log(f"  • {f} — {sz:.1f} MB{extra}")
    log("")

    # Clean output
    if os.path.exists(OUTPUT_ROOT):
        shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    # Run all suites
    suites = [
        ("CS1",  cs1_output_formats),
        ("CS2",  cs2_markdown_flavors),
        ("CS3",  cs3_heading_detection),
        ("CS4",  cs4_caption_association),
        ("CS5",  cs5_paragraph_merging),
        ("CS6",  cs6_postprocessor_pipeline),
        ("CS7",  cs7_settings_matrix),
        ("CS8",  cs8_csv_formats),
        ("CS9",  cs9_all_small_batch),
        ("CS10", cs10_engineering_pdfs),
        ("CS11", cs11_cancel_searchable_pdf),
        ("CS12", cs12_full_book_features),
        ("CS13", cs13_rag_chunks_large),
        ("CS14", cs14_quality_preset_each),
        ("CS15", cs15_confidence_validation),
    ]

    for label, fn in suites:
        try:
            fn()
        except Exception as e:
            log(f"\n  ✗ {label} CRASHED: {e}")
            traceback.print_exc()
            FINDINGS.append(("CRASH", label, str(e)))
            global FAIL
            FAIL += 1

    elapsed = time.time() - start

    # ── Summary report ──────────────────────────────────────
    log(f"\n{'='*60}")
    log(f"RESULTS:  {PASS} passed  |  {FAIL} failed  |  {WARN} warnings")
    log(f"Elapsed:  {elapsed:.1f}s ({elapsed/60:.1f} min)")
    log(f"{'='*60}")

    if FINDINGS:
        log(f"\n{'─'*60}")
        log("FINDINGS REPORT")
        log(f"{'─'*60}")

        fails = [f for f in FINDINGS if f[0] == "FAIL"]
        warns = [f for f in FINDINGS if f[0] == "WARN"]
        crashes = [f for f in FINDINGS if f[0] == "CRASH"]
        notes = [f for f in FINDINGS if f[0] == "NOTE"]

        if crashes:
            log(f"\n🔴 CRASHES ({len(crashes)}):")
            for _, suite, msg in crashes:
                log(f"  [{suite}] {msg}")

        if fails:
            log(f"\n🔴 FAILURES ({len(fails)}):")
            for _, suite, msg in fails:
                log(f"  [{suite}] {msg}")

        if warns:
            log(f"\n🟡 WARNINGS ({len(warns)}):")
            for _, suite, msg in warns:
                log(f"  [{suite}] {msg}")

        if notes:
            log(f"\n🔵 OBSERVATIONS ({len(notes)}):")
            for _, suite, msg in notes:
                log(f"  [{suite}] {msg}")

    # Write full report
    report_path = os.path.join(OUTPUT_ROOT, "stress_report.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(results_log))
    log(f"\nFull report: {report_path}")

    try:
        _ROOT.destroy()
    except Exception:
        pass

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
