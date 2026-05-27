"""
RTF (Rich Text Format) converter.

Converts .rtf files to Markdown by stripping RTF control words and
extracting the plain-text content, then structuring it as Markdown
with heading detection and paragraph formatting.

Uses striprtf if available for accurate RTF parsing, otherwise falls
back to a regex-based RTF control-word stripper.

Cross-platform: Windows, Linux, macOS.
"""

import os
import re
from typing import Callable, Optional

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput


def convert(
    source_file: str,
    *,
    alias: str = "",
    logger=None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> ConversionOutput:
    """
    Convert an RTF file to Markdown.

    Parameters
    ----------
    source_file : str
        Path to the .rtf file.
    alias : str
        Optional output name override.
    logger : ConversionLogger, optional
        Per-file logger instance.
    progress_callback : callable, optional
        Reports progress as a float 0.0–1.0.

    Returns
    -------
    ConversionOutput
        Populated with sections, confidence, and metadata.
    """

    def progress(p: float):
        if progress_callback:
            progress_callback(p)

    def log_info(msg: str):
        if logger:
            logger.info(msg)

    def log_warn(msg: str):
        if logger:
            logger.warning(msg)

    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence

    progress(0.1)

    # ------------------------------------------------------------------
    # 1. Read the RTF file
    # ------------------------------------------------------------------
    try:
        with open(source_file, "rb") as fh:
            raw_bytes = fh.read()
    except Exception as e:
        log_warn(f"Failed to read RTF file: {e}")
        confidence.overall = "Failed"
        confidence.text_extraction = "Failed"
        confidence.add_warning(f"Could not read file: {e}")
        return output

    progress(0.2)

    # ------------------------------------------------------------------
    # 2. Extract plain text from RTF
    # ------------------------------------------------------------------
    text = ""
    engine_used = ""

    # Try striprtf first (best quality)
    try:
        from striprtf.striprtf import rtf_to_text
        text = rtf_to_text(raw_bytes.decode("utf-8", errors="replace"))
        engine_used = "striprtf"
        log_info("RTF parsed with striprtf")
    except ImportError:
        log_info("striprtf not available — using regex fallback")
    except Exception as e:
        log_warn(f"striprtf failed: {e} — trying regex fallback")

    # Regex fallback: strip RTF control words
    if not text.strip():
        try:
            text = _rtf_to_text_fallback(raw_bytes.decode("utf-8", errors="replace"))
            engine_used = "regex-fallback"
            log_info("RTF parsed with regex fallback")
        except Exception as e:
            log_warn(f"RTF regex fallback failed: {e}")
            confidence.overall = "Failed"
            confidence.text_extraction = "Failed"
            confidence.add_warning(f"All RTF parsing methods failed: {e}")
            return output

    progress(0.5)
    output.engine_used = engine_used

    if not text.strip():
        log_warn("RTF file produced no text content")
        confidence.text_extraction = "Low"
        confidence.add_warning("No text content extracted from RTF file")
        confidence.derive_overall()
        return output

    # ------------------------------------------------------------------
    # 3. Structure as Markdown
    # ------------------------------------------------------------------
    sections = _structure_text(text)
    progress(0.7)

    stem = alias if alias else os.path.splitext(os.path.basename(source_file))[0]

    # Build TOC from detected headings
    for section in sections:
        heading = section["heading"]
        body = section["body"]
        output.add_section(heading=heading, body=body)
        if heading:
            level = heading.count("#", 0, heading.index(" ")) if " " in heading else 1
            title = heading.lstrip("# ").strip()
            output.add_toc_entry(level, title)

    progress(0.85)

    # ------------------------------------------------------------------
    # 4. Confidence scoring
    # ------------------------------------------------------------------
    word_count = len(text.split())
    has_structure = any(s["heading"] for s in sections)

    confidence.text_extraction = "High" if word_count > 20 else "Medium"
    confidence.table_structure = "N/A"
    confidence.image_extraction = "N/A"
    confidence.image_placement = "N/A"
    confidence.document_order = "High" if has_structure else "Medium"
    confidence.ocr_confidence = "N/A"

    if engine_used == "regex-fallback":
        confidence.text_extraction = "Medium"
        confidence.add_note("Used regex fallback — some formatting may be lost")

    if not has_structure:
        confidence.add_note("No heading structure detected in RTF document")

    confidence.add_note(f"Engine: {engine_used} | Words: {word_count}")
    confidence.derive_overall()

    log_info(f"RTF conversion complete | engine={engine_used} "
             f"words={word_count} sections={len(sections)} "
             f"confidence={confidence.overall}")
    progress(1.0)
    return output


# ---------------------------------------------------------------------------
# RTF text extraction fallback
# ---------------------------------------------------------------------------

def _rtf_to_text_fallback(rtf: str) -> str:
    """
    Basic RTF-to-text using regex to strip control words.
    Handles the most common RTF constructs but may miss complex formatting.
    """
    # Remove RTF header/font table/color table blocks
    text = re.sub(r'\{\\fonttbl[^}]*\}', '', rtf)
    text = re.sub(r'\{\\colortbl[^}]*\}', '', rtf)
    text = re.sub(r'\{\\stylesheet[^}]*\}', '', rtf)
    text = re.sub(r'\{\\info[^}]*\}', '', rtf)

    # Remove pictures and objects
    text = re.sub(r'\{\\pict[^}]*\}', '', text)
    text = re.sub(r'\{\\object[^}]*\}', '', text)

    # Handle special characters
    text = text.replace(r'\par', '\n')
    text = text.replace(r'\tab', '\t')
    text = text.replace(r'\line', '\n')
    text = text.replace(r'\page', '\n\n---\n\n')

    # Handle Unicode escapes: \uN? where N is a decimal code point
    def _unicode_replace(m):
        try:
            return chr(int(m.group(1)))
        except (ValueError, OverflowError):
            return ''
    text = re.sub(r"\\u(-?\d+)\??", _unicode_replace, text)

    # Handle hex escapes: \'XX
    def _hex_replace(m):
        try:
            return chr(int(m.group(1), 16))
        except (ValueError, OverflowError):
            return ''
    text = re.sub(r"\\'([0-9a-fA-F]{2})", _hex_replace, text)

    # Strip remaining RTF control words (e.g., \b, \i, \fs24)
    text = re.sub(r'\\[a-z]{1,32}-?\d*\s?', '', text)

    # Remove remaining braces
    text = text.replace('{', '').replace('}', '')

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


# ---------------------------------------------------------------------------
# Text structuring
# ---------------------------------------------------------------------------

def _structure_text(text: str) -> list[dict]:
    """
    Analyze plain text from RTF and detect headings and paragraphs.

    Heuristics for heading detection:
    - Short lines (< 80 chars) followed by a blank line
    - Lines that are ALL CAPS and short
    - Lines that look like numbered sections (e.g., "1. Introduction")
    """
    lines = text.split('\n')
    sections: list[dict] = []
    current_heading = ""
    current_body_lines: list[str] = []

    def _flush():
        nonlocal current_heading, current_body_lines
        body = '\n'.join(current_body_lines).strip()
        if current_heading or body:
            sections.append({"heading": current_heading, "body": body})
        current_heading = ""
        current_body_lines = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines — they separate paragraphs
        if not stripped:
            if current_body_lines:
                current_body_lines.append("")
            i += 1
            continue

        # Detect heading patterns
        is_heading = False

        # Pattern 1: ALL CAPS, short, followed by blank or EOF
        if (stripped.isupper() and len(stripped) < 80 and len(stripped) > 2
                and not stripped.startswith(('|', '-', '=', '*'))):
            next_blank = (i + 1 >= len(lines) or not lines[i + 1].strip())
            if next_blank:
                is_heading = True

        # Pattern 2: Numbered section header (e.g., "1. Introduction", "1.1 Overview")
        if not is_heading and re.match(r'^\d+(\.\d+)*\.?\s+[A-Z]', stripped):
            if len(stripped) < 80:
                next_blank = (i + 1 >= len(lines) or not lines[i + 1].strip())
                if next_blank:
                    is_heading = True

        if is_heading:
            _flush()
            # Determine heading level
            numbered = re.match(r'^(\d+(?:\.\d+)*)', stripped)
            if numbered:
                depth = numbered.group(1).count('.') + 1
                level = min(depth + 1, 6)  # ## for "1.", ### for "1.1", etc.
            else:
                level = 2  # Default ALL-CAPS headings to H2
            current_heading = f"{'#' * level} {stripped.title() if stripped.isupper() else stripped}"
            i += 1
            continue

        # Regular text line
        current_body_lines.append(stripped)
        i += 1

    _flush()

    # If no headings detected, wrap everything in a single section
    if len(sections) == 1 and not sections[0]["heading"]:
        return sections

    return sections
