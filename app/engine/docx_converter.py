"""
DOCX / DOC converter.

Primary:  docling  — AI-powered layout analysis, handles complex structure,
                     tables, images, and heading hierarchy.
Fallback: mammoth  — clean semantic HTML → Markdown conversion.
Last resort: python-docx — manual DOM traversal to Markdown.

Output preserves heading hierarchy, tables, images (saved to assets/),
and auto-generates a TOC from heading structure when no formal TOC exists.
"""

import os
import re
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput, rows_to_markdown_table, _pad
from .logger import ConversionLogger


def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    language: str = "en",
    preserve_images: bool = True,
    rebuild_toc: bool = True,
    preserve_page_numbers: bool = True,
    use_subfolder: bool = True,
    remove_headers_footers: bool = True,
    skip_blank_pages: bool = True,
    strip_line_numbers: bool = False,
    detect_code_blocks: bool = True,
    detect_footnotes: bool = True,
    detect_equations: bool = True,
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    stage_callback: Optional[Callable[[str], None]] = None,
) -> ConversionOutput:
    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence

    def log_info(msg):
        if logger: logger.info(msg)
    def log_warn(msg):
        if logger: logger.warning(msg)
        confidence.add_warning(msg)
    def progress(p):
        if progress_callback: progress_callback(p)
    def stage(s):
        if stage_callback: stage_callback(s)

    log_info(f"DOCX converter started | file={os.path.basename(source_file)}")
    progress(0.05)

    pp_settings = dict(
        remove_headers_footers=remove_headers_footers,
        skip_blank_pages=skip_blank_pages,
        strip_line_numbers=strip_line_numbers,
        detect_code_blocks=detect_code_blocks,
        detect_footnotes=detect_footnotes,
        detect_equations=detect_equations,
    )

    # Try docling first
    if _docling_available():
        try:
            result = _convert_docling(
                source_file, alias, output_root, preserve_images, rebuild_toc,
                preserve_page_numbers, use_subfolder, output, confidence,
                log_info, log_warn, progress, stage, pp_settings=pp_settings,
            )
            if result:
                return result
        except Exception as e:
            log_warn(f"docling failed: {e} — trying mammoth fallback.")

    progress(0.15)

    # Try mammoth
    if _mammoth_available():
        try:
            return _convert_mammoth(
                source_file, alias, output_root, preserve_images, rebuild_toc,
                use_subfolder, output, confidence, log_info, log_warn, progress,
                pp_settings=pp_settings,
            )
        except Exception as e:
            log_warn(f"mammoth failed: {e} — trying python-docx fallback.")

    progress(0.25)

    # python-docx last resort
    if _python_docx_available():
        return _convert_python_docx(
            source_file, alias, output_root, preserve_images, rebuild_toc,
            use_subfolder, output, confidence, log_info, log_warn, progress,
            pp_settings=pp_settings,
        )

    log_warn("No DOCX conversion engine available.")
    confidence.text_extraction = "Failed"
    confidence.overall = "Failed"
    return output


# ---------------------------------------------------------------------------
# docling path
# ---------------------------------------------------------------------------

def _docling_available() -> bool:
    try:
        import docling  # noqa: F401
        return True
    except ImportError:
        return False


