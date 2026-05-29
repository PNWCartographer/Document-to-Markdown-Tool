"""
Alternative output format writers (JSON, HTML, Plain Text).

Markdown is handled by markdown_writer.py — this module covers the rest.
Each builder takes a ConversionOutput and returns a formatted string.
"""

import html as _html_mod
import json
import os
import re
import datetime
from typing import Optional

from .markdown_writer import (
    ConversionOutput,
    _safe_stem,
    output_dir_for,
    assets_dir_for,
)


# ---------------------------------------------------------------------------
# Format registry
# ---------------------------------------------------------------------------

FORMATS = {
    "Markdown":       {"ext": ".md",    "label": "Markdown (.md)"},
    "JSON":           {"ext": ".json",  "label": "JSON (.json)"},
    "HTML":           {"ext": ".html",  "label": "HTML (.html)"},
    "Plain Text":     {"ext": ".txt",   "label": "Plain Text (.txt)"},
    "AI-Ready Chunks": {"ext": ".jsonl", "label": "AI-Ready Chunks (.jsonl)"},
    "Searchable PDF": {"ext": ".pdf",   "label": "Searchable PDF (.pdf)"},
}

FORMAT_NAMES = list(FORMATS.keys())


def extension_for(fmt: str) -> str:
    """Return the file extension for the given format name."""
    return FORMATS.get(fmt, FORMATS["Markdown"])["ext"]


# ---------------------------------------------------------------------------
# Path helper (format-aware)
# ---------------------------------------------------------------------------

def output_path_for(
    source_file: str,
    output_root: str,
    fmt: str = "Markdown",
    alias: str = "",
    use_subfolder: bool = True,
) -> str:
    """Return the full output file path for the given format."""
    stem = alias if alias else _safe_stem(source_file)
    out_dir = output_dir_for(source_file, output_root, alias, use_subfolder)
    ext = extension_for(fmt)
    return os.path.join(out_dir, stem + ext)


# ═══════════════════════════════════════════════════════════════════════════
# JSON
# ═══════════════════════════════════════════════════════════════════════════

