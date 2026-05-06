"""
Confidence scoring and report generation.

Each converter produces a ConfidenceResult. The orchestrator collects
results per file and writes confidence_report.txt to the output folder.

Levels (plain language, per spec):
    High | Medium | Low | Failed | N/A
"""

import os
from dataclasses import dataclass, field
from typing import Optional


LEVELS = ("High", "Medium", "Low", "Failed", "N/A")


@dataclass
class ConfidenceResult:
    """Confidence scores for one converted file."""

    source_file: str = ""

    overall: str = "N/A"
    text_extraction: str = "N/A"
    table_structure: str = "N/A"
    image_extraction: str = "N/A"
    image_placement: str = "N/A"
    document_order: str = "N/A"
    ocr_confidence: str = "N/A"          # "N/A" when OCR was not used

    manual_review_recommended: bool = False
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_note(self, note: str) -> None:
        self.notes.append(note)

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)
        self.manual_review_recommended = True

    def derive_overall(self) -> None:
        """
        Compute overall from the worst individual score.
        Call this after all per-area scores have been set.
        """
        priority = {"Failed": 0, "Low": 1, "Medium": 2, "High": 3, "N/A": 4}
        scored = [
            s for s in (
                self.text_extraction,
                self.table_structure,
                self.image_extraction,
                self.image_placement,
                self.document_order,
                self.ocr_confidence,
            )
            if s != "N/A"
        ]
        if not scored:
            self.overall = "N/A"
            return
        worst = min(scored, key=lambda s: priority.get(s, 4))
        self.overall = worst

    def to_report_text(self) -> str:
        """Return the plain-text content for confidence_report.txt."""
        lines = [
            "Conversion Confidence Report",
            "",
            f"Source file: {os.path.basename(self.source_file)}",
            f"Overall confidence: {self.overall}",
            "",
            f"Text extraction:    {self.text_extraction}",
            f"Table structure:    {self.table_structure}",
            f"Image extraction:   {self.image_extraction}",
            f"Image placement:    {self.image_placement}",
            f"Document order:     {self.document_order}",
        ]
        if self.ocr_confidence != "N/A":
            lines.append(f"OCR confidence:     {self.ocr_confidence}")

        lines += [
            "",
            f"Manual review recommended: {'Yes' if self.manual_review_recommended else 'No'}",
        ]

        if self.notes:
            lines += ["", "Notes:"]
            for n in self.notes:
                lines.append(f"  - {n}")

        if self.warnings:
            lines += ["", "Warnings:"]
            for w in self.warnings:
                lines.append(f"  - {w}")

        return "\n".join(lines)

    def to_markdown_summary(self) -> str:
        """One-line blockquote for embedding at the top of the .md output."""
        review = " Manual review recommended." if self.manual_review_recommended else ""
        return f"> Conversion confidence: {self.overall}.{review}"


def write_confidence_report(result: ConfidenceResult, output_dir: str) -> str:
    """
    Write confidence_report.txt to output_dir.
    Returns the path written.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "confidence_report.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(result.to_report_text())
    return path


def aggregate_confidence(results: list[ConfidenceResult]) -> ConfidenceResult:
    """
    Combine per-file results into a single batch-level summary.
    Used when converting multiple files to populate the Results screen.
    """
    if not results:
        return ConfidenceResult(source_file="(batch)")

    priority = {"Failed": 0, "Low": 1, "Medium": 2, "High": 3, "N/A": 4}

    def worst(values: list[str]) -> str:
        scored = [v for v in values if v != "N/A"]
        if not scored:
            return "N/A"
        return min(scored, key=lambda s: priority.get(s, 4))

    batch = ConfidenceResult(source_file="(batch)")
    batch.overall = worst([r.overall for r in results])
    batch.text_extraction = worst([r.text_extraction for r in results])
    batch.table_structure = worst([r.table_structure for r in results])
    batch.image_extraction = worst([r.image_extraction for r in results])
    batch.image_placement = worst([r.image_placement for r in results])
    batch.document_order = worst([r.document_order for r in results])
    batch.ocr_confidence = worst([r.ocr_confidence for r in results])
    batch.manual_review_recommended = any(r.manual_review_recommended for r in results)
    for r in results:
        batch.warnings.extend(r.warnings)
    return batch
