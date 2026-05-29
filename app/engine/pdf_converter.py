"""
PDF converter.

Routing strategy (in order of quality):
  1. docling        — AI layout analysis, full structure, tables, images. Best quality.
  2. pymupdf4llm    — Fast Markdown export. Good for clean native PDFs.
  3. pymupdf (fitz) — Raw extraction with page-by-page text + image pull. Reliable fallback.
  4. OCR via ocr_engine — Last resort for scanned/image-only PDFs.

Table extraction supplements all paths via table_extractor (pdfplumber + camelot).

Outputs:
  - Markdown with heading hierarchy, TOC, page anchors
  - assets/ with extracted images
  - Per-page OCR results when applicable
  - ConfidenceResult populated from extraction quality signals
"""

import os
import re
import statistics
import threading
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput
from .logger import ConversionLogger
from . import ocr_engine
from . import table_extractor


class ConversionCancelled(Exception):
    """Raised when the user cancels a conversion mid-file."""
    pass


# ---------------------------------------------------------------------------
# Shared PDF utility
# ---------------------------------------------------------------------------

def get_pdf_page_count(path: str) -> int | None:
    """Return the number of pages in a PDF, or None on error.

    Uses pymupdf (fitz) for fast page count without full content parse.
    This is intentionally cheap — it only reads the PDF catalog, so even
    a 1400-page file returns in milliseconds.
    """
    try:
        import fitz
        with fitz.open(path) as doc:
            return len(doc)
    except Exception:
        return None


def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    conversion_mode: str = "Auto-detect",   # Standard | OCR | Auto-detect
    language: str = "en",
    preserve_images: bool = True,
    rebuild_toc: bool = True,
    preserve_page_numbers: bool = True,
    use_subfolder: bool = True,
    embed_images: bool = True,
    remove_headers_footers: bool = True,
    skip_blank_pages: bool = True,
    strip_line_numbers: bool = False,
    detect_code_blocks: bool = True,
    detect_footnotes: bool = True,
    detect_equations: bool = True,
    auto_translate: bool = True,
    prefer_engine: str = "rapidocr",
    ocr_dpi_scale: float = 4.0,
    quality: str = "Quality",
    page_range: list[int] | None = None,
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
    stage_callback: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[threading.Event] = None,
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
    def check_cancel():
        if cancel_event and cancel_event.is_set():
            raise ConversionCancelled("Conversion cancelled by user")

    log_info(f"PDF converter started | file={os.path.basename(source_file)} mode={conversion_mode}")
    progress(0.03)

    # ------------------------------------------------------------------
    # Check for encrypted / password-protected PDFs
    # ------------------------------------------------------------------
    try:
        import fitz as _fitz_check
        with _fitz_check.open(source_file) as _doc_check:
            if _doc_check.is_encrypted:
                log_warn("PDF is password-protected or encrypted. Cannot extract content.")
                confidence.overall = "Failed"
                confidence.text_extraction = "Failed"
                confidence.manual_review_recommended = True
                output.add_section(
                    body="*This PDF is password-protected or encrypted. "
                         "Please remove the password and try again.*")
                return output
    except Exception:
        pass  # will be caught by the actual converter below

    if page_range:
        log_info(f"Page range filter active: {len(page_range)} pages selected")

    # ------------------------------------------------------------------
    # Auto-detect: check if PDF has extractable text or is scanned
    # ------------------------------------------------------------------
    is_scanned = False
    if conversion_mode == "Auto-detect":
        stage("Detecting document type…")
        is_scanned = _detect_scanned(source_file, log_info)
        if is_scanned:
            log_info("Auto-detect: PDF appears to be scanned/image-based — enabling OCR path.")
            conversion_mode = "OCR"
        else:
            log_info("Auto-detect: PDF has extractable text — using Standard path.")
            conversion_mode = "Standard"

    progress(0.06)

    pp_settings = dict(
        remove_headers_footers=remove_headers_footers,
        skip_blank_pages=skip_blank_pages,
        strip_line_numbers=strip_line_numbers,
        detect_code_blocks=detect_code_blocks,
        detect_footnotes=detect_footnotes,
        detect_equations=detect_equations,
    )

    # ------------------------------------------------------------------
    # Standard path: docling → pymupdf4llm → pymupdf
    # Fast quality skips docling (heavy ML models) for maximum speed.
    # ------------------------------------------------------------------
    if conversion_mode == "Standard":

        if quality == "Fast":
            log_info("Fast mode — skipping docling, using lightweight engines.")
        elif _docling_available():
            try:
                result = _convert_docling(
                    source_file, alias, output_root, preserve_images,
                    rebuild_toc, preserve_page_numbers, use_subfolder,
                    embed_images, output, confidence, log_info, log_warn, progress, stage,
                    pp_settings=pp_settings,
                    cancel_event=cancel_event,
                )
                if result:
                    return result
            except Exception as e:
                log_warn(f"docling PDF failed: {e} — falling back.")

        if _pymupdf4llm_available():
            try:
                return _convert_pymupdf4llm(
                    source_file, alias, output_root, preserve_images,
                    rebuild_toc, preserve_page_numbers, use_subfolder,
                    output, confidence, log_info, log_warn, progress,
                    pp_settings=pp_settings,
                    page_range=page_range,
                )
            except Exception as e:
                log_warn(f"pymupdf4llm failed: {e} — falling back.")

        if _pymupdf_available():
            return _convert_pymupdf(
                source_file, alias, output_root, preserve_images,
                rebuild_toc, preserve_page_numbers, language, use_subfolder,
                output, confidence, log_info, log_warn, progress,
                use_ocr=False, pp_settings=pp_settings,
                ocr_dpi_scale=ocr_dpi_scale, prefer_engine=prefer_engine,
                cancel_event=cancel_event, page_range=page_range,
            )

    # ------------------------------------------------------------------
    # OCR path: pymupdf extracts images per page → OCR each page
    # ------------------------------------------------------------------
    if conversion_mode == "OCR":
        if _pymupdf_available():
            return _convert_pymupdf(
                source_file, alias, output_root, preserve_images,
                rebuild_toc, preserve_page_numbers, language, use_subfolder,
                output, confidence, log_info, log_warn, progress,
                use_ocr=True, pp_settings=pp_settings,
                ocr_dpi_scale=ocr_dpi_scale, prefer_engine=prefer_engine,
                cancel_event=cancel_event, page_range=page_range,
            )

    log_warn("No PDF conversion engine available.")
    confidence.text_extraction = "Failed"
    confidence.overall = "Failed"
    return output


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------