def _convert_docling(
    source_file, alias, output_root, preserve_images, rebuild_toc,
    preserve_page_numbers, use_subfolder, output, confidence, log_info, log_warn, progress,
    stage=None,
    pp_settings: Optional[dict] = None,
) -> Optional[ConversionOutput]:
    from docling.document_converter import DocumentConverter

    log_info("Using docling engine for DOCX.")
    _stage = stage if stage else (lambda s: None)

    # First-run AI-model download messaging (shares the marker with the PDF
    # path — docling models are downloaded once and reused across formats).
    try:
        from .logger import appdata_dir as _appdata_dir
        _marker = os.path.join(_appdata_dir(), ".ai_models_ready")
    except Exception:
        _marker = None
    _first_run = bool(_marker) and not os.path.isfile(_marker)

    if _first_run:
        log_info("First run — downloading AI models (~1-2 GB, one-time setup).")
        _stage("First run: downloading AI models (~1–2 GB). One-time setup — "
               "this may take several minutes…")
    else:
        _stage("Loading AI models…")
    progress(-1.0)  # indeterminate — model load/download exposes no progress hook

    converter = DocumentConverter()
    if not _first_run:
        _stage("Converting document…")
    result = converter.convert(source_file)
    doc = result.document

    # Models are present now — record the marker so future runs skip the
    # first-run download messaging.
    if _first_run and _marker:
        try:
            with open(_marker, "w", encoding="utf-8") as _mf:
                _mf.write("ok")
        except Exception:
            pass
    progress(0.5)

    # Export to Markdown via docling's built-in exporter
    md_text = doc.export_to_markdown()
    if not md_text.strip():
        log_warn("docling returned empty Markdown.")
        return None

    output.engine_used = "docling"

    # Run post-processor pipeline on monolithic text
    pp = pp_settings or {}
    _pp_active = ("strip_line_numbers", "detect_code_blocks", "detect_footnotes", "detect_equations")
    if any(pp.get(k) for k in _pp_active):
        from . import post_processors
        if pp.get("strip_line_numbers", False):
            md_text = post_processors.strip_line_numbers(md_text)
            log_info("Post-processing: stripped line numbers.")
        if pp.get("detect_code_blocks", True):
            md_text = post_processors.detect_code_blocks_in_markdown(md_text)
            log_info("Post-processing: detected code blocks.")
        if pp.get("detect_footnotes", True):
            md_text = post_processors.detect_footnotes_in_markdown(md_text)
            log_info("Post-processing: detected footnotes.")
        if pp.get("detect_equations", True):
            md_text = post_processors.detect_equations(md_text)
            log_info("Post-processing: detected equations.")

    # Extract TOC entries from headings in the Markdown
    if rebuild_toc:
        _extract_toc_from_markdown(md_text, output)

    # Extract and save images
    if preserve_images and output_root:
        _save_docling_images(doc, source_file, alias, output_root, output, log_info, use_subfolder)

    output.add_section(body=md_text)
    progress(0.9)

    # Confidence
    confidence.text_extraction = "High"
    confidence.table_structure = "High"
    confidence.document_order = "High"
    confidence.image_extraction = "High" if preserve_images else "N/A"
    confidence.image_placement = "High" if preserve_images else "N/A"
    confidence.ocr_confidence = "N/A"
    confidence.derive_overall()

    log_info("docling DOCX conversion complete.")
    progress(1.0)
    return output


def _save_docling_images(doc, source_file, alias, output_root, output, log_info, use_subfolder=True):
    from .markdown_writer import assets_dir_for, assets_rel_prefix_for

    assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
    rel_prefix = assets_rel_prefix_for(source_file, alias, use_subfolder)
    os.makedirs(assets_dir, exist_ok=True)

    saved = 0
    try:
        for idx, picture in enumerate(doc.pictures):
            img_filename = f"image_{idx + 1:03d}.png"
            img_path = os.path.join(assets_dir, img_filename)
            try:
                pil_img = picture.get_image(doc)
                if pil_img is None and hasattr(picture, 'image') and picture.image:
                    pil_img = picture.image.pil_image
                if pil_img:
                    try:
                        pil_img.save(img_path)
                        output.asset_paths.append(f"{rel_prefix}{img_filename}")
                        log_info(f"Saved image asset: {img_filename}")
                        saved += 1
                    finally:
                        pil_img.close()
            except Exception:
                pass
    except Exception:
        pass
    log_info(f"DOCX image extraction complete | saved={saved}")


def _extract_toc_from_markdown(md_text: str, output: ConversionOutput) -> None:
    for line in md_text.splitlines():
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            output.add_toc_entry(level, title)


# ---------------------------------------------------------------------------
# mammoth path
# ---------------------------------------------------------------------------

