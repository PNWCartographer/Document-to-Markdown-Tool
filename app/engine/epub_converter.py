"""
EPUB (.epub) to Markdown converter.

Conversion approach:
  - Read EPUB spine order (reading sequence).
  - Each chapter/document in spine → DocumentSection.
  - HTML content → Markdown via BeautifulSoup parsing:
    - <h1>-<h6> → # headings
    - <p> → paragraphs
    - <ul>/<ol> → lists
    - <table> → Markdown tables
    - <img> → extracted from EPUB archive, saved to assets
    - <blockquote> → > blockquotes
    - <code>/<pre> → code blocks
  - TOC extracted from NCX or EPUB3 nav document → toc_entries.
  - Embedded images extracted from EPUB zip archive.
  - Progress reported per-chapter.

Dependencies: ebooklib >= 0.18, beautifulsoup4 >= 4.12.0
"""

import os
import re
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput, rows_to_markdown_table
from .logger import ConversionLogger


def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    preserve_images: bool = True,
    use_subfolder: bool = True,
    rebuild_toc: bool = True,
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> ConversionOutput:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence
    output.engine_used = "ebooklib"

    def log_info(msg):
        if logger: logger.info(msg)
    def log_warn(msg):
        if logger: logger.warning(msg)
        confidence.add_warning(msg)
    def progress(p):
        if progress_callback: progress_callback(p)

    log_info(f"EPUB converter started | file={os.path.basename(source_file)}")
    progress(0.05)

    try:
        book = epub.read_epub(source_file, options={"ignore_ncx": False})
    except Exception as e:
        log_warn(f"ebooklib failed to open EPUB: {e}")
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        return output

    # Assets directory for image extraction
    assets_dir = None
    rel_prefix = "assets/"
    if preserve_images and output_root:
        from .markdown_writer import assets_dir_for, assets_rel_prefix_for
        assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
        rel_prefix = assets_rel_prefix_for(source_file, alias, use_subfolder)
        os.makedirs(assets_dir, exist_ok=True)

    # ── Extract and save images from EPUB archive ────────
    img_counter = 0
    image_map: dict[str, str] = {}  # original href → saved rel_path

    if preserve_images and assets_dir:
        for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
            try:
                img_counter += 1
                ext = _guess_ext(item.get_name(), item.media_type)
                filename = f"epub_img_{img_counter:03d}.{ext}"
                img_path = os.path.join(assets_dir, filename)

                with open(img_path, "wb") as fh:
                    fh.write(item.get_content())

                rel_path = f"{rel_prefix}{filename}"
                output.asset_paths.append(rel_path)
                image_map[item.get_name()] = rel_path
                # Also map the filename alone for src="images/photo.jpg" style refs
                image_map[os.path.basename(item.get_name())] = rel_path
                log_info(f"Saved image: {filename} ({len(item.get_content())} bytes)")
            except Exception as e:
                log_warn(f"Could not extract EPUB image '{item.get_name()}': {e}")

    # ── Extract TOC ──────────────────────────────────────
    if rebuild_toc:
        _extract_toc(book, output, log_info)

    # ── Convert spine documents ──────────────────────────
    spine_items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
    # Filter to only items in spine order
    spine_ids = [item_id for (item_id, _linear) in book.spine]
    spine_lookup = {item.get_id(): item for item in spine_items}
    ordered_items = [spine_lookup[sid] for sid in spine_ids if sid in spine_lookup]

    if not ordered_items:
        # Fallback: just use all document items
        ordered_items = spine_items

    total_chapters = len(ordered_items)
    log_info(f"EPUB spine | chapters={total_chapters} images={img_counter}")

    chapter_num = 0
    table_count = 0

    for ch_idx, item in enumerate(ordered_items):
        prog = 0.1 + (ch_idx / max(total_chapters, 1)) * 0.8
        progress(prog)

        try:
            html_content = item.get_body_content()
            if html_content is None:
                html_content = item.get_content()
            if isinstance(html_content, bytes):
                html_content = html_content.decode("utf-8", errors="replace")
        except Exception as e:
            log_warn(f"Could not read chapter content: {e}")
            continue

        soup = BeautifulSoup(html_content, "html.parser")

        # Skip items with no meaningful text (cover pages, blank chapters)
        text_content = soup.get_text(strip=True)
        if len(text_content) < 10:
            continue

        chapter_num += 1
        parts = []

        # Convert HTML elements to Markdown
        body = soup.find("body") or soup
        md_text, ch_tables = _html_to_markdown(body, image_map)
        table_count += ch_tables

        if md_text.strip():
            # Extract chapter title from first heading
            first_heading = soup.find(re.compile(r'^h[1-6]$'))
            chapter_title = first_heading.get_text(strip=True) if first_heading else f"Chapter {chapter_num}"

            output.add_section(
                heading=f"## {chapter_title}",
                body=md_text.strip(),
                page_number=chapter_num,
            )

    progress(0.95)

    # Confidence
    confidence.text_extraction = "High" if chapter_num > 0 else "Low"
    confidence.table_structure = "High" if table_count > 0 else "N/A"
    confidence.document_order = "High"
    confidence.image_extraction = "High" if img_counter > 0 else "N/A"
    confidence.image_placement = "Medium" if img_counter > 0 else "N/A"
    confidence.ocr_confidence = "N/A"
    confidence.add_note("Engine: ebooklib (EPUB structured reading)")
    confidence.derive_overall()

    log_info(f"EPUB conversion complete | chapters={chapter_num} images={img_counter} tables={table_count}")
    progress(1.0)
    return output