def _docling_available() -> bool:
    try:
        from docling.document_converter import DocumentConverter  # noqa: F401
        return True
    except ImportError:
        return False


def _pymupdf4llm_available() -> bool:
    try:
        import pymupdf4llm  # noqa: F401
        return True
    except ImportError:
        return False


def _pymupdf_available() -> bool:
    try:
        import fitz  # noqa: F401
        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# Scanned PDF detection
# ---------------------------------------------------------------------------

def _detect_scanned(pdf_path: str, log_info) -> bool:
    """
    Sample the first few pages. If less than 20 chars of text per page
    are extractable, treat as scanned.
    """
    if not _pymupdf_available():
        return False
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            sample_pages = min(3, len(doc))
            total_chars = 0
            for i in range(sample_pages):
                page = doc[i]
                total_chars += len(page.get_text("text").strip())
            avg_chars = total_chars / max(sample_pages, 1)
            log_info(f"Scanned detection | avg_chars_per_page={avg_chars:.0f}")
            return avg_chars < 20
    except Exception:
        return False


# ---------------------------------------------------------------------------
# docling path
# ---------------------------------------------------------------------------

def _convert_docling(
    source_file, alias, output_root, preserve_images, rebuild_toc,
    preserve_page_numbers, use_subfolder, embed_images,
    output, confidence, log_info, log_warn, progress, stage,
    pp_settings: Optional[dict] = None,
    cancel_event: Optional[threading.Event] = None,
) -> Optional[ConversionOutput]:
    from docling.document_converter import DocumentConverter

    import time as _time

    log_info("Using docling engine for PDF.")
    output.engine_used = "docling"
    progress(0.1)

    stage("Loading docling models…")
    converter = DocumentConverter()
    progress(0.15)

    stage("Converting PDF — this may take a while for large documents…")
    progress(-1.0)

    # Run the blocking docling call in a sub-thread so we can poll cancel
    # and update the stage text with elapsed time so the user sees activity.
    if cancel_event:
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
        t0 = _time.monotonic()
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(converter.convert, source_file)
            tick = 0
            while not future.done():
                if cancel_event.is_set():
                    raise ConversionCancelled("Conversion cancelled by user")
                try:
                    future.result(timeout=2.0)
                except FutureTimeout:
                    tick += 1
                    elapsed = int(_time.monotonic() - t0)
                    m, s = divmod(elapsed, 60)
                    stage(f"Converting PDF — {m}:{s:02d} elapsed…")
            result = future.result()
    else:
        result = converter.convert(source_file)

    doc = result.document
    progress(0.55)
    stage("Processing output…")

    md_text = doc.export_to_markdown()
    if not md_text.strip():
        log_warn("docling returned empty Markdown for PDF.")
        return None

    # Embed images inline (base64) BEFORE cleaning — placeholders must still be present
    if embed_images and preserve_images and output_root:
        log_info("Embedding images as inline base64...")
        md_text = _embed_images_in_markdown(
            md_text, doc, source_file, log_info, log_warn
        )
        confidence.add_note("Images embedded as inline base64 for self-contained Markdown.")
    elif preserve_images and output_root:
        # Fall back to saving image files to assets/
        _extract_fitz_images(source_file, alias, output_root, output, log_info, log_warn, use_subfolder)

    # Post-process text artifacts (PUA chars, soft hyphens, leftover placeholders)
    md_text = _clean_docling_text(md_text)

    # Run post-processor pipeline (header/footer removal, blank page skip, line numbers)
    pp = pp_settings or {}
    _pp_keys = ("remove_headers_footers", "skip_blank_pages", "strip_line_numbers",
                 "detect_code_blocks", "detect_footnotes", "detect_equations")
    if any(pp.get(k) for k in _pp_keys):
        from . import post_processors
        # Docling produces a monolithic string; split on page anchors if present,
        # otherwise treat as single page (post-processors are less effective).
        page_marker = re.compile(r'(?=<a\s+id="page-\d+")')
        pages = page_marker.split(md_text)
        pages = [p for p in pages if p]  # drop empty leading split
        if len(pages) > 1:
            log_info(f"Post-processing {len(pages)} page segments...")
            pages = post_processors.run_pipeline(
                pages,
                do_remove_headers_footers=pp.get("remove_headers_footers", True),
                do_skip_blank_pages=pp.get("skip_blank_pages", True),
                do_strip_line_numbers=pp.get("strip_line_numbers", False),
                do_detect_code_blocks=pp.get("detect_code_blocks", True),
                do_detect_footnotes=pp.get("detect_footnotes", True),
                do_detect_equations=pp.get("detect_equations", True),
            )
            md_text = "".join(pages)
        else:
            # Single block — run applicable processors individually
            if pp.get("strip_line_numbers", False):
                md_text = post_processors.strip_line_numbers(md_text)
            if pp.get("detect_code_blocks", True):
                md_text = post_processors.detect_code_blocks_in_markdown(md_text)
            if pp.get("detect_footnotes", True):
                md_text = post_processors.detect_footnotes_in_markdown(md_text)
            if pp.get("detect_equations", True):
                md_text = post_processors.detect_equations(md_text)
            log_info("Post-processing: single text block (header/footer removal needs page segments).")

    # Extract outline / TOC from docling document model
    if rebuild_toc:
        _extract_docling_toc(doc, output, log_info)

    # Inject page anchors if page number info is available
    if preserve_page_numbers:
        md_text = _inject_page_anchors_from_text(md_text)

    output.add_section(body=md_text)
    progress(0.9)

    confidence.text_extraction = "High"
    confidence.table_structure = "High"
    confidence.document_order = "High"
    confidence.image_extraction = "High" if preserve_images else "N/A"
    confidence.image_placement = "High" if preserve_images else "N/A"
    confidence.ocr_confidence = "N/A"
    confidence.add_note("Engine: docling (AI layout analysis)")
    confidence.derive_overall()

    log_info("docling PDF conversion complete.")
    progress(1.0)
    return output


