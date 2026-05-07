"""
Markdown assembly and output file writer.

Responsible for:
  - Building the final .md string from converter-supplied sections
  - Injecting the confidence summary blockquote (when enabled)
  - Writing the .md file to disk
  - Determining the correct output path for a given source file

Output structure per file (matches CONVERSION_REQUIREMENTS.md):
    <output_root>/
        <stem>/
            <stem>.md
            assets/
            confidence_report.txt
            conversion_log.txt
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from .confidence import ConfidenceResult


@dataclass
class DocumentSection:
    """
    A single logical section of the converted document.

    heading      : Markdown heading string, e.g. "## Chapter 1" (or "" for body)
    body         : Markdown body text
    page_number  : source page this section came from (None if not applicable)
    """
    heading: str = ""
    body: str = ""
    page_number: Optional[int] = None


@dataclass
class ConversionOutput:
    """
    Everything a converter produces for one source file.
    The markdown_writer assembles this into the final .md.
    """
    source_file: str = ""
    alias: str = ""                          # user-supplied output name override
    sections: list[DocumentSection] = field(default_factory=list)
    toc_entries: list[tuple[int, str, Optional[int]]] = field(default_factory=list)
    # toc_entries: list of (level, title, page_number)
    asset_paths: list[str] = field(default_factory=list)
    confidence: Optional[ConfidenceResult] = None
    warnings: list[str] = field(default_factory=list)
    engine_used: str = ""

    def add_section(
        self,
        body: str,
        heading: str = "",
        page_number: Optional[int] = None,
    ) -> None:
        self.sections.append(DocumentSection(heading=heading, body=body, page_number=page_number))

    def add_toc_entry(self, level: int, title: str, page_number: Optional[int] = None) -> None:
        self.toc_entries.append((level, title, page_number))


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def output_dir_for(
    source_file: str,
    output_root: str,
    alias: str = "",
    use_subfolder: bool = True,
) -> str:
    """
    Return the per-file output directory.
    use_subfolder=True  → <output_root>/<stem>/
    use_subfolder=False → <output_root>/
    """
    if use_subfolder:
        stem = alias if alias else _safe_stem(source_file)
        return os.path.join(output_root, stem)
    return output_root


def md_path_for(
    source_file: str,
    output_root: str,
    alias: str = "",
    use_subfolder: bool = True,
) -> str:
    """Return the full path for the .md output file."""
    stem = alias if alias else _safe_stem(source_file)
    out_dir = output_dir_for(source_file, output_root, alias, use_subfolder)
    return os.path.join(out_dir, stem + ".md")


def assets_dir_for(
    source_file: str,
    output_root: str,
    alias: str = "",
    use_subfolder: bool = True,
) -> str:
    """
    Return the assets/ subdirectory path (absolute).
    use_subfolder=True  → <output_root>/<stem>/assets/
    use_subfolder=False → <output_root>/assets/<stem>/   (keeps per-file separation)
    """
    out_dir = output_dir_for(source_file, output_root, alias, use_subfolder)
    if use_subfolder:
        return os.path.join(out_dir, "assets")
    # When all .md files land in output_root directly, give each its own
    # assets sub-folder so images from different files don't collide.
    stem = alias if alias else _safe_stem(source_file)
    return os.path.join(out_dir, "assets", stem)


def assets_rel_prefix_for(
    source_file: str,
    alias: str = "",
    use_subfolder: bool = True,
) -> str:
    """
    Return the relative path prefix used in Markdown image references.
    use_subfolder=True  → "assets/"
    use_subfolder=False → "assets/<stem>/"
    """
    if use_subfolder:
        return "assets/"
    stem = alias if alias else _safe_stem(source_file)
    return f"assets/{stem}/"


# ---------------------------------------------------------------------------
# Markdown assembly
# ---------------------------------------------------------------------------

def build_markdown(
    output: ConversionOutput,
    include_confidence_summary: bool = True,
    include_page_numbers: bool = True,
    rebuild_toc: bool = True,
) -> str:
    """
    Assemble the full Markdown string from a ConversionOutput.
    """
    parts: list[str] = []

    # Confidence summary at top
    if include_confidence_summary and output.confidence:
        parts.append(output.confidence.to_markdown_summary())
        parts.append("")

    # Table of contents
    if rebuild_toc and output.toc_entries:
        parts.append(_build_toc_block(output.toc_entries))
        parts.append("")

    # Body sections
    prev_page: Optional[int] = None
    for section in output.sections:

        # Page anchor when page changes
        if include_page_numbers and section.page_number is not None:
            if section.page_number != prev_page:
                parts.append(_page_anchor(section.page_number))
                prev_page = section.page_number

        if section.heading:
            parts.append(section.heading)

        if section.body:
            parts.append(section.body.strip())

        parts.append("")

    return "\n".join(parts).strip() + "\n"


def write_markdown(
    output: ConversionOutput,
    output_root: str,
    use_subfolder: bool = True,
    include_confidence_summary: bool = True,
    include_page_numbers: bool = True,
    rebuild_toc: bool = True,
    overwrite: bool = False,
) -> str:
    """
    Write the assembled Markdown to disk.
    Returns the path written.
    Raises FileExistsError if file exists and overwrite=False.
    """
    path = md_path_for(output.source_file, output_root, output.alias, use_subfolder)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    os.makedirs(assets_dir_for(output.source_file, output_root, output.alias, use_subfolder), exist_ok=True)

    if not overwrite and os.path.exists(path):
        raise FileExistsError(f"Output file already exists: {path}")

    md = build_markdown(
        output,
        include_confidence_summary=include_confidence_summary,
        include_page_numbers=include_page_numbers,
        rebuild_toc=rebuild_toc,
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md)

    return path


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _page_anchor(page: int) -> str:
    return f'<a id="page-{page}"></a>\n\n---\n*Page {page}*'


def _build_toc_block(entries: list[tuple[int, str, Optional[int]]]) -> str:
    lines = ["## Table of Contents", ""]
    for level, title, page in entries:
        indent = "  " * (level - 1)
        anchor = f"#page-{page}" if page is not None else "#"
        lines.append(f"{indent}- [{title}]({anchor})")
    lines.append("")
    lines.append("---")
    return "\n".join(lines)


def _safe_stem(file_path: str) -> str:
    """Return a filesystem-safe stem from a file path."""
    base = os.path.splitext(os.path.basename(file_path))[0]
    safe = re.sub(r'[<>:"/\\|?*]', "_", base).strip()
    return safe or "output"


# ---------------------------------------------------------------------------
# Table building helpers (used by converters)
# ---------------------------------------------------------------------------

def rows_to_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """
    Convert a list of header strings and data rows into a Markdown table.
    Cells are coerced to str; pipe characters inside cells are escaped.
    """
    def _cell(v) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")

    col_count = max(len(headers), max((len(r) for r in rows), default=0))
    headers = _pad(headers, col_count)
    header_row = "| " + " | ".join(_cell(h) for h in headers) + " |"
    sep_row = "| " + " | ".join("---" for _ in headers) + " |"
    data_rows = [
        "| " + " | ".join(_cell(c) for c in _pad(row, col_count)) + " |"
        for row in rows
    ]
    return "\n".join([header_row, sep_row] + data_rows)


def _pad(lst: list, length: int) -> list:
    return list(lst) + [""] * max(0, length - len(lst))