def _mammoth_available() -> bool:
    try:
        import mammoth  # noqa: F401
        return True
    except ImportError:
        return False


def _convert_mammoth(
    source_file, alias, output_root, preserve_images, rebuild_toc,
    use_subfolder, output, confidence, log_info, log_warn, progress,
    pp_settings: Optional[dict] = None,
) -> ConversionOutput:
    import mammoth

    log_info("Using mammoth engine for DOCX.")
    output.engine_used = "mammoth"
    progress(0.2)

    # Style map — preserve heading hierarchy and other common styles
    style_map = """
        p[style-name='Heading 1'] => h1:fresh
        p[style-name='Heading 2'] => h2:fresh
        p[style-name='Heading 3'] => h3:fresh
        p[style-name='Heading 4'] => h4:fresh
        p[style-name='Heading 5'] => h5:fresh
        p[style-name='Heading 6'] => h6:fresh
        p[style-name='Title'] => h1:fresh
        p[style-name='Subtitle'] => h2:fresh
        r[style-name='Strong'] => strong
        r[style-name='Emphasis'] => em
    """

    with open(source_file, "rb") as fh:
        result = mammoth.convert_to_markdown(fh, style_map=style_map)

    md_text = result.value
    for msg in result.messages:
        if msg.type == "warning":
            log_warn(f"mammoth: {msg.message}")

    progress(0.7)

    if not md_text.strip():
        log_warn("mammoth returned empty Markdown.")
        confidence.text_extraction = "Low"
        confidence.overall = "Low"
        return output

    # Run post-processor pipeline on monolithic text
    pp = pp_settings or {}
    _pp_mammoth_keys = ("strip_line_numbers", "detect_code_blocks", "detect_footnotes", "detect_equations")
    if any(pp.get(k) for k in _pp_mammoth_keys):
        from . import post_processors
        if pp.get("strip_line_numbers", False):
            md_text = post_processors.strip_line_numbers(md_text)
            log_info("Post-processing: stripped line numbers.")
        if pp.get("detect_code_blocks", True):
            md_text = post_processors.detect_code_blocks_in_markdown(md_text)
            log_info("Post-processing: detected code blocks.")
        if pp.get("detect_footnotes", True):
            md_text = post_processors.detect_footnotes_in_markdown(md_text)
            log_info("Post-processing: detected footnotes.")
        if pp.get("detect_equations", True):
            md_text = post_processors.detect_equations(md_text)
            log_info("Post-processing: detected equations.")

    if rebuild_toc:
        _extract_toc_from_markdown(md_text, output)

    output.add_section(body=md_text)

    confidence.text_extraction = "High"
    confidence.table_structure = "Medium"
    confidence.document_order = "High"
    confidence.image_extraction = "N/A"
    confidence.image_placement = "N/A"
    confidence.ocr_confidence = "N/A"
    confidence.add_note("mammoth was used — complex tables may need review.")
    confidence.derive_overall()

    log_info("mammoth DOCX conversion complete.")
    progress(1.0)
    return output


# ---------------------------------------------------------------------------
# python-docx last resort
# ---------------------------------------------------------------------------

def _python_docx_available() -> bool:
    try:
        import docx  # noqa: F401
        return True
    except ImportError:
        return False


_HEADING_MAP = {
    "Heading 1": "#",
    "Heading 2": "##",
    "Heading 3": "###",
    "Heading 4": "####",
    "Heading 5": "#####",
    "Heading 6": "######",
    "Title": "#",
    "Subtitle": "##",
}