# ---------------------------------------------------------------------------
# TOC extraction
# ---------------------------------------------------------------------------

def _extract_toc(book, output: ConversionOutput, log_info) -> None:
    """Extract TOC from EPUB NCX or nav document."""
    try:
        toc = book.toc
        if toc:
            _walk_toc(toc, output, level=1)
            log_info(f"Extracted EPUB TOC | entries={len(output.toc_entries)}")
    except Exception:
        pass


def _walk_toc(toc_items, output: ConversionOutput, level: int) -> None:
    """Recursively walk the EPUB TOC tree."""
    for item in toc_items:
        if isinstance(item, tuple) and len(item) == 2:
            # (Section, children) — nested TOC
            section, children = item
            title = getattr(section, 'title', str(section))
            output.add_toc_entry(level, title)
            _walk_toc(children, output, level + 1)
        else:
            # ebooklib.epub.Link
            title = getattr(item, 'title', str(item))
            output.add_toc_entry(level, title)


# ---------------------------------------------------------------------------
# HTML → Markdown conversion
# ---------------------------------------------------------------------------

def _html_to_markdown(element, image_map: dict) -> tuple[str, int]:
    """
    Convert a BeautifulSoup element tree to Markdown.
    Returns (markdown_text, table_count).
    """
    parts = []
    table_count = 0

    for child in element.children:
        tag = getattr(child, 'name', None)

        if tag is None:
            # NavigableString (text node)
            text = str(child).strip()
            if text:
                parts.append(text)
            continue

        # Headings
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            level = int(tag[1])
            prefix = "#" * level
            text = child.get_text(strip=True)
            if text:
                parts.append(f"\n{prefix} {text}\n")

        # Paragraphs
        elif tag == 'p':
            text = _inline_to_md(child, image_map)
            if text.strip():
                parts.append(f"\n{text}\n")

        # Blockquotes
        elif tag == 'blockquote':
            inner, tc = _html_to_markdown(child, image_map)
            table_count += tc
            if inner.strip():
                quoted = "\n".join(f"> {line}" for line in inner.strip().splitlines())
                parts.append(f"\n{quoted}\n")

        # Unordered list
        elif tag == 'ul':
            items = _list_to_md(child, ordered=False, image_map=image_map)
            if items:
                parts.append(f"\n{items}\n")

        # Ordered list
        elif tag == 'ol':
            items = _list_to_md(child, ordered=True, image_map=image_map)
            if items:
                parts.append(f"\n{items}\n")

        # Code blocks
        elif tag == 'pre':
            code = child.get_text()
            if code.strip():
                parts.append(f"\n```\n{code.rstrip()}\n```\n")

        # Inline code (standalone)
        elif tag == 'code' and child.parent and child.parent.name != 'pre':
            text = child.get_text()
            if text:
                parts.append(f"`{text}`")

        # Tables
        elif tag == 'table':
            md_table = _html_table_to_md(child)
            if md_table:
                parts.append(f"\n{md_table}\n")
                table_count += 1

        # Images
        elif tag == 'img':
            src = child.get('src', '')
            alt = child.get('alt', 'Image')
            # Resolve image path through our map
            resolved = _resolve_image(src, image_map)
            if resolved:
                parts.append(f"![{alt}]({resolved})")

        # Divs, sections, articles — recurse
        elif tag in ('div', 'section', 'article', 'span', 'main', 'aside', 'figure', 'figcaption'):
            inner, tc = _html_to_markdown(child, image_map)
            table_count += tc
            if inner.strip():
                parts.append(inner)

        # Horizontal rule
        elif tag == 'hr':
            parts.append("\n---\n")

        # Line break
        elif tag == 'br':
            parts.append("  \n")

        # Bold / italic / emphasis
        elif tag in ('strong', 'b'):
            text = _inline_to_md(child, image_map)
            if text.strip():
                parts.append(f"**{text.strip()}**")
        elif tag in ('em', 'i'):
            text = _inline_to_md(child, image_map)
            if text.strip():
                parts.append(f"*{text.strip()}*")

        # Links
        elif tag == 'a':
            href = child.get('href', '')
            text = child.get_text(strip=True)
            if text and href:
                parts.append(f"[{text}]({href})")
            elif text:
                parts.append(text)

        # Anything else — extract text
        else:
            inner, tc = _html_to_markdown(child, image_map)
            table_count += tc
            if inner.strip():
                parts.append(inner)

    return " ".join(parts) if not any('\n' in p for p in parts) else "\n".join(parts), table_count