def _embed_images_in_markdown(
    md_text: str,
    doc,
    source_file: str,
    log_info,
    log_warn,
) -> str:
    """
    Replace every ``<!-- image -->`` placeholder emitted by docling's
    ``export_to_markdown()`` with a base64-encoded PNG crop extracted from
    the PDF at the exact position of the corresponding picture element.

    Algorithm
    ---------
    1. Count how many ``<!-- image -->`` placeholders appear in md_text.
    2. Iterate ``doc.pictures`` (a list of PictureItem objects in document
       order, which matches the order of the placeholders).
    3. For each picture:
       - Read its bounding-box from ``prov[0].bbox`` (docling uses a
         bottom-left coordinate origin in PDF points).
       - Open the PDF with fitz and get the page height (top-left origin).
       - Convert:  fitz_rect = (bbox.l, page_height - bbox.t,
                                bbox.r, page_height - bbox.b)
       - Render the cropped region at 3× resolution for clarity.
       - Base64-encode the PNG and replace the placeholder inline.
    4. Any picture whose crop fails falls back to a text note so the
       placeholder is always consumed.
    """
    import fitz
    import base64

    PLACEHOLDER_RE = re.compile(r'<!--\s*image\s*-->', re.IGNORECASE)
    placeholder_count = len(PLACEHOLDER_RE.findall(md_text))

    if placeholder_count == 0:
        log_info("No <!-- image --> placeholders found — nothing to embed.")
        return md_text

    pictures = getattr(doc, 'pictures', [])
    log_info(f"Embedding images | placeholders={placeholder_count} pictures={len(pictures)}")

    if not pictures:
        log_info("doc.pictures is empty — skipping base64 embedding.")
        return md_text

    # Open PDF once; keep it open for all crops
    try:
        fitz_doc = fitz.open(source_file)
    except Exception as e:
        log_warn(f"fitz could not open PDF for image embedding: {e}")
        return md_text

    replacements: list[str] = []

    try:
        for idx, picture in enumerate(pictures):
            if idx >= placeholder_count:
                break  # more pictures than placeholders — stop early

            try:
                prov_list = getattr(picture, 'prov', None)
                if not prov_list:
                    raise ValueError("picture has no prov list")

                prov = prov_list[0]
                bbox = prov.bbox          # docling BoundingBox: l, t, r, b (bottom-left origin)
                page_no = prov.page_no    # 1-indexed

                page_idx = page_no - 1
                if page_idx < 0 or page_idx >= len(fitz_doc):
                    raise ValueError(f"page_no={page_no} out of range (doc has {len(fitz_doc)} pages)")

                page = fitz_doc[page_idx]
                page_height = page.rect.height   # fitz: top-left origin

                # Coordinate conversion: docling bottom-left → fitz top-left
                fitz_rect = fitz.Rect(
                    bbox.l,
                    page_height - bbox.t,
                    bbox.r,
                    page_height - bbox.b,
                )

                # Validate the rect
                if fitz_rect.is_empty or fitz_rect.is_infinite or fitz_rect.width < 2 or fitz_rect.height < 2:
                    raise ValueError(f"Degenerate bounding box: {fitz_rect}")

                # Render at 3× for crisp output
                mat = fitz.Matrix(3.0, 3.0)
                pix = page.get_pixmap(matrix=mat, clip=fitz_rect, colorspace=fitz.csRGB)
                try:
                    img_bytes = pix.tobytes("png")
                finally:
                    pix = None  # release Pixmap memory immediately

                b64_data = base64.b64encode(img_bytes).decode("ascii")
                alt = f"Image {idx + 1} — page {page_no}"
                replacement = f"![{alt}](data:image/png;base64,{b64_data})"
                replacements.append(replacement)

                log_info(
                    f"  Embedded image {idx + 1}/{placeholder_count}: "
                    f"page={page_no} size={fitz_rect.width:.0f}×{fitz_rect.height:.0f}pt "
                    f"png={len(img_bytes)} bytes"
                )

            except Exception as e:
                log_warn(f"Could not embed image {idx + 1}: {e}")
                replacements.append("*[image — could not be extracted]*")
    finally:
        fitz_doc.close()

    # Replace placeholders back-to-front by offset to avoid re-scanning
    # base64 data (Fix A: lambda avoids regex template interpretation,
    # Fix B: back-to-front string slicing avoids O(n*m) rescanning)
    matches = list(PLACEHOLDER_RE.finditer(md_text))
    result = md_text
    for match, replacement in reversed(list(zip(matches, replacements))):
        result = result[:match.start()] + replacement + result[match.end():]

    embedded = sum(1 for r in replacements if r.startswith("!["))
    log_info(f"Image embedding complete | embedded={embedded}/{len(replacements)}")
    return result


def _docling_label_to_level(label: str) -> int:
    """
    Map a docling element label to a Markdown heading level.

    Priority order matters: "subtitle" must be checked before "title"
    because "subtitle" contains "title" as a substring and should be
    level 2, not level 1.  If the label contains a digit (e.g.
    "heading_level_2"), extract the number directly.
    """
    # Check for explicit level digit first (e.g. "heading_level_2")
    digit_match = re.search(r'(\d+)', label)
    if digit_match:
        extracted = int(digit_match.group(1))
        if 1 <= extracted <= 6:
            return extracted

    # Check substring matches in priority order (most specific first)
    if "subtitle" in label:
        return 2
    if "title" in label:
        return 1
    if "section_header" in label:
        return 2
    if "heading" in label:
        return 2
    # Generic section fallback
    return 3


