"""
CSV converter.

Uses pandas for robust parsing (encoding detection, delimiter sniffing,
large file handling) with stdlib csv as a lightweight fallback.

Produces one Markdown table per sheet/file. Multiple CSV files in a batch
are each converted independently by the orchestrator.
"""

import os
from typing import Optional, Callable

from .confidence import ConfidenceResult
from .markdown_writer import ConversionOutput, rows_to_markdown_table
from .logger import ConversionLogger


def convert(
    source_file: str,
    alias: str = "",
    logger: Optional[ConversionLogger] = None,
    progress_callback: Optional[Callable[[float], None]] = None,
) -> ConversionOutput:
    """
    Convert a CSV file to a ConversionOutput.

    Parameters
    ----------
    source_file : str
        Absolute path to the .csv file.
    alias : str
        User-supplied output name override.
    logger : ConversionLogger, optional
    progress_callback : callable, optional
        Called with a float in [0.0, 1.0] as conversion progresses.
    """
    output = ConversionOutput(source_file=source_file, alias=alias)
    confidence = ConfidenceResult(source_file=source_file)
    output.confidence = confidence
    output.engine_used = "pandas"

    def log_info(msg):
        if logger:
            logger.info(msg)

    def log_warn(msg):
        if logger:
            logger.warning(msg)
        confidence.add_warning(msg)

    def progress(p: float):
        if progress_callback:
            progress_callback(p)

    log_info(f"CSV converter started | file={os.path.basename(source_file)}")
    progress(0.1)

    try:
        import pandas as pd
    except ImportError:
        return _fallback_stdlib(source_file, alias, logger, progress_callback, confidence, output)

    # ------------------------------------------------------------------
    # Load with pandas — sniff delimiter and encoding
    # ------------------------------------------------------------------
    df = None
    errors = []

    # Try csv.Sniffer first for fast, accurate delimiter detection
    import csv as _csv
    _sniffed_sep = None
    try:
        with open(source_file, newline="", encoding="utf-8", errors="replace") as _fh:
            sample = _fh.read(8192)
        dialect = _csv.Sniffer().sniff(sample)
        _sniffed_sep = dialect.delimiter
        log_info(f"csv.Sniffer detected delimiter: {repr(_sniffed_sep)}")
    except Exception:
        pass

    # Build delimiter list: sniffed first (if found), then the usual suspects
    _delimiters = [_sniffed_sep] if _sniffed_sep else []
    for _s in (",", ";", "\t", "|"):
        if _s not in _delimiters:
            _delimiters.append(_s)

    for sep in _delimiters:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                df = pd.read_csv(
                    source_file,
                    sep=sep,
                    encoding=enc,
                    dtype=str,
                    keep_default_na=False,
                )
                if df.shape[1] >= 1:
                    log_info(f"Loaded CSV | sep={repr(sep)} encoding={enc} "
                             f"rows={len(df)} cols={df.shape[1]}")
                    break
                df = None
            except Exception as e:
                errors.append(str(e))
        if df is not None:
            break

    if df is None:
        # Last attempt: let pandas engine auto-detect
        try:
            df = pd.read_csv(source_file, dtype=str, keep_default_na=False, engine="python")
            log_info(f"Loaded CSV via python engine | rows={len(df)} cols={df.shape[1]}")
        except Exception as e:
            errors.append(str(e))
            last_err = errors[-1] if errors else "unknown error"
            log_warn(f"pandas could not parse CSV: {last_err}")
            return _fallback_stdlib(source_file, alias, logger, progress_callback, confidence, output)

    progress(0.5)

    headers = list(df.columns)
    rows = [list(row) for row in df.itertuples(index=False, name=None)]

    if not rows:
        log_warn("CSV file has headers but no data rows.")
        confidence.add_note("File contained no data rows.")

    stem = alias if alias else os.path.splitext(os.path.basename(source_file))[0]
    table_md = rows_to_markdown_table(headers, rows)
    heading = f"## {stem}"
    meta = (
        f"*Source: `{os.path.basename(source_file)}`  "
        f"Rows: {len(rows)}  Columns: {len(headers)}*"
    )
    body = f"{meta}\n\n{table_md}"
    output.add_section(body=body, heading=heading)

    _set_confidence(confidence, rows, headers)
    confidence.derive_overall()
    progress(1.0)
    log_info(f"CSV conversion complete | rows={len(rows)} cols={len(headers)}")
    return output


# ---------------------------------------------------------------------------
# Stdlib fallback
# ---------------------------------------------------------------------------

def _fallback_stdlib(
    source_file, alias, logger, progress_callback, confidence, output
) -> ConversionOutput:
    import csv

    if logger:
        logger.info("Falling back to stdlib csv parser.")
    output.engine_used = "stdlib_csv"

    try:
        with open(source_file, newline="", encoding="utf-8", errors="replace") as fh:
            reader = csv.reader(fh)
            all_rows = list(reader)
    except Exception as e:
        if logger:
            logger.error(f"stdlib csv failed: {e}")
        confidence.text_extraction = "Failed"
        confidence.overall = "Failed"
        return output

    if not all_rows:
        confidence.text_extraction = "Low"
        confidence.add_warning("CSV file appears empty.")
        confidence.derive_overall()
        return output

    headers = all_rows[0]
    rows = all_rows[1:]
    stem = alias if alias else os.path.splitext(os.path.basename(source_file))[0]
    table_md = rows_to_markdown_table(headers, rows)
    output.add_section(body=table_md, heading=f"## {stem}")
    _set_confidence(confidence, rows, headers)
    confidence.derive_overall()

    if progress_callback:
        progress_callback(1.0)
    return output


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def _set_confidence(
    confidence: ConfidenceResult,
    rows: list,
    headers: list,
) -> None:
    confidence.image_extraction = "N/A"
    confidence.image_placement = "N/A"
    confidence.ocr_confidence = "N/A"

    if not rows:
        confidence.text_extraction = "Low"
        confidence.table_structure = "Low"
        confidence.document_order = "N/A"
        return

    # Check for ragged rows (inconsistent column count)
    expected = len(headers)
    ragged = sum(1 for r in rows if len(r) != expected)
    if ragged > 0:
        pct = ragged / len(rows)
        if pct > 0.2:
            confidence.table_structure = "Low"
            confidence.add_warning(f"{ragged} of {len(rows)} rows have inconsistent column count.")
        else:
            confidence.table_structure = "Medium"
            confidence.add_note(f"{ragged} rows had inconsistent column count (minor).")
    else:
        confidence.table_structure = "High"

    confidence.text_extraction = "High"
    confidence.document_order = "High"
