"""
PDF table extraction.

Primary:  pdfplumber  — best on ambiguous, borderless, and complex PDF tables.
Fallback: camelot-py  — best on lattice/bordered grid-style tables.

Both engines accept a page reference and return a list of TableResult objects
that converters can incorporate into ConversionOutput sections.

The caller (pdf_converter) decides when to invoke these based on whether
docling already extracted a satisfactory table.
"""

from dataclasses import dataclass, field
from typing import Optional

from .markdown_writer import rows_to_markdown_table, _pad


@dataclass
class TableResult:
    """One extracted table."""
    page_number: Optional[int] = None
    table_index: int = 0
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    confidence: str = "Medium"      # High | Medium | Low
    engine: str = ""
    raw_markdown: str = ""
    warning: str = ""

    def to_markdown(self) -> str:
        if self.raw_markdown:
            return self.raw_markdown
        return rows_to_markdown_table(self.headers, self.rows)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_tables_from_file(
    pdf_path: str,
    pages: Optional[list[int]] = None,
    prefer_engine: str = "pdfplumber",
) -> list[TableResult]:
    """
    Extract all tables from a PDF file.

    Parameters
    ----------
    pdf_path : str
        Absolute path to the PDF.
    pages : list[int], optional
        1-based page numbers to extract from. None = all pages.
    prefer_engine : str
        "pdfplumber" or "camelot"

    Returns
    -------
    list[TableResult]
    """
    if prefer_engine == "pdfplumber" and _pdfplumber_available():
        results = _extract_pdfplumber(pdf_path, pages)
        if results:
            return results
        # Fall through to camelot if pdfplumber found nothing
    if _camelot_available():
        return _extract_camelot(pdf_path, pages)
    if _pdfplumber_available():
        return _extract_pdfplumber(pdf_path, pages)
    return []


def extract_tables_from_page(
    page,                       # pdfplumber page object
    page_number: int,
) -> list[TableResult]:
    """
    Extract tables from a single pdfplumber page object.
    Used by pdf_converter when it already has pages open.
    """
    results = []
    try:
        tables = page.extract_tables()
        for idx, table in enumerate(tables):
            tr = _pdfplumber_table_to_result(table, page_number, idx)
            if tr:
                results.append(tr)
    except Exception:
        pass
    return results


# ---------------------------------------------------------------------------
# pdfplumber
# ---------------------------------------------------------------------------

def _pdfplumber_available() -> bool:
    try:
        import pdfplumber  # noqa: F401
        return True
    except ImportError:
        return False


def _extract_pdfplumber(pdf_path: str, pages: Optional[list[int]]) -> list[TableResult]:
    try:
        import pdfplumber
    except ImportError:
        return []

    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            page_iter = (
                [(i, pdf.pages[i - 1]) for i in pages if 0 < i <= len(pdf.pages)]
                if pages
                else [(i + 1, p) for i, p in enumerate(pdf.pages)]
            )
            for page_num, page in page_iter:
                tables = page.extract_tables()
                for idx, table in enumerate(tables):
                    tr = _pdfplumber_table_to_result(table, page_num, idx)
                    if tr:
                        results.append(tr)
    except Exception:
        pass

    return results


def _pdfplumber_table_to_result(
    table: list[list],
    page_number: int,
    table_index: int,
) -> Optional[TableResult]:
    if not table or len(table) < 2:
        return None

    def clean(v) -> str:
        if v is None:
            return ""
        return str(v).replace("\n", " ").strip()

    all_rows = [[clean(cell) for cell in row] for row in table]
    headers = all_rows[0]
    rows = all_rows[1:]

    # Normalize column count
    col_count = max(len(headers), max((len(r) for r in rows), default=0))
    headers = _pad(headers, col_count)
    rows = [_pad(r, col_count) for r in rows]

    # Confidence: penalize for high blank ratio
    total_cells = sum(len(r) for r in rows)
    blank_cells = sum(1 for r in rows for c in r if not c.strip())
    blank_ratio = blank_cells / total_cells if total_cells > 0 else 1.0
    if blank_ratio > 0.5:
        confidence = "Low"
    elif blank_ratio > 0.2:
        confidence = "Medium"
    else:
        confidence = "High"

    return TableResult(
        page_number=page_number,
        table_index=table_index,
        headers=headers,
        rows=rows,
        confidence=confidence,
        engine="pdfplumber",
    )


# ---------------------------------------------------------------------------
# camelot-py
# ---------------------------------------------------------------------------

def _camelot_available() -> bool:
    try:
        import camelot  # noqa: F401
        return True
    except ImportError:
        return False


def _extract_camelot(pdf_path: str, pages: Optional[list[int]]) -> list[TableResult]:
    try:
        import camelot
    except ImportError:
        return []

    results = []
    page_str = ",".join(str(p) for p in pages) if pages else "all"

    for flavor in ("lattice", "stream"):
        try:
            tables = camelot.read_pdf(pdf_path, pages=page_str, flavor=flavor)
            for t in tables:
                df = t.df
                if df.empty or len(df) < 2:
                    continue

                headers = list(df.iloc[0])
                rows = [list(df.iloc[i]) for i in range(1, len(df))]
                headers = [str(h).replace("\n", " ").strip() for h in headers]
                rows = [[str(c).replace("\n", " ").strip() for c in row] for row in rows]

                col_count = max(len(headers), max((len(r) for r in rows), default=0))
                headers = _pad(headers, col_count)
                rows = [_pad(r, col_count) for r in rows]

                acc = t.parsing_report.get("accuracy", 0)
                if acc >= 85:
                    conf = "High"
                elif acc >= 60:
                    conf = "Medium"
                else:
                    conf = "Low"

                pg = t.parsing_report.get("page", None)
                results.append(TableResult(
                    page_number=pg,
                    table_index=len(results),
                    headers=headers,
                    rows=rows,
                    confidence=conf,
                    engine=f"camelot-{flavor}",
                ))

            if results:
                break

        except Exception:
            continue

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