def _extract_docling_toc(doc, output: ConversionOutput, log_info) -> None:
    try:
        for item in doc.texts:
            label = str(getattr(item, "label", "")).lower()
            if "title" in label or "heading" in label or "section" in label:
                text = getattr(item, "text", "").strip()
                if text:
                    level = _docling_label_to_level(label)
                    page_ref = getattr(getattr(item, "prov", [None])[0], "page_no", None) if getattr(item, "prov", None) else None
                    output.add_toc_entry(level, text, page_ref)
    except Exception as e:
        log_info(f"Docling TOC extraction failed: {e}")

    # Fallback: extract headings from the Markdown text in sections
    for section in output.sections:
        for line in section.body.splitlines():
            m = re.match(r'^(#{1,6})\s+(.+)', line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                output.add_toc_entry(level, title)

    # Deduplicate
    seen = set()
    unique = []
    for entry in output.toc_entries:
        key = (entry[0], entry[1])
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    output.toc_entries = unique


def _extract_fitz_images(
    source_file: str,
    alias: str,
    output_root: str,
    output: ConversionOutput,
    log_info,
    log_warn,
    use_subfolder: bool = True,
    page_range: list[int] | None = None,
) -> dict[int, list[str]]:
    """
    Extract embedded images from a PDF using fitz and save them to assets/.
    Used by the pymupdf4llm conversion path.
    Deduplicates images by xref so the same image reused on multiple pages
    is only saved once.

    When *page_range* is given (1-based page numbers), only those pages are
    scanned for images.  This avoids processing the entire document when only
    a subset of pages was requested for text extraction.

    Returns a dict mapping page_num (1-based) to a list of Markdown image
    reference strings, including captions when detected.
    """
    page_refs: dict[int, list[str]] = {}
    try:
        import fitz
        from .markdown_writer import assets_dir_for, assets_rel_prefix_for
        assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
        rel_prefix = assets_rel_prefix_for(source_file, alias, use_subfolder)
        os.makedirs(assets_dir, exist_ok=True)

        with fitz.open(source_file) as doc:
            saved_xrefs: set[int] = set()
            img_counter = 0

            # Only scan requested pages (or all pages when no range given)
            if page_range:
                page_indices = [p - 1 for p in page_range if 0 < p <= len(doc)]
            else:
                page_indices = list(range(len(doc)))

            for page_idx in page_indices:
                page = doc[page_idx]
                page_num = page_idx + 1
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    if xref in saved_xrefs:
                        continue  # skip duplicate (same image on multiple pages)
                    try:
                        base_image = doc.extract_image(xref)
                        img_bytes = base_image["image"]
                        if len(img_bytes) < 512:
                            continue  # skip tiny images (icons, borders)
                        ext = base_image.get("ext", "png")
                        img_counter += 1
                        filename = f"image_{img_counter:03d}_p{page_num}.{ext}"
                        img_path = os.path.join(assets_dir, filename)
                        with open(img_path, "wb") as fh:
                            fh.write(img_bytes)
                        rel_path = f"{rel_prefix}{filename}"
                        output.asset_paths.append(rel_path)
                        saved_xrefs.add(xref)

                        # Caption detection
                        alt_text = f"Image from page {page_num}"
                        caption_line = ""
                        try:
                            rects = page.get_image_rects(xref)
                            img_rect = rects[0] if rects else None
                        except Exception:
                            img_rect = None
                        caption = _find_caption_for_image(page, img_rect, log_info)
                        if caption:
                            alt_text = caption
                            caption_line = f"\n*{caption}*"
                            log_info(f"Caption detected for {filename}: {caption}")

                        ref = f"\n![{alt_text}]({rel_path}){caption_line}\n"
                        page_refs.setdefault(page_num, []).append(ref)

                        log_info(f"Saved image: {filename} ({len(img_bytes)} bytes)")
                    except Exception as e:
                        log_warn(f"Could not extract image xref={xref}: {e}")

            log_info(f"Image extraction complete | saved={img_counter}")

    except Exception as e:
        log_warn(f"fitz image extraction failed: {e}")

    return page_refs


# ---------------------------------------------------------------------------
# pymupdf4llm path
# ---------------------------------------------------------------------------

def _convert_pymupdf4llm(
    source_file, alias, output_root, preserve_images, rebuild_toc,
    preserve_page_numbers, use_subfolder, output, confidence, log_info, log_warn, progress,
    pp_settings: Optional[dict] = None,
    page_range: list[int] | None = None,
) -> ConversionOutput:
    import pymupdf4llm
    import fitz

    log_info("Using pymupdf4llm engine for PDF.")
    output.engine_used = "pymupdf4llm"
    progress(0.1)

    # pymupdf4llm accepts 0-indexed page list
    pages_arg = [p - 1 for p in page_range] if page_range else None
    md_text = pymupdf4llm.to_markdown(source_file, pages=pages_arg)
    if not md_text.strip():
        log_warn("pymupdf4llm returned empty output.")
        confidence.text_extraction = "Low"
        confidence.derive_overall()
        return output

    progress(0.5)

    # Extract TOC from PDF outline
    if rebuild_toc:
        _extract_fitz_toc(source_file, output, log_info)

    # Extract and save images via fitz — inject refs into the markdown text
    if preserve_images and output_root:
        page_image_refs = _extract_fitz_images(
            source_file, alias, output_root, output, log_info, log_warn,
            use_subfolder, page_range=page_range,
        )
        if page_image_refs:
            # pymupdf4llm uses --- separators between pages; split, inject, rejoin
            _page_sep = re.compile(r'(?m)^-{3,}\s*$')
            segments = _page_sep.split(md_text)

            # Build page-number → segment-index mapping.  When a page_range is
            # active the segments correspond to the *requested* pages in order,
            # not to absolute page numbers in the PDF.
            if page_range:
                _pg_to_seg = {pg: i for i, pg in enumerate(sorted(page_range))}
            else:
                _pg_to_seg = None  # fall back to pg_num-1

            for pg_num, refs in page_image_refs.items():
                if _pg_to_seg is not None:
                    idx = _pg_to_seg.get(pg_num, -1)
                    if idx < 0:
                        continue  # image page not in requested range
                else:
                    idx = pg_num - 1

                if idx < len(segments):
                    segments[idx] += "\n" + "\n".join(refs)
                else:
                    # Page beyond segment count — append to last segment
                    segments[-1] += "\n" + "\n".join(refs)
            md_text = "\n---\n".join(segments)

    # Run post-processor pipeline
    pp = pp_settings or {}
    _pp_keys_4llm = ("remove_headers_footers", "skip_blank_pages", "strip_line_numbers",
                      "detect_code_blocks", "detect_footnotes", "detect_equations")
    if any(pp.get(k) for k in _pp_keys_4llm):
        from . import post_processors
        # pymupdf4llm uses --- as page separators; split on them for per-page processing
        page_sep = re.compile(r'(?m)^-{3,}\s*$')
        pages = page_sep.split(md_text)
        if len(pages) > 1:
            log_info(f"Post-processing {len(pages)} page segments...")
            pages = post_processors.run_pipeline(
                pages,
                do_remove_headers_footers=pp.get("remove_headers_footers", True),
                do_skip_blank_pages=pp.get("skip_blank_pages", True),
                do_strip_line_numbers=pp.get("strip_line_numbers", False),
                do_detect_code_blocks=pp.get("detect_code_blocks", True),
                do_detect_footnotes=pp.get("detect_footnotes", True),
                do_detect_equations=pp.get("detect_equations", True),
            )
            md_text = "\n---\n".join(pages)
        else:
            if pp.get("strip_line_numbers", False):
                md_text = post_processors.strip_line_numbers(md_text)
            if pp.get("detect_code_blocks", True):
                md_text = post_processors.detect_code_blocks_in_markdown(md_text)
            if pp.get("detect_footnotes", True):
                md_text = post_processors.detect_footnotes_in_markdown(md_text)
            if pp.get("detect_equations", True):
                md_text = post_processors.detect_equations(md_text)

    if preserve_page_numbers:
        md_text = _inject_page_anchors_from_text(md_text)

    output.add_section(body=md_text)
    progress(0.9)

    confidence.text_extraction = "High"
    confidence.table_structure = "Medium"
    confidence.document_order = "High"
    confidence.image_extraction = "High" if preserve_images else "N/A"
    confidence.image_placement = "Medium" if preserve_images else "N/A"
    confidence.ocr_confidence = "N/A"
    confidence.add_note("Engine: pymupdf4llm (fast Markdown export)")
    confidence.add_note("Table structure is best-effort — verify complex tables.")
    confidence.derive_overall()

    log_info("pymupdf4llm PDF conversion complete.")
    progress(1.0)
    return output


# ---------------------------------------------------------------------------
# pymupdf (fitz) page-by-page path
# ---------------------------------------------------------------------------

def _convert_pymupdf(
    source_file, alias, output_root, preserve_images, rebuild_toc,
    preserve_page_numbers, language, use_subfolder, output, confidence,
    log_info, log_warn, progress, use_ocr: bool = False,
    pp_settings: Optional[dict] = None,
    ocr_dpi_scale: float = 4.0,
    prefer_engine: str = "rapidocr",
    cancel_event: Optional[threading.Event] = None,
    page_range: list[int] | None = None,
) -> ConversionOutput:
    import fitz

    log_info(f"Using pymupdf (fitz) engine | ocr={use_ocr}")
    output.engine_used = "pymupdf-ocr" if use_ocr else "pymupdf"
    progress(0.05)

    try:
        doc = fitz.open(source_file)
    except Exception as e:
        log_warn(f"fitz failed to open PDF: {e}")
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        return output

    page_sections = []
    ocr_confidences = []
    text_quality_flags = []

    try:
        total_pages = len(doc)
        log_info(f"Opened PDF | pages={total_pages}")

        # Extract TOC from PDF outline
        if rebuild_toc:
            _extract_fitz_toc_from_doc(doc, output, log_info)

        # Assets dir
        assets_dir = None
        rel_prefix = "assets/"
        if preserve_images and output_root:
            from .markdown_writer import assets_dir_for, assets_rel_prefix_for
            assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
            rel_prefix = assets_rel_prefix_for(source_file, alias, use_subfolder)
            os.makedirs(assets_dir, exist_ok=True)

        saved_xrefs: set[int] = set()
        active_pages = len(page_range) if page_range else total_pages
        pages_done = 0

        for page_idx in range(total_pages):
            if cancel_event and cancel_event.is_set():
                raise ConversionCancelled("Conversion cancelled by user")
            page_num = page_idx + 1
            # Skip pages not in the selected range
            if page_range and page_num not in page_range:
                continue
            page = doc[page_idx]
            prog = 0.1 + (pages_done / max(active_pages, 1)) * 0.75
            pages_done += 1
            progress(prog)

            page_parts = []

            # Page anchor
            if preserve_page_numbers:
                page_parts.append(f'<a id="page-{page_num}"></a>\n\n---\n*Page {page_num}*\n')

            # Text extraction
            if use_ocr:
                page_text, ocr_conf = _ocr_page(page, language, log_info, log_warn,
                                                ocr_dpi_scale=ocr_dpi_scale,
                                                prefer_engine=prefer_engine)
                ocr_confidences.append(ocr_conf)
                if page_text.strip():
                    page_parts.append(page_text)
                text_quality_flags.append(bool(page_text.strip()))
            else:
                text = _extract_page_text_columns(page, page_num, log_info)
                text = text.strip()
                if text:
                    # Detect visual headings for PDFs lacking a proper outline
                    if not output.toc_entries:
                        text = _detect_headings_in_text(page, text)
                    page_parts.append(text)
                text_quality_flags.append(bool(text))

            # Image extraction
            if preserve_images and assets_dir:
                img_refs = _extract_page_images(
                    doc, page, page_num, assets_dir, output, log_info, rel_prefix,
                    saved_xrefs=saved_xrefs,
                )
                page_parts.extend(img_refs)

            # Table extraction via pdfplumber for this page
            tables = _get_page_tables(source_file, page_num, log_info)
            for tr in tables:
                page_parts.append(f"\n{tr.to_markdown()}\n")
                if tr.confidence == "Low":
                    confidence.add_warning(f"Page {page_num}: low-confidence table detected.")

            if page_parts:
                page_sections.append((page_num, "\n".join(page_parts)))
        progress(0.88)

        # Run post-processor pipeline on collected page texts
        pp = pp_settings or {}
        _pp_keys_mupdf = ("remove_headers_footers", "skip_blank_pages", "strip_line_numbers",
                           "detect_code_blocks", "detect_footnotes", "detect_equations")
        if page_sections and any(pp.get(k) for k in _pp_keys_mupdf):
            from . import post_processors
            page_texts = [body for _, body in page_sections]
            page_nums  = [num for num, _ in page_sections]

            log_info(f"Post-processing {len(page_texts)} pages...")
            processed = post_processors.run_pipeline(
                page_texts,
                do_remove_headers_footers=pp.get("remove_headers_footers", True),
                do_skip_blank_pages=pp.get("skip_blank_pages", True),
                do_strip_line_numbers=pp.get("strip_line_numbers", False),
                do_detect_code_blocks=pp.get("detect_code_blocks", True),
                do_detect_footnotes=pp.get("detect_footnotes", True),
                do_detect_equations=pp.get("detect_equations", True),
            )

            # Rebuild page_sections from processed output.
            # When lengths match, pair 1:1 with original page numbers.
            # When processed is shorter (blank-page filtering removed some),
            # assign pages sequentially from the original page numbers,
            # truncating if needed. This avoids fragile content-matching.
            if len(processed) == len(page_texts):
                page_sections = list(zip(page_nums, processed))
            elif len(processed) < len(page_texts):
                log_warn(
                    f"Post-processing reduced pages from {len(page_texts)} to "
                    f"{len(processed)} — assigning page numbers sequentially."
                )
                page_sections = list(zip(page_nums[:len(processed)], processed))
            else:
                # Processed somehow has more entries (shouldn't happen);
                # truncate to original count
                log_warn(
                    f"Post-processing expanded pages from {len(page_texts)} to "
                    f"{len(processed)} — truncating to original count."
                )
                page_sections = list(zip(page_nums, processed[:len(page_texts)]))

        # Merge sentence fragments split across page boundaries
        if len(page_sections) > 1:
            page_sections = _merge_cross_page_paragraphs(page_sections)

        # Assemble sections
        for page_num, body in page_sections:
            output.add_section(body=body, page_number=page_num)

        # Confidence
        extracted_pages = sum(1 for f in text_quality_flags if f)
        extraction_ratio = extracted_pages / max(total_pages, 1)

        if extraction_ratio >= 0.9:
            confidence.text_extraction = "High"
        elif extraction_ratio >= 0.6:
            confidence.text_extraction = "Medium"
        else:
            confidence.text_extraction = "Low"

        if use_ocr and ocr_confidences:
            ocr_label_priority = {"High": 3, "Medium": 2, "Low": 1, "Failed": 0, "N/A": 4}
            worst_ocr = min(ocr_confidences, key=lambda s: ocr_label_priority.get(s, 0))
            confidence.ocr_confidence = worst_ocr
            if worst_ocr in ("Low", "Failed"):
                confidence.add_warning("Some pages had low OCR confidence — manual review recommended.")
        else:
            confidence.ocr_confidence = "N/A"

        confidence.table_structure = "Medium"
        confidence.document_order = "High"
        confidence.image_extraction = "High" if preserve_images and assets_dir else "N/A"
        confidence.image_placement = "Medium" if preserve_images and assets_dir else "N/A"
        confidence.derive_overall()

        engine_label = "pymupdf page-by-page (OCR)" if use_ocr else "pymupdf page-by-page"
        confidence.add_note(f"Engine: {engine_label}")
        log_info(f"pymupdf conversion complete | pages={total_pages} extracted={extracted_pages}")
        progress(1.0)
        return output
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Heading detection from font metrics
# ---------------------------------------------------------------------------

def _detect_headings_in_text(page, text: str) -> str:
    """Detect visual headings by analysing font size / bold spans.

    Uses ``page.get_text("dict")`` to collect font metrics, determines the
    median body font size, and prefixes lines whose font size significantly
    exceeds the median with Markdown heading markup.

    Only short lines (< 120 chars, single logical line) are promoted so
    that large-font body paragraphs are not incorrectly treated as headings.
    """
    try:
        page_dict = page.get_text("dict")
    except Exception:
        return text

    # 1. Collect per-line font info ----------------------------------------
    line_info: list[tuple[str, float, bool]] = []   # (text, size, bold)
    all_sizes: list[float] = []

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:              # text blocks only
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            line_text_parts = []
            weighted_size = 0.0
            total_chars = 0
            is_bold = False
            for span in spans:
                stxt = span.get("text", "")
                sz = span.get("size", 0)
                flags = span.get("flags", 0)
                line_text_parts.append(stxt)
                char_count = len(stxt)
                weighted_size += sz * char_count
                total_chars += char_count
                # fitz flag bit 4 (16) = bold
                if flags & 16:
                    is_bold = True
                all_sizes.append(sz)

            line_text = "".join(line_text_parts).strip()
            avg_size = weighted_size / max(total_chars, 1)
            if line_text:
                line_info.append((line_text, avg_size, is_bold))

    if not all_sizes or not line_info:
        return text

    # 2. Compute median body font size ------------------------------------
    median_size = statistics.median(all_sizes)
    if median_size <= 0:
        return text

    # 3. Decide heading candidates ----------------------------------------
    heading_map: dict[str, str] = {}    # normalised line text -> prefix
    for lt, sz, bold in line_info:
        if len(lt) >= 120:
            continue
        ratio = sz / median_size
        prefix = ""
        if ratio >= 2.0:
            prefix = "## "
        elif ratio >= 1.5:
            prefix = "### "
        elif ratio >= 1.3:
            prefix = "#### "
        elif bold and ratio >= 1.15:
            prefix = "#### "
        if prefix:
            # Use the stripped line as key for matching into the raw text
            heading_map[lt] = prefix

    if not heading_map:
        return text

    # 4. Apply heading prefixes to the extracted text ----------------------
    out_lines: list[str] = []
    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if stripped in heading_map:
            # Avoid double-prefixing if the line already starts with #
            if not stripped.startswith("#"):
                out_lines.append(heading_map[stripped] + stripped)
            else:
                out_lines.append(raw_line)
        else:
            out_lines.append(raw_line)
    return "\n".join(out_lines)


# ---------------------------------------------------------------------------
# Cross-page paragraph merging
# ---------------------------------------------------------------------------

def _merge_cross_page_paragraphs(page_sections: list) -> list:
    """Merge sentence fragments that were split across page boundaries.

    When the previous page ends with a line that lacks sentence-ending
    punctuation and the next page begins with a lowercase letter, the
    trailing line is removed from the previous page and prepended to the
    next page (joined with a space).  This repairs mid-sentence page
    breaks that are common in multi-page PDFs.
    """
    if len(page_sections) < 2:
        return page_sections

    _SENTENCE_END = frozenset(".!?:")

    result = list(page_sections)  # shallow copy of tuples

    for i in range(len(result) - 1):
        prev_num, prev_body = result[i]
        next_num, next_body = result[i + 1]

        prev_lines = prev_body.split("\n")
        # Find the last non-empty line in the previous page
        trailing_idx = None
        for idx in range(len(prev_lines) - 1, -1, -1):
            if prev_lines[idx].strip():
                trailing_idx = idx
                break
        if trailing_idx is None:
            continue

        trailing = prev_lines[trailing_idx].strip()

        # Skip headings, list items, and empty lines
        if trailing.startswith("#") or trailing.startswith("- ") or trailing.startswith("* "):
            continue
        if re.match(r"^\d+\.\s", trailing):
            continue
        # Skip if the line ends with sentence-ending punctuation
        if trailing and trailing[-1] in _SENTENCE_END:
            continue

        # Check if the next page starts with a lowercase letter
        next_lines = next_body.split("\n")
        first_content = ""
        for nl in next_lines:
            if nl.strip():
                first_content = nl.strip()
                break
        if not first_content or not first_content[0].islower():
            continue

        # Merge: remove trailing line from prev, prepend to next
        prev_lines.pop(trailing_idx)
        result[i] = (prev_num, "\n".join(prev_lines))

        # Prepend the trailing fragment to the first content line of next page
        merged_next_lines = []
        merged = False
        for nl in next_lines:
            if not merged and nl.strip():
                merged_next_lines.append(trailing + " " + nl.lstrip())
                merged = True
            else:
                merged_next_lines.append(nl)
        result[i + 1] = (next_num, "\n".join(merged_next_lines))

    return result


# ---------------------------------------------------------------------------
# Multi-column layout detection and text extraction
# ---------------------------------------------------------------------------

def _extract_page_text_columns(page, page_num: int, log_info) -> str:
    """
    Extract text from a PDF page with multi-column layout awareness.

    Uses text block bounding boxes to detect columns: if blocks cluster
    into 2-3 distinct horizontal bands with a vertical gap between them,
    reorder blocks left-to-right by column, then top-to-bottom within
    each column.
    """
    blocks = page.get_text("blocks")
    # blocks: list of (x0, y0, x1, y1, text, block_no, block_type)
    # block_type 0 = text, 1 = image
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]

    if not text_blocks:
        return page.get_text("text")

    page_width = page.rect.width
    if page_width < 1:
        return page.get_text("text")

    # Detect columns by clustering block midpoints
    cols = _detect_columns(text_blocks, page_width)

    if len(cols) <= 1:
        # Single column — use default extraction order
        return page.get_text("text")

    log_info(f"Page {page_num}: detected {len(cols)}-column layout")

    # Sort blocks within each column top-to-bottom by y0
    ordered_text = []
    for col_blocks in cols:
        col_blocks.sort(key=lambda b: b[1])  # sort by y0
        for b in col_blocks:
            ordered_text.append(b[4].strip())

    return "\n\n".join(ordered_text)