def _inline_to_md(element, image_map: dict) -> str:
    """Convert inline HTML to Markdown (bold, italic, links, images, text)."""
    parts = []
    for child in element.children:
        tag = getattr(child, 'name', None)
        if tag is None:
            parts.append(str(child))
        elif tag in ('strong', 'b'):
            text = child.get_text()
            if text:
                parts.append(f"**{text}**")
        elif tag in ('em', 'i'):
            text = child.get_text()
            if text:
                parts.append(f"*{text}*")
        elif tag == 'code':
            text = child.get_text()
            if text:
                parts.append(f"`{text}`")
        elif tag == 'a':
            href = child.get('href', '')
            text = child.get_text()
            if text and href:
                parts.append(f"[{text}]({href})")
            elif text:
                parts.append(text)
        elif tag == 'img':
            src = child.get('src', '')
            alt = child.get('alt', 'Image')
            resolved = _resolve_image(src, image_map)
            if resolved:
                parts.append(f"![{alt}]({resolved})")
        elif tag == 'br':
            parts.append("  \n")
        elif tag == 'span':
            parts.append(_inline_to_md(child, image_map))
        else:
            parts.append(child.get_text())
    return "".join(parts)


def _list_to_md(list_el, ordered: bool, image_map: dict, indent: int = 0) -> str:
    """Convert <ul> or <ol> to Markdown list."""
    items = []
    counter = 1
    prefix_base = "  " * indent

    for li in list_el.find_all('li', recursive=False):
        text = ""
        sub_lists = []

        for child in li.children:
            tag = getattr(child, 'name', None)
            if tag in ('ul', 'ol'):
                sub_lists.append((tag, child))
            elif tag is None:
                text += str(child).strip()
            else:
                text += _inline_to_md(child, image_map)

        if ordered:
            prefix = f"{prefix_base}{counter}. "
            counter += 1
        else:
            prefix = f"{prefix_base}- "

        if text.strip():
            items.append(f"{prefix}{text.strip()}")

        for sub_tag, sub_el in sub_lists:
            sub_md = _list_to_md(sub_el, ordered=(sub_tag == 'ol'),
                                 image_map=image_map, indent=indent + 1)
            if sub_md:
                items.append(sub_md)

    return "\n".join(items)


def _html_table_to_md(table_el) -> str:
    """Convert an HTML <table> to Markdown table syntax."""
    rows_data = []

    # Check for thead/tbody structure
    thead = table_el.find('thead')
    tbody = table_el.find('tbody')

    if thead:
        for tr in thead.find_all('tr'):
            cells = [_cell_text(td) for td in tr.find_all(['th', 'td'])]
            rows_data.append(cells)

    body_el = tbody if tbody else table_el
    for tr in body_el.find_all('tr', recursive=(not tbody)):
        cells = [_cell_text(td) for td in tr.find_all(['th', 'td'])]
        if cells:
            rows_data.append(cells)

    if not rows_data:
        return ""

    headers = rows_data[0]
    body_rows = rows_data[1:] if len(rows_data) > 1 else []

    col_count = max(len(r) for r in rows_data)
    headers = _pad(headers, col_count)
    body_rows = [_pad(r, col_count) for r in body_rows]

    return rows_to_markdown_table(headers, body_rows)


def _cell_text(td) -> str:
    """Get cell text, collapsing whitespace."""
    return td.get_text(strip=True).replace("\n", " ")


def _resolve_image(src: str, image_map: dict) -> str:
    """Try to resolve an image src to our saved asset path."""
    if not src:
        return ""
    # Direct match
    if src in image_map:
        return image_map[src]
    # Try basename
    basename = os.path.basename(src)
    if basename in image_map:
        return image_map[basename]
    # Try without leading ../
    clean = src.lstrip("./").lstrip("../")
    if clean in image_map:
        return image_map[clean]
    return ""


def _guess_ext(filename: str, media_type: str) -> str:
    """Guess file extension from filename or MIME type."""
    ext = os.path.splitext(filename)[1].lstrip(".")
    if ext:
        return "jpg" if ext == "jpeg" else ext
    mime_map = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "image/webp": "webp",
    }
    return mime_map.get(media_type, "png")


def _pad(lst: list, length: int) -> list:
    return list(lst) + [""] * max(0, length - len(lst))
