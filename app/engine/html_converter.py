"""
HTML (.html, .htm) to Markdown converter.

Conversion approach:
  - Read HTML file with encoding detection (BOM, meta charset, BS4 auto).
  - Strip non-content elements: script, style, nav, header, footer, noscript.
  - Extract and save images referenced via <img> tags.
  - Convert HTML to Markdown using markdownify (primary) or
    BeautifulSoup manual traversal (fallback).
  - Build TOC from heading elements.
  - Progress reported across stages.

Dependencies: beautifulsoup4 >= 4.12.0
Optional:     markdownify >= 0.14.1 (falls back to manual conversion)
"""

import os
import re
import shutil
from typing import Optional, Callable
from urllib.parse import urlparse, unquote

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput, rows_to_markdown_table, _pad
from .logger import ConversionLogger

try:
    import markdownify as _md
    _HAS_MARKDOWNIFY = True
except ImportError:
    _HAS_MARKDOWNIFY = False

_STRIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript",
               "iframe", "svg", "form"}

_IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif",
             ".webp", ".svg"}


def convert(
    source_file: str,
    alias: str = "",
    output_root: str = "",
    preserve_images: bool = True,
    use_subfolder: bool = True,
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> ConversionOutput:
    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence

    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        confidence.add_warning(f"beautifulsoup4 not installed: {e}")
        return output

    output.engine_used = "markdownify" if _HAS_MARKDOWNIFY else "beautifulsoup4"

    def log_info(msg):
        if logger: logger.info(msg)
    def log_warn(msg):
        if logger: logger.warning(msg)
        confidence.add_warning(msg)
    def progress(p):
        if progress_callback: progress_callback(p)

    log_info(f"HTML converter started | file={os.path.basename(source_file)}")
    progress(0.05)

    # ── Read file with encoding detection ────────────────
    raw = _read_file(source_file)
    if raw is None:
        log_warn(f"Could not read HTML file: {source_file}")
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        return output

    soup = BeautifulSoup(raw, "html.parser")
    progress(0.15)

    # ── Strip non-content elements ───────────────────────
    for tag in soup.find_all(list(_STRIP_TAGS)):
        tag.decompose()

    # ── Extract page title ───────────────────────────────
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""
    if not page_title:
        page_title = os.path.splitext(os.path.basename(source_file))[0]

    # ── Image extraction ─────────────────────────────────
    assets_dir = None
    rel_prefix = "assets/"
    image_map: dict[str, str] = {}
    img_count = 0

    if preserve_images and output_root:
        from .markdown_writer import assets_dir_for, assets_rel_prefix_for
        assets_dir = assets_dir_for(source_file, output_root, alias, use_subfolder)
        rel_prefix = assets_rel_prefix_for(source_file, alias, use_subfolder)
        os.makedirs(assets_dir, exist_ok=True)

    if preserve_images and assets_dir:
        source_dir = os.path.dirname(os.path.abspath(source_file))
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src or src.startswith("data:"):
                continue
            resolved = _resolve_local_image(src, source_dir)
            if resolved and os.path.isfile(resolved):
                try:
                    img_count += 1
                    ext = os.path.splitext(resolved)[1].lower() or ".png"
                    filename = f"html_img_{img_count:03d}{ext}"
                    dest = os.path.join(assets_dir, filename)
                    shutil.copy2(resolved, dest)
                    rel_path = f"{rel_prefix}{filename}"
                    output.asset_paths.append(rel_path)
                    image_map[src] = rel_path
                    img.attrs["src"] = rel_path
                    log_info(f"Saved image: {filename}")
                except Exception as e:
                    log_warn(f"Could not copy image '{src}': {e}")

    progress(0.30)

    # ── Build TOC from headings ──────────────────────────
    for heading in soup.find_all(re.compile(r"^h[1-6]$")):
        level = int(heading.name[1])
        text = heading.get_text(strip=True)
        if text:
            output.add_toc_entry(level, text)

    progress(0.40)

    # ── Convert to Markdown ──────────────────────────────
    body = soup.find("body") or soup
    text_content = body.get_text(strip=True)

    if not text_content:
        log_warn("HTML file contains no text content.")
        confidence.text_extraction = "Low"
        confidence.overall = "Low"
        progress(1.0)
        return output

    if _HAS_MARKDOWNIFY:
        md_text = _convert_with_markdownify(body)
        log_info("Converted HTML with markdownify engine")
    else:
        md_text = _convert_with_bs4(body, image_map)
        log_info("Converted HTML with BeautifulSoup fallback (markdownify not installed)")

    progress(0.80)

    # ── Clean up excessive whitespace ────────────────────
    md_text = re.sub(r"\n{3,}", "\n\n", md_text).strip()

    if md_text:
        output.add_section(
            heading=f"# {page_title}",
            body=md_text,
            page_number=1,
        )

    progress(0.90)

    # ── Confidence scoring ───────────────────────────────
    confidence.text_extraction = "High"
    table_count = len(soup.find_all("table"))
    confidence.table_structure = "High" if table_count > 0 else "N/A"
    confidence.document_order = "High"
    confidence.image_extraction = "High" if img_count > 0 else "N/A"
    confidence.image_placement = "Medium" if img_count > 0 else "N/A"
    confidence.ocr_confidence = "N/A"
    confidence.add_note(f"Engine: {output.engine_used}")
    if table_count:
        confidence.add_note(f"Tables detected: {table_count}")
    confidence.derive_overall()

    log_info(f"HTML conversion complete | images={img_count} tables={table_count}")
    progress(1.0)
    return output


# ---------------------------------------------------------------------------
# File reading with encoding detection
# ---------------------------------------------------------------------------

def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as fh:
            raw_bytes = fh.read()
    except OSError:
        return None

    # Try UTF-8 BOM, then UTF-8, then latin-1 (never fails)
    for enc in ("utf-8-sig", "utf-8"):
        try:
            return raw_bytes.decode(enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return raw_bytes.decode("latin-1")


# ---------------------------------------------------------------------------
# Image path resolution
# ---------------------------------------------------------------------------

def _resolve_local_image(src: str, source_dir: str) -> Optional[str]:
    parsed = urlparse(src)
    if parsed.scheme in ("http", "https", "ftp"):
        return None
    local_path = unquote(parsed.path)
    if os.path.isabs(local_path):
        resolved = os.path.realpath(os.path.normpath(local_path))
    else:
        resolved = os.path.realpath(os.path.normpath(os.path.join(source_dir, local_path)))
    # Prevent path traversal — resolved path must stay within (or adjacent to)
    # the source directory.  realpath resolves symlinks so a symlink pointing
    # outside the source tree is correctly rejected.
    norm_source = os.path.realpath(os.path.normpath(source_dir))
    if not resolved.startswith(norm_source + os.sep) and resolved != norm_source:
        return None
    return resolved


# ---------------------------------------------------------------------------
# markdownify conversion
# ---------------------------------------------------------------------------

def _convert_with_markdownify(body) -> str:
    return _md.markdownify(
        str(body),
        heading_style="ATX",
        bullets="-",
        code_language="",
    )


# ---------------------------------------------------------------------------
# BeautifulSoup fallback (mirrors epub_converter._html_to_markdown)
# ---------------------------------------------------------------------------

def _convert_with_bs4(element, image_map: dict) -> str:
    parts, _ = _html_to_md(element, image_map)
    return parts


def _html_to_md(element, image_map: dict) -> tuple[str, int]:
    parts = []
    table_count = 0

    for child in element.children:
        tag = getattr(child, "name", None)
        if tag is None:
            text = str(child).strip()
            if text:
                parts.append(text)
            continue

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            text = child.get_text(strip=True)
            if text:
                parts.append(f"\n{'#' * level} {text}\n")

        elif tag == "p":
            text = _inline(child, image_map)
            if text.strip():
                parts.append(f"\n{text}\n")

        elif tag == "blockquote":
            inner, tc = _html_to_md(child, image_map)
            table_count += tc
            if inner.strip():
                quoted = "\n".join(f"> {line}" for line in inner.strip().splitlines())
                parts.append(f"\n{quoted}\n")

        elif tag == "ul":
            md = _list_md(child, ordered=False, image_map=image_map)
            if md:
                parts.append(f"\n{md}\n")

        elif tag == "ol":
            md = _list_md(child, ordered=True, image_map=image_map)
            if md:
                parts.append(f"\n{md}\n")

        elif tag == "pre":
            code = child.get_text()
            if code.strip():
                parts.append(f"\n```\n{code.rstrip()}\n```\n")

        elif tag == "code" and child.parent and child.parent.name != "pre":
            text = child.get_text()
            if text:
                parts.append(f"`{text}`")

        elif tag == "table":
            md_table = _table_md(child)
            if md_table:
                parts.append(f"\n{md_table}\n")
                table_count += 1

        elif tag == "img":
            src = child.get("src", "")
            alt = child.get("alt", "Image")
            resolved = image_map.get(src, src)
            if resolved:
                parts.append(f"![{alt}]({resolved})")

        elif tag in ("div", "section", "article", "span", "main",
                      "aside", "figure", "figcaption"):
            inner, tc = _html_to_md(child, image_map)
            table_count += tc
            if inner.strip():
                parts.append(inner)

        elif tag == "hr":
            parts.append("\n---\n")

        elif tag == "br":
            parts.append("  \n")

        elif tag in ("strong", "b"):
            text = _inline(child, image_map)
            if text.strip():
                parts.append(f"**{text.strip()}**")

        elif tag in ("em", "i"):
            text = _inline(child, image_map)
            if text.strip():
                parts.append(f"*{text.strip()}*")

        elif tag == "a":
            href = child.get("href", "")
            text = child.get_text(strip=True)
            if text and href:
                parts.append(f"[{text}]({href})")
            elif text:
                parts.append(text)

        else:
            inner, tc = _html_to_md(child, image_map)
            table_count += tc
            if inner.strip():
                parts.append(inner)

    return "\n\n".join(p.strip("\n") for p in parts if p.strip()), table_count


def _inline(element, image_map: dict) -> str:
    parts = []
    for child in element.children:
        tag = getattr(child, "name", None)
        if tag is None:
            parts.append(str(child))
        elif tag in ("strong", "b"):
            text = child.get_text()
            if text: parts.append(f"**{text}**")
        elif tag in ("em", "i"):
            text = child.get_text()
            if text: parts.append(f"*{text}*")
        elif tag == "code":
            text = child.get_text()
            if text: parts.append(f"`{text}`")
        elif tag == "a":
            href = child.get("href", "")
            text = child.get_text()
            if text and href: parts.append(f"[{text}]({href})")
            elif text: parts.append(text)
        elif tag == "img":
            src = child.get("src", "")
            alt = child.get("alt", "Image")
            resolved = image_map.get(src, src)
            if resolved: parts.append(f"![{alt}]({resolved})")
        elif tag == "br":
            parts.append("  \n")
        elif tag == "span":
            parts.append(_inline(child, image_map))
        else:
            parts.append(child.get_text())
    return "".join(parts)


def _list_md(list_el, ordered: bool, image_map: dict, indent: int = 0) -> str:
    items = []
    counter = 1
    prefix_base = "  " * indent
    for li in list_el.find_all("li", recursive=False):
        text = ""
        sub_lists = []
        for child in li.children:
            tag = getattr(child, "name", None)
            if tag in ("ul", "ol"):
                sub_lists.append((tag, child))
            elif tag is None:
                text += str(child).strip()
            else:
                text += _inline(child, image_map)
        prefix = f"{prefix_base}{counter}. " if ordered else f"{prefix_base}- "
        if ordered:
            counter += 1
        if text.strip():
            items.append(f"{prefix}{text.strip()}")
        for sub_tag, sub_el in sub_lists:
            sub = _list_md(sub_el, ordered=(sub_tag == "ol"),
                           image_map=image_map, indent=indent + 1)
            if sub:
                items.append(sub)
    return "\n".join(items)


def _table_md(table_el) -> str:
    rows_data = []
    thead = table_el.find("thead")
    tbody = table_el.find("tbody")
    if thead:
        for tr in thead.find_all("tr"):
            cells = [td.get_text(strip=True).replace("\n", " ")
                     for td in tr.find_all(["th", "td"])]
            rows_data.append(cells)
    body_el = tbody if tbody else table_el
    for tr in body_el.find_all("tr", recursive=(not tbody)):
        # Skip rows that belong to <thead> when iterating the whole table
        if not tbody and thead and tr.parent == thead:
            continue
        cells = [td.get_text(strip=True).replace("\n", " ")
                 for td in tr.find_all(["th", "td"])]
        if cells:
            rows_data.append(cells)
    if not rows_data:
        return ""
    col_count = max(len(r) for r in rows_data)
    headers = _pad(rows_data[0], col_count)
    body_rows = [_pad(r, col_count) for r in rows_data[1:]]
    return rows_to_markdown_table(headers, body_rows)