def _convert_python_docx(
    source_file, alias, output_root, preserve_images, rebuild_toc,
    use_subfolder, output, confidence, log_info, log_warn, progress,
    pp_settings: Optional[dict] = None,
) -> ConversionOutput:
    import docx as python_docx

    log_info("Using python-docx engine for DOCX.")
    output.engine_used = "python-docx"
    progress(0.2)

    try:
        doc = python_docx.Document(source_file)
    except Exception as e:
        log_warn(f"python-docx failed to open file: {e}")
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        return output

    parts = []
    table_count = 0
    heading_count = 0
    paragraph_count = 0

    for element in doc.element.body:
        tag = element.tag.split("}")[-1] if "}" in element.tag else element.tag

        if tag == "p":
            para = python_docx.text.paragraph.Paragraph(element, doc)
            style_name = para.style.name if para.style else ""
            text = para.text.strip()

            if not text:
                parts.append("")
                continue

            if style_name in _HEADING_MAP:
                prefix = _HEADING_MAP[style_name]
                parts.append(f"{prefix} {text}")
                level = prefix.count("#")
                output.add_toc_entry(level, text)
                heading_count += 1
            else:
                # Inline formatting
                line = _para_to_md(para)
                parts.append(line)
                paragraph_count += 1

        elif tag == "tbl":
            try:
                tbl = python_docx.table.Table(element, doc)
                md_table = _docx_table_to_md(tbl)
                parts.append(md_table)
                table_count += 1
            except Exception as e:
                log_warn(f"Could not convert table: {e}")
                parts.append("*[Table could not be converted]*")

    progress(0.8)

    md_text = "\n".join(parts)

    # Run post-processor pipeline on assembled text
    pp = pp_settings or {}
    _pp_docx_keys = ("strip_line_numbers", "detect_code_blocks", "detect_footnotes", "detect_equations")
    if any(pp.get(k) for k in _pp_docx_keys):
        from . import post_processors
        if pp.get("strip_line_numbers", False):
            md_text = post_processors.strip_line_numbers(md_text)
            log_info("Post-processing: stripped line numbers.")
        if pp.get("detect_code_blocks", True):
            md_text = post_processors.detect_code_blocks_in_markdown(md_text)
            log_info("Post-processing: detected code blocks.")
        if pp.get("detect_footnotes", True):
            md_text = post_processors.detect_footnotes_in_markdown(md_text)
            log_info("Post-processing: detected footnotes.")
        if pp.get("detect_equations", True):
            md_text = post_processors.detect_equations(md_text)
            log_info("Post-processing: detected equations.")

    output.add_section(body=md_text)

    confidence.text_extraction = "High" if paragraph_count > 0 else "Low"
    confidence.table_structure = "Medium" if table_count > 0 else "N/A"
    confidence.document_order = "High"
    confidence.image_extraction = "N/A"
    confidence.image_placement = "N/A"
    confidence.ocr_confidence = "N/A"
    confidence.add_note("python-docx used — limited formatting fidelity.")
    confidence.derive_overall()

    log_info(f"python-docx conversion complete | headings={heading_count} paragraphs={paragraph_count} tables={table_count}")
    progress(1.0)
    return output


def _para_to_md(para) -> str:
    parts = []
    for run in para.runs:
        text = run.text
        if not text:
            continue
        if run.bold and run.italic:
            text = f"***{text}***"
        elif run.bold:
            text = f"**{text}**"
        elif run.italic:
            text = f"*{text}*"
        parts.append(text)
    result = "".join(parts)
    # Safety net: if runs produced significantly less text than para.text,
    # non-run content (hyperlinks, field codes, smart tags) was lost — fall back.
    full_text = para.text
    if full_text and len(result) < len(full_text) * 0.5:
        return full_text
    return result


def _docx_table_to_md(tbl) -> str:
    all_rows = []
    for row in tbl.rows:
        # Deduplicate adjacent cells that share the same underlying XML element
        # (merged cells repeat the same Cell object for each spanned column)
        cells_deduped = [cell for i, cell in enumerate(row.cells)
                         if i == 0 or cell._tc is not row.cells[i - 1]._tc]
        cells = [cell.text.replace("\n", " ").strip() for cell in cells_deduped]
        all_rows.append(cells)
    if not all_rows:
        return ""
    headers = all_rows[0]
    rows = all_rows[1:]
    col_count = max(len(headers), max((len(r) for r in rows), default=0))
    headers = _pad(headers, col_count)
    rows = [_pad(r, col_count) for r in rows]
    return rows_to_markdown_table(headers, rows)