def build_json(
    output: ConversionOutput,
    include_confidence: bool = True,
    include_page_numbers: bool = True,
    rebuild_toc: bool = True,
) -> str:
    """Build a structured JSON document from conversion output."""
    doc: dict = {
        "document": {
            "source_file": os.path.basename(output.source_file),
            "converted_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "engine": output.engine_used or "unknown",
            "format_version": "1.0",
        },
    }

    # Confidence
    if include_confidence and output.confidence:
        c = output.confidence
        doc["confidence"] = {
            "overall": c.overall,
            "text_extraction": c.text_extraction,
            "table_structure": c.table_structure,
            "image_extraction": c.image_extraction,
            "image_placement": c.image_placement,
            "document_order": c.document_order,
            "ocr_confidence": c.ocr_confidence,
            "manual_review_recommended": c.manual_review_recommended,
            "notes": list(c.notes),
            "warnings": list(c.warnings),
        }

    # Table of contents
    if rebuild_toc and output.toc_entries:
        doc["table_of_contents"] = [
            {"level": level, "title": title, "page": page}
            for level, title, page in output.toc_entries
        ]

    # Sections
    sections = []
    for section in output.sections:
        entry: dict = {}
        if section.heading:
            entry["heading"] = section.heading.lstrip("#").strip()
        if section.body:
            entry["body"] = section.body.strip()
        if include_page_numbers and section.page_number is not None:
            entry["page"] = section.page_number
        if entry:
            sections.append(entry)
    doc["sections"] = sections

    # Assets and warnings
    doc["assets"] = [os.path.basename(p) for p in output.asset_paths]
    doc["warnings"] = list(output.warnings)

    return json.dumps(doc, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════════
# HTML
# ═══════════════════════════════════════════════════════════════════════════

_CSS = """\
:root { color-scheme: light dark; }
body {
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width: 52em; margin: 2em auto; padding: 0 1.5em;
    line-height: 1.6; color: #1a1a1a; background: #fff;
}
@media (prefers-color-scheme: dark) {
    body { color: #d4d4d4; background: #1e1e1e; }
    a { color: #6cb6ff; }
    table, th, td { border-color: #444; }
    th { background: #2a2a2a; }
    blockquote { border-color: #555; color: #aaa; }
    hr { border-color: #444; }
    .page-marker { color: #888; border-color: #444; }
    pre { background: #2a2a2a; }
}
h1,h2,h3,h4,h5,h6 { margin-top: 1.5em; margin-bottom: 0.5em; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ccc; padding: 0.5em 0.75em; text-align: left; }
th { background: #f5f5f5; font-weight: 600; }
blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #666; }
pre { background: #f6f6f6; padding: 1em; overflow-x: auto; border-radius: 4px; }
code { font-size: 0.9em; }
img { max-width: 100%; height: auto; }
.page-marker {
    text-align: center; color: #999; border-top: 1px solid #ddd;
    padding-top: 0.5em; margin: 2em 0 1em; font-size: 0.85em;
}
.confidence {
    font-size: 0.85em; padding: 0.75em 1em;
    border-radius: 4px; margin-bottom: 2em;
}
.toc { margin: 1.5em 0; }
.toc ul { list-style: none; padding-left: 1.5em; }
.toc > ul { padding-left: 0; }
@media print {
    body { color: #000; background: #fff; }
    .page-marker { page-break-before: always; }
}"""


def build_html(
    output: ConversionOutput,
    include_confidence: bool = True,
    include_page_numbers: bool = True,
    rebuild_toc: bool = True,
) -> str:
    """Build a self-contained HTML document from conversion output."""
    title = os.path.splitext(os.path.basename(output.source_file))[0]

    parts: list[str] = []
    parts.append(
        f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        f"<meta charset=\"utf-8\">\n"
        f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{_esc(title)}</title>\n"
        f"<style>\n{_CSS}\n</style>\n"
        f"</head>\n<body>\n"
        f"<h1>{_esc(title)}</h1>\n"
    )

    # Confidence banner
    if include_confidence and output.confidence:
        c = output.confidence
        review = " Manual review recommended." if c.manual_review_recommended else ""
        parts.append(
            f'<blockquote class="confidence">'
            f"Conversion confidence: {_esc(c.overall)}.{_esc(review)}"
            f"</blockquote>\n"
        )

    # Table of contents
    if rebuild_toc and output.toc_entries:
        parts.append('<nav class="toc">\n<h2>Table of Contents</h2>\n<ul>\n')
        for level, title_text, page in output.toc_entries:
            indent = "  " * level
            anchor = f"#page-{page}" if page is not None else "#"
            parts.append(f'{indent}<li><a href="{anchor}">{_esc(title_text)}</a></li>\n')
        parts.append("</ul>\n</nav>\n<hr>\n")

    # Sections
    prev_page: Optional[int] = None
    for section in output.sections:
        if include_page_numbers and section.page_number is not None:
            if section.page_number != prev_page:
                parts.append(
                    f'<div class="page-marker" id="page-{section.page_number}">'
                    f"Page {section.page_number}</div>\n"
                )
                prev_page = section.page_number

        if section.heading:
            m = re.match(r'^(#{1,6})\s', section.heading)
            lvl = len(m.group(1)) if m else 2
            clean = section.heading.lstrip("#").strip()
            parts.append(f"<h{lvl}>{_esc(clean)}</h{lvl}>\n")

        if section.body:
            parts.append(_md_body_to_html(section.body.strip()))
            parts.append("\n")

    parts.append("</body>\n</html>\n")
    return "".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# Plain Text
# ═══════════════════════════════════════════════════════════════════════════

def build_plaintext(
    output: ConversionOutput,
    include_confidence: bool = True,
    include_page_numbers: bool = True,
    rebuild_toc: bool = True,
) -> str:
    """Build a clean plain-text document from conversion output."""
    lines: list[str] = []
    title = os.path.splitext(os.path.basename(output.source_file))[0]
    lines.append(title.upper())
    lines.append("=" * len(title))
    lines.append("")

    if include_confidence and output.confidence:
        c = output.confidence
        review = " Manual review recommended." if c.manual_review_recommended else ""
        lines.append(f"[Conversion confidence: {c.overall}.{review}]")
        lines.append("")

    if rebuild_toc and output.toc_entries:
        lines.append("TABLE OF CONTENTS")
        lines.append("-" * 17)
        for level, title_text, page in output.toc_entries:
            indent = "  " * (level - 1)
            pg = f"  (p. {page})" if page is not None else ""
            lines.append(f"{indent}{title_text}{pg}")
        lines.append("")
        lines.append("---")
        lines.append("")

    prev_page: Optional[int] = None
    for section in output.sections:
        if include_page_numbers and section.page_number is not None:
            if section.page_number != prev_page:
                lines.append(f"--- Page {section.page_number} ---")
                lines.append("")
                prev_page = section.page_number

        if section.heading:
            clean = section.heading.lstrip("#").strip()
            lines.append(clean.upper())
            lines.append("-" * len(clean))
            lines.append("")

        if section.body:
            lines.append(_strip_markdown(section.body.strip()))
            lines.append("")

    return "\n".join(lines).strip() + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# AI-Ready Chunks (JSONL)
# ═══════════════════════════════════════════════════════════════════════════

def build_rag_chunks(
    output: ConversionOutput,
    include_confidence: bool = True,
    include_page_numbers: bool = True,
    rebuild_toc: bool = True,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> str:
    """
    Produce JSONL where each line is a self-contained chunk for RAG ingestion.

    Chunking strategy:
      1. Split by sections first (natural document boundaries).
      2. Within sections, split by paragraph if section > chunk_size words.
      3. Overlap: include last chunk_overlap words from previous chunk.
      4. Preserve heading context: each chunk knows its parent heading.
    """
    source_name = os.path.basename(output.source_file)
    stem = _safe_stem(output.source_file)
    confidence_level = "N/A"
    if output.confidence:
        confidence_level = output.confidence.overall or "N/A"

    chunks: list[dict] = []
    chunk_idx = 0

    for section in output.sections:
        heading = section.heading.lstrip("#").strip() if section.heading else ""
        body = section.body.strip() if section.body else ""
        if not body:
            continue

        page = section.page_number

        # Split body into words for size check
        words = body.split()

        if len(words) <= chunk_size:
            # Small enough — single chunk
            chunk = _make_chunk(
                stem, chunk_idx, body, source_name, page,
                heading, confidence_level, include_confidence,
            )
            chunks.append(chunk)
            chunk_idx += 1
        else:
            # Split into paragraphs, then group into chunks
            paragraphs = re.split(r'\n\n+', body)
            current_words: list[str] = []
            overlap_words: list[str] = []

            for para in paragraphs:
                para_words = para.split()
                if not para_words:
                    continue

                # Split oversized paragraphs that exceed chunk_size on their own
                if len(para_words) > chunk_size:
                    if current_words:
                        text = " ".join(current_words)
                        chunk = _make_chunk(
                            stem, chunk_idx, text, source_name, page,
                            heading, confidence_level, include_confidence,
                        )
                        chunks.append(chunk)
                        chunk_idx += 1
                        overlap_words = current_words[-chunk_overlap:] if chunk_overlap else []
                        current_words = list(overlap_words)
                    for wi in range(0, len(para_words), chunk_size):
                        batch = para_words[wi:wi + chunk_size]
                        combined = current_words + batch
                        text = " ".join(combined)
                        chunk = _make_chunk(
                            stem, chunk_idx, text, source_name, page,
                            heading, confidence_level, include_confidence,
                        )
                        chunks.append(chunk)
                        chunk_idx += 1
                        overlap_words = combined[-chunk_overlap:] if chunk_overlap else []
                        current_words = list(overlap_words)
                    continue

                if current_words and len(current_words) + len(para_words) > chunk_size:
                    # Flush current chunk
                    text = " ".join(current_words)
                    chunk = _make_chunk(
                        stem, chunk_idx, text, source_name, page,
                        heading, confidence_level, include_confidence,
                    )
                    chunks.append(chunk)
                    chunk_idx += 1

                    # Keep overlap from end of current chunk
                    overlap_words = current_words[-chunk_overlap:] if chunk_overlap else []
                    current_words = list(overlap_words) + para_words
                else:
                    current_words.extend(para_words)

            # Flush remaining
            if current_words:
                text = " ".join(current_words)
                chunk = _make_chunk(
                    stem, chunk_idx, text, source_name, page,
                    heading, confidence_level, include_confidence,
                )
                chunks.append(chunk)
                chunk_idx += 1

    # Set total_chunks on all
    total = len(chunks)
    for ch in chunks:
        ch["metadata"]["total_chunks"] = total

    # Build JSONL
    lines = [json.dumps(ch, ensure_ascii=False) for ch in chunks]
    return "\n".join(lines) + "\n"


def _make_chunk(
    stem: str,
    idx: int,
    text: str,
    source: str,
    page: Optional[int],
    heading: str,
    confidence: str,
    include_confidence: bool,
) -> dict:
    """Build a single RAG chunk dict."""
    chunk = {
        "id": f"{stem}_chunk_{idx:04d}",
        "text": text,
        "metadata": {
            "source": source,
            "chunk_index": idx,
            "total_chunks": 0,  # filled in later
        },
    }
    if page is not None:
        chunk["metadata"]["page"] = page
    if heading:
        chunk["metadata"]["heading"] = heading
    if include_confidence:
        chunk["metadata"]["confidence"] = confidence
    return chunk


# ═══════════════════════════════════════════════════════════════════════════
# Unified writer
# ═══════════════════════════════════════════════════════════════════════════

def write_output(
    output: ConversionOutput,
    output_root: str,
    fmt: str,
    use_subfolder: bool = True,
    include_confidence: bool = True,
    include_page_numbers: bool = True,
    rebuild_toc: bool = True,
    overwrite: bool = False,
) -> str:
    """Write the conversion output in the specified format. Returns path written."""
    path = output_path_for(
        output.source_file, output_root, fmt,
        output.alias, use_subfolder,
    )
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    os.makedirs(
        assets_dir_for(output.source_file, output_root, output.alias, use_subfolder),
        exist_ok=True,
    )

    if not overwrite and os.path.exists(path):
        raise FileExistsError(f"Output file already exists: {path}")

    builders = {
        "JSON":       build_json,
        "HTML":       build_html,
        "Plain Text": build_plaintext,
        "AI-Ready Chunks": build_rag_chunks,
    }
    builder = builders.get(fmt)
    if builder is None:
        raise ValueError(f"Unsupported output format: {fmt}")

    content = builder(
        output,
        include_confidence=include_confidence,
        include_page_numbers=include_page_numbers,
        rebuild_toc=rebuild_toc,
    )

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


# ═══════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════

_PAGE_ANCHOR_RE = re.compile(r'<a\s+id="page-\d+"></a>')


def _esc(text: str) -> str:
    """HTML-escape special characters."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _md_body_to_html(body: str) -> str:
    """Lightweight Markdown-to-HTML for section bodies.

    Handles paragraphs, bold/italic, inline code, fenced code blocks,
    tables, images (file and base64), headings, and horizontal rules.
    Not a full Markdown parser — covers the patterns our converters produce.
    """
    out: list[str] = []
    in_table = False
    in_code = False
    _thead_closed = False

    for line in body.split("\n"):
        stripped = line.strip()

        # Fenced code blocks
        if stripped.startswith("```"):
            if in_code:
                out.append("</code></pre>")
                in_code = False
            else:
                out.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            out.append(_esc(line))
            continue

        # Table rows
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
                continue  # separator row
            if not in_table:
                out.append("<table><thead>")
                tag = "th"
                in_table = True
                _thead_closed = False
            else:
                if not _thead_closed:
                    out.append("</thead><tbody>")
                    _thead_closed = True
                tag = "td"
            row_html = "".join(f"<{tag}>{_esc(c)}</{tag}>" for c in cells)
            out.append(f"<tr>{row_html}</tr>")
            continue
        elif in_table:
            out.append("</tbody></table>" if _thead_closed else "</thead></table>")
            in_table = False
            _thead_closed = False

        # Images (file ref or base64)
        img_m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if img_m:
            alt, src = img_m.groups()
            # Use html.escape with quote=True to properly escape src attributes
            safe_src = src if src.startswith("data:") else _html_mod.escape(src, quote=True)
            out.append(f'<img src="{safe_src}" alt="{_html_mod.escape(alt, quote=True)}">')
            continue

        # Headings (rare in body, but handle gracefully)
        hm = re.match(r"^(#{1,6})\s+(.+)", line)
        if hm:
            lvl = len(hm.group(1))
            out.append(f"<h{lvl}>{_esc(hm.group(2))}</h{lvl}>")
            continue

        # Horizontal rule
        if re.match(r"^-{3,}\s*$", stripped):
            out.append("<hr>")
            continue

        # Preserve page anchors (e.g. <a id="page-1"></a>) before escaping
        anchors = _PAGE_ANCHOR_RE.findall(line)
        p = _PAGE_ANCHOR_RE.sub("\x00ANCHOR\x00", line)

        # Regular paragraph — apply inline formatting
        p = _esc(p)
        p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"\*(.+?)\*", r"<em>\1</em>", p)
        p = re.sub(r"`(.+?)`", r"<code>\1</code>", p)

        # Restore preserved anchors
        for anchor in anchors:
            p = p.replace("\x00ANCHOR\x00", anchor, 1)

        if stripped:
            out.append(f"<p>{p}</p>")

    if in_table:
        out.append("</tbody></table>" if _thead_closed else "</thead></table>")
    if in_code:
        out.append("</code></pre>")

    return "\n".join(out)


def _strip_markdown(text: str) -> str:
    """Remove Markdown formatting, leaving readable plain text."""
    s = text
    # Remove images (base64 and file references) → [image] placeholder
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", "[image]", s)
    # Remove links, keep visible text
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    # Remove bold / italic markers
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    s = re.sub(r"__(.+?)__", r"\1", s)
    s = re.sub(r"_(.+?)_", r"\1", s)
    # Remove inline code backticks
    s = re.sub(r"`(.+?)`", r"\1", s)
    # Remove heading markers
    s = re.sub(r"^#{1,6}\s+", "", s, flags=re.MULTILINE)
    # Remove HTML tags
    s = re.sub(r"<[^>]+>", "", s)
    # Collapse horizontal rules
    s = re.sub(r"^-{3,}\s*$", "---", s, flags=re.MULTILINE)
    # Clean up table pipes → aligned text
    cleaned: list[str] = []
    for line in s.split("\n"):
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(c.replace("-", "").replace(":", "").strip() == "" for c in cells):
                continue  # skip separator row
            cleaned.append("  |  ".join(cells))
        else:
            cleaned.append(line)
    return "\n".join(cleaned)
