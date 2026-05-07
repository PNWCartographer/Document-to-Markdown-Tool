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
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput
from .logger import ConversionLogger
from . import ocr_engine
from . import table_extractor


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
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
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

    log_info(f"PDF converter started | file={os.path.basename(source_file)} mode={conversion_mode}")
    progress(0.03)

    # ------------------------------------------------------------------
    # Auto-detect: check if PDF has extractable text or is scanned
    # ------------------------------------------------------------------
    is_scanned = False
    if conversion_mode == "Auto-detect":
        is_scanned = _detect_scanned(source_file, log_info)
        if is_scanned:
            log_info("Auto-detect: PDF appears to be scanned/image-based — enabling OCR path.")
            conversion_mode = "OCR"
        else:
            log_info("Auto-detect: PDF has extractable text — using Standard path.")
            conversion_mode = "Standard"

    progress(0.06)

    # ------------------------------------------------------------------
    # Standard path: docling → pymupdf4llm → pymupdf
    # ------------------------------------------------------------------
    if conversion_mode == "Standard":

        if _docling_available():
            try:
                result = _convert_docling(
                    source_file, alias, output_root, preserve_images,
                    rebuild_toc, preserve_page_numbers, use_subfolder,
                    embed_images, output, confidence, log_info, log_warn, progress
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
                    output, confidence, log_info, log_warn, progress
                )
            except Exception as e:
                log_warn(f"pymupdf4llm failed: {e} — falling back.")

        if _pymupdf_available():
            return _convert_pymupdf(
                source_file, alias, output_root, preserve_images,
                rebuild_toc, preserve_page_numbers, language, use_subfolder,
                output, confidence, log_info, log_warn, progress,
                use_ocr=False
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
                use_ocr=True
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
        doc = fitz.open(pdf_path)
        sample_pages = min(3, len(doc))
        total_chars = 0
        for i in range(sample_pages):
            page = doc[i]
            total_chars += len(page.get_text("text").strip())
        doc.close()
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
    output, confidence, log_info, log_warn, progress
) -> Optional[ConversionOutput]:
    from docling.document_converter import DocumentConverter

    log_info("Using docling engine for PDF.")
    output.engine_used = "docling"
    progress(0.1)

    converter = DocumentConverter()
    result = converter.convert(source_file)
    doc = result.document
    progress(0.55)

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
            img_bytes = pix.tobytes("png")

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

    fitz_doc.close()

    # Replace placeholders one by one in document order
    result = md_text
    for replacement in replacements:
        result = PLACEHOLDER_RE.sub(replacement, result, count=1)

    embedded = sum(1 for r in replacements if r.startswith("!["))
    log_info(f"Image embedding complete | embedded={embedded}/{len(replacements)}")
    return result


def _extract_docling_toc(doc, output: ConversionOutput, log_info) -> None:
    try:
        for item in doc.texts:
            label = str(getattr(item, "label", "")).lower()
            if "title" in label or "heading" in label or "section" in label:
                text = getattr(item, "text", "").strip()
                if text:
                    level = 1 if "title" in label else (2 if "heading" in label else 3)
                    page_ref = getattr(getattr(item, "prov", [None])[0], "page_no", None) if getattr(item, "prov", None) else None
                    output.add_toc_entry(level, text, page_ref)
    except Exception:
        pass

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
) -> None:
    """
    Extract all embedded images from a PDF using fitz and save them to assets/.
    Used by all three PDF conversion paths (docling, pymupdf4llm, pymupdf page-by-page).
    Deduplicates images by xref so the same image reused on multiple pages
    is only saved once.
    """
    try:
        import fitz
        from .markdown_writer import assets_dir_for
        assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
        os.makedirs(assets_dir, exist_ok=True)

        doc = fitz.open(source_file)
        saved_xrefs: set[int] = set()
        img_counter = 0

        for page_idx in range(len(doc)):
            page = doc[page_idx]
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
                    filename = f"image_{img_counter:03d}_p{page_idx + 1}.{ext}"
                    img_path = os.path.join(assets_dir, filename)
                    with open(img_path, "wb") as fh:
                        fh.write(img_bytes)
                    output.asset_paths.append(f"assets/{filename}")
                    saved_xrefs.add(xref)
                    log_info(f"Saved image: {filename} ({len(img_bytes)} bytes)")
                except Exception as e:
                    log_warn(f"Could not extract image xref={xref}: {e}")

        doc.close()
        log_info(f"Image extraction complete | saved={img_counter}")

    except Exception as e:
        log_warn(f"fitz image extraction failed: {e}")


# ---------------------------------------------------------------------------
# pymupdf4llm path
# ---------------------------------------------------------------------------