def _detect_columns(text_blocks: list, page_width: float) -> list[list]:
    """
    Cluster text blocks into columns based on their x-position.

    Algorithm: sort blocks by x0, then detect gaps wider than 5% of page
    width between adjacent block groups. Each gap boundary defines a
    column split.
    """
    if len(text_blocks) < 2:
        return [text_blocks]

    # Collect all block left edges and right edges to find column boundaries
    blocks_by_x = sorted(text_blocks, key=lambda b: b[0])

    # Build x-ranges for each block
    x_ranges = [(b[0], b[2], b) for b in blocks_by_x]

    # Find distinct x-position clusters using a gap threshold
    gap_threshold = page_width * 0.05
    columns: list[list] = [[]]

    # Sort by center-x to cluster
    x_ranges.sort(key=lambda r: (r[0] + r[1]) / 2)

    # Use the right edge of blocks to detect column gaps
    # Group blocks where the center-x values cluster together
    centers = sorted([(r[0] + r[1]) / 2 for r in x_ranges])

    if len(centers) < 2:
        return [text_blocks]

    # Find large gaps in center-x positions
    gaps = []
    for i in range(len(centers) - 1):
        gap = centers[i + 1] - centers[i]
        if gap > gap_threshold:
            gaps.append((i, gap, (centers[i] + centers[i + 1]) / 2))

    if not gaps:
        return [text_blocks]

    # Use the largest gap(s) as column boundaries
    # For 2-column: 1 gap. For 3-column: 2 gaps. Cap at 3 columns.
    gaps.sort(key=lambda g: g[1], reverse=True)
    boundaries = sorted([g[2] for g in gaps[:2]])

    # Assign blocks to columns based on their center-x relative to boundaries
    columns = [[] for _ in range(len(boundaries) + 1)]
    for b in text_blocks:
        cx = (b[0] + b[2]) / 2
        assigned = False
        for col_idx, boundary in enumerate(boundaries):
            if cx < boundary:
                columns[col_idx].append(b)
                assigned = True
                break
        if not assigned:
            columns[-1].append(b)

    # Filter out empty columns
    columns = [c for c in columns if c]

    # Only treat as multi-column if each column has at least 2 blocks
    if all(len(c) >= 2 for c in columns) and len(columns) >= 2:
        return columns

    return [text_blocks]


