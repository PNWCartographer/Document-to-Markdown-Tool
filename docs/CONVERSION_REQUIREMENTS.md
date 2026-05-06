# Conversion Requirements

## Primary Conversion Goal
The tool must convert source documents into organized Markdown while preserving the source structure as much as practical.

The purpose is not basic text dumping. The purpose is structured Markdown conversion for human review, AI upload, memory systems, and knowledgebase repositories.

## Required Structure Preservation
The Markdown output should attempt to preserve:
- Heading hierarchy
- Paragraph order
- List structure
- Table structure
- Matrix structure
- Image placement
- Electrical drawing references
- Captions
- Page context
- Embedded content location
- Source file traceability

## Asset Handling
Images, diagrams, drawings, and other extracted assets should be saved in an `assets/` folder near the Markdown output.

Markdown should link to extracted assets using relative paths.

Example:

```markdown
![Extracted diagram](assets/page_03_diagram_01.png)
```

## Tables and Matrices
Tables should be converted into Markdown tables when reliable.

If the table is too complex for clean Markdown, the tool should use a stop gap approach, such as:
- Preserve as image and include extracted text below it
- Convert to HTML table inside Markdown
- Ask user which option they prefer
- Flag the table for manual review

## Electrical Drawings With Text
Electrical drawings should be preserved as images whenever the visual layout is important. OCR text may be extracted and placed near the image, but the image should remain available because the diagram itself carries meaning.

Recommended output:

```markdown
## Electrical Drawing, Page 4

![Electrical drawing](assets/page_04_drawing_01.png)

### Extracted Text From Drawing
Detected text goes here.

Confidence: Medium
Manual review recommended.
```

## OCR Behavior
OCR should be used for:
- Scanned PDFs
- Images with text
- Drawings with text
- Embedded images where text extraction is needed

OCR confidence should be captured when available.

## File Type Routing
The tool should detect file type and route conversion through the best local method available.

Possible routing model:
- PDFs: document layout engine, PDF Markdown engine, OCR fallback
- DOCX and Word files: document parser or conversion engine
- Excel and CSV files: spreadsheet parser and Markdown table builder
- Images: OCR and asset preservation
- Datasets: structured text or table export depending on format

## Edge Case Stop Gaps
When conversion quality is uncertain, the tool should not hide the issue. It should flag the issue and offer clear options when possible.

Examples:
- Keep image only
- Keep image and extracted text
- Convert table to Markdown
- Convert table to HTML
- Mark section for manual review
- Skip unsupported object and log it

## Page Number Preservation

Source documents with page numbers should preserve that information in the Markdown output.

Markdown does not have native page breaks, so page boundaries should be represented using HTML anchors and visible labels inserted at each page transition.

Required format at every page boundary:

```markdown
<a id="page-12"></a>

---
*Page 12*

```

This approach:
- Creates a linkable URL fragment anchor that works in GitHub, Obsidian, VS Code, and AI tools
- Keeps the page number visible in plain text rendering
- Uses a horizontal rule to visually separate page content
- Allows cross-referencing between the Markdown output and the original source document

Page number preservation should be on by default and configurable in Settings.

File types where page markers apply:
- PDF files — use physical page numbers from the source document
- DOCX files — use page count if available, otherwise omit page markers

File types where page markers do not apply:
- Excel files
- CSV files
- Plain image files

## Table of Contents Reconstruction

When a source document includes a table of contents, the tool should extract it and rebuild it as a navigable Markdown section at the top of the output file.

For PDF files, use the document outline extracted by the PDF engine. This provides title, nesting level, and page number for each entry.

Rebuilt TOC format:

```markdown
## Table of Contents

- [Chapter 1 — Introduction](#page-12)
- [Chapter 2 — Background](#page-34)
  - [2.1 Prior Work](#page-38)
- [Chapter 3 — Methods](#page-67)

---
```

TOC links should point to the corresponding page anchor in the document body using the `#page-N` format so the TOC and page markers stay connected.

For DOCX files without a formal TOC, auto-generate one from the heading hierarchy present in the document.

TOC reconstruction should be on by default and configurable in Settings.

When no TOC or heading structure is detected, skip TOC reconstruction silently and note it in the conversion log.

## Output Organization
Recommended output structure:

```text
output/
  source_file_name/
    source_file_name.md
    assets/
    confidence_report.txt
    conversion_log.txt
```