def _convert_pymupdf4llm(
    source_file, alias, output_root, preserve_images, rebuild_toc,
    preserve_page_numbers, use_subfolder, output, confidence, log_info, log_warn, progress
) -> ConversionOutput:
    import pymupdf4llm
    import fitz

    log_info("Using pymupdf4llm engine for PDF.")
    output.engine_used = "pymupdf4llm"
    progress(0.1)

    md_text = pymupdf4llm.to_markdown(source_file)
    if not md_text.strip():
        log_warn("pymupdf4llm returned empty output.")
        confidence.text_extraction = "Low"
        confidence.derive_overall()
        return output

    progress(0.5)

    # Extract TOC from PDF outline
    if rebuild_toc:
        _extract_fitz_toc(source_file, output, log_info)

    # Extract and save images via fitz
    if preserve_images and output_root:
        _extract_fitz_images(source_file, alias, output_root, output, log_info, log_warn, use_subfolder)

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
    log_info, log_warn, progress, use_ocr: bool = False
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

    page_sections = []
    ocr_confidences = []
    text_quality_flags = []

    for page_idx in range(total_pages):
        page_num = page_idx + 1
        page = doc[page_idx]
        prog = 0.1 + (page_idx / total_pages) * 0.75
        progress(prog)

        page_parts = []

        # Page anchor
        if preserve_page_numbers:
            page_parts.append(f'<a id="page-{page_num}"></a>\n\n---\n*Page {page_num}*\n')

        # Text extraction
        if use_ocr:
            page_text, ocr_conf = _ocr_page(page, language, log_info, log_warn)
            ocr_confidences.append(ocr_conf)
            if page_text.strip():
                page_parts.append(page_text)
            text_quality_flags.append(bool(page_text.strip()))
        else:
            text = page.get_text("markdown") or page.get_text("text")
            text = text.strip()
            if text:
                page_parts.append(text)
            text_quality_flags.append(bool(text))

        # Image extraction
        if preserve_images and assets_dir:
            img_refs = _extract_page_images(
                doc, page, page_num, assets_dir, output, log_info, rel_prefix
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

    doc.close()
    progress(0.88)

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


# ---------------------------------------------------------------------------
# Page-level OCR
# ---------------------------------------------------------------------------

def _ocr_page(page, language: str, log_info, log_warn) -> tuple[str, str]:
    """Render a fitz page to an image and OCR it. Returns (text, confidence_label)."""
    try:
        import fitz
        from PIL import Image
        import io

        mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better OCR resolution
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img_bytes = pix.tobytes("png")
        pil_image = Image.open(io.BytesIO(img_bytes))

        result = ocr_engine.run_ocr(pil_image, language=language)
        return result.text, result.confidence_label

    except Exception as e:
        log_warn(f"Page OCR failed: {e}")
        return "", "Failed"


# ---------------------------------------------------------------------------
# Image extraction
# ---------------------------------------------------------------------------

def _extract_page_images(
    doc, page, page_num: int, assets_dir: str,
    output: ConversionOutput, log_info,
    rel_prefix: str = "assets/",
) -> list[str]:
    """Extract embedded images from a fitz page, save to assets/, return Markdown refs."""
    import fitz

    refs = []
    try:
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            xref = img_info[0]
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
                refs.append(f"\n![Image from page {page_num}]({rel_path})\n")
                log_info(f"Saved image: {filename}")
            except Exception:
                pass
    except Exception:
        pass
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
        doc = fitz.open(pdf_path)
        _extract_fitz_toc_from_doc(doc, output, log_info)
        doc.close()
    except Exception:
        pass


def _extract_fitz_toc_from_doc(doc, output: ConversionOutput, log_info) -> None:
    try:
        toc = doc.get_toc()
        if toc:
            log_info(f"Extracted PDF outline | entries={len(toc)}")
            for level, title, page in toc:
                output.add_toc_entry(level, title, page)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Page anchor injection
# ---------------------------------------------------------------------------

def _inject_page_anchors_from_text(md_text: str) -> str:
    """
    pymupdf4llm includes page separators as horizontal rules.
    Detect them and inject page anchors. Very basic heuristic.
    """
    lines = md_text.splitlines()
    result = []
    page_num = 0
    for line in lines:
        if re.match(r'^-{3,}\s*$', line) and page_num == 0:
            page_num = 1
            result.append(f'<a id="page-{page_num}"></a>\n\n---\n*Page {page_num}*')
        elif re.match(r'^-{3,}\s*$', line):
            page_num += 1
            result.append(f'<a id="page-{page_num}"></a>\n\n---\n*Page {page_num}*')
        else:
            result.append(line)
    return "\n".join(result)