# ---------------------------------------------------------------------------
# Page-level OCR
# ---------------------------------------------------------------------------

def _ocr_page(page, language: str, log_info, log_warn,
              ocr_dpi_scale: float = 4.0,
              prefer_engine: str = "rapidocr") -> tuple[str, str]:
    """Render a fitz page to an image and OCR it. Returns (text, confidence_label)."""
    try:
        import fitz
        from PIL import Image
        import io

        mat = fitz.Matrix(ocr_dpi_scale, ocr_dpi_scale)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        try:
            img_bytes = pix.tobytes("png")
        finally:
            pix = None  # release Pixmap memory immediately
        pil_image = Image.open(io.BytesIO(img_bytes))

        try:
            result = ocr_engine.run_ocr(pil_image, language=language,
                                         prefer_engine=prefer_engine)
            return result.text, result.confidence_label
        finally:
            pil_image.close()

    except Exception as e:
        log_warn(f"Page OCR failed: {e}")
        return "", "Failed"


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

def _find_caption_for_image(page, img_rect, log_info) -> str:
    """Find a caption for an image by checking text blocks near its edges.

    Looks for text blocks immediately below (or above) the image whose
    content matches common caption patterns such as "Figure 1", "Fig. 2",
    "Image 3", "Diagram 4", "Table 5", "Exhibit 6", etc.

    Returns the caption text if found, or an empty string.
    """
    if img_rect is None or img_rect.is_empty:
        return ""

    _CAPTION_RE = re.compile(
        r"^(figure|fig\.?|image|diagram|illustration|photo|plate|"
        r"table|chart|graph|exhibit|drawing|sketch|map|plan)\s*"
        r"[\d.:\-—–]+",
        re.IGNORECASE,
    )

    # Maximum vertical gap (points) between image edge and caption block
    _GAP = 45

    try:
        blocks = page.get_text("blocks")
    except Exception:
        return ""

    text_blocks = [(b[0], b[1], b[2], b[3], b[4].strip()) for b in blocks
                   if b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return ""

    best_caption = ""
    best_dist = _GAP + 1

    for bx0, by0, bx1, by1, btxt in text_blocks:
        # Horizontal overlap check — caption must overlap the image x-range
        overlap = min(bx1, img_rect.x1) - max(bx0, img_rect.x0)
        if overlap < (img_rect.width * 0.25):
            continue

        # Check below the image
        dist_below = by0 - img_rect.y1
        if 0 <= dist_below < best_dist:
            if _CAPTION_RE.match(btxt):
                best_caption = btxt
                best_dist = dist_below

        # Check above the image (some documents place captions above)
        dist_above = img_rect.y0 - by1
        if 0 <= dist_above < best_dist:
            if _CAPTION_RE.match(btxt):
                best_caption = btxt
                best_dist = dist_above

    # Trim overly long captions (keep first line only if multi-line)
    if best_caption:
        first_line = best_caption.split("\n")[0].strip()
        if len(first_line) > 200:
            first_line = first_line[:200] + "…"
        return first_line

    return ""


def _extract_page_images(
    doc, page, page_num: int, assets_dir: str,
    output: ConversionOutput, log_info,
    rel_prefix: str = "assets/",
    saved_xrefs: Optional[set] = None,
) -> list[str]:
    """Extract embedded images from a fitz page, save to assets/, return Markdown refs.

    ``saved_xrefs`` is an optional set shared across pages so that
    duplicate images (watermarks, logos reused on every page) are only
    saved once.  The caller passes the same set for each page call.

    For each image, attempts to detect a nearby caption (e.g. "Figure 1:
    …") and includes it as the Markdown alt text and an italic line
    beneath the image reference.
    """
    import fitz

    if saved_xrefs is None:
        saved_xrefs = set()

    refs = []
    try:
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
            if xref in saved_xrefs:
                continue  # skip duplicate (same image on another page)
            try:
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                ext = base_image.get("ext", "png")
                filename = f"page_{page_num:03d}_img_{img_idx + 1:02d}.{ext}"
                img_path = os.path.join(assets_dir, filename)

                with open(img_path, "wb") as f:
                    f.write(img_bytes)

                rel_path = f"{rel_prefix}{filename}"
                output.asset_paths.append(rel_path)

                # Try to find a caption near the image
                alt_text = f"Image from page {page_num}"
                caption_line = ""
                try:
                    rects = page.get_image_rects(xref)
                    img_rect = rects[0] if rects else None
                except Exception:
                    img_rect = None

                caption = _find_caption_for_image(page, img_rect, log_info)
                if caption:
                    alt_text = caption
                    caption_line = f"\n*{caption}*"
                    log_info(f"Caption detected for {filename}: {caption}")

                refs.append(f"\n![{alt_text}]({rel_path}){caption_line}\n")
                saved_xrefs.add(xref)
                log_info(f"Saved image: {filename}")
            except Exception as e:
                log_info(f"Could not extract image xref={xref} on page {page_num}: {e}")
    except Exception as e:
        log_info(f"Image extraction failed for page {page_num}: {e}")
    return refs


# ---------------------------------------------------------------------------
# Table extraction helper
# ---------------------------------------------------------------------------

def _get_page_tables(pdf_path: str, page_num: int, log_info) -> list:
    try:
        return table_extractor.extract_tables_from_file(pdf_path, pages=[page_num])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Docling output post-processing
# ---------------------------------------------------------------------------

def _clean_docling_text(text: str) -> str:
    """
    Fix three classes of artifacts that docling produces from PDFs with
    custom-encoded fonts:

    1. Adobe PUA characters (U+F700-U+F7FF) — many PDFs encode their body
       font glyphs in the Private Use Area block offset by 0xF700. Each PUA
       char is simply the matching printable ASCII char plus 0xF700.
       Subtract 0xF700 to recover the original character.

    2. Soft hyphens (U+00AD) — used in PDFs for in-line word-break
       hyphenation. Removing them rejoins the word correctly.

    3. <!-- image --> placeholders — docling inserts these when it detects
       an embedded image it cannot export. Replace with a human-readable note.

    4. Decorative PUA separators (U+E048, U+E061) — custom ornament glyphs
       used as section dividers. Replace with a Markdown horizontal rule.
    """
    result = []
    for ch in text:
        cp = ord(ch)
        if 0xF700 <= cp <= 0xF7FF:
            ascii_equiv = cp - 0xF700
            if 0x20 <= ascii_equiv <= 0x7E:
                result.append(chr(ascii_equiv))
            # else: drop non-printable PUA char
        elif cp == 0x00AD:
            pass  # drop soft hyphen — rejoins hyphenated word
        elif cp in (0xE048, 0xE061):
            result.append("\n\n---\n\n")
        else:
            result.append(ch)

    cleaned = "".join(result)

    # Replace docling image placeholders with a readable note
    cleaned = re.sub(
        r'<!--\s*image\s*-->',
        '*[image — could not be extracted]*',
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned


# ---------------------------------------------------------------------------
# TOC helpers
# ---------------------------------------------------------------------------

def _extract_fitz_toc(pdf_path: str, output: ConversionOutput, log_info) -> None:
    try:
        import fitz
        with fitz.open(pdf_path) as doc:
            _extract_fitz_toc_from_doc(doc, output, log_info)
    except Exception as e:
        log_info(f"Could not extract PDF outline: {e}")


def _extract_fitz_toc_from_doc(doc, output: ConversionOutput, log_info) -> None:
    try:
        toc = doc.get_toc()
        if toc:
            log_info(f"Extracted PDF outline | entries={len(toc)}")
            for level, title, page in toc:
                output.add_toc_entry(level, title, page)
    except Exception as e:
        log_info(f"PDF outline extraction failed: {e}")


# ---------------------------------------------------------------------------
# Page anchor injection
# ---------------------------------------------------------------------------

def _inject_page_anchors_from_text(md_text: str) -> str:
    """
    pymupdf4llm includes page separators as horizontal rules.
    Detect them and inject page anchors. Content before the first
    separator is page 1; each ``---`` advances to the next page.
    """
    lines = md_text.splitlines()
    result = []
    page_num = 1
    # Insert anchor for page 1 before any content
    result.append(f'<a id="page-{page_num}"></a>\n*Page {page_num}*')
    for line in lines:
        if re.match(r'^-{3,}\s*$', line):
            page_num += 1
            result.append(f'<a id="page-{page_num}"></a>\n\n---\n*Page {page_num}*')
        else:
            result.append(line)
    return "\n".join(result)
