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
- Searchable PDF creation (adding invisible text layer)

OCR confidence should be captured when available.

### OCR Engine Routing
The tool uses platform-aware OCR engine selection:

| Platform | Primary Engine | Secondary | Fallback |
|----------|---------------|-----------|----------|
| Windows | RapidOCR (CUDA or DirectML) | Tesseract | CPU-only RapidOCR |
| Linux | RapidOCR (CUDA) | Tesseract | CPU-only RapidOCR |
| macOS | Apple Vision (Neural Engine) | RapidOCR (CoreML) | Tesseract |

### Ensemble OCR Mode
When OCR Engine is set to "Ensemble":
1. Run RapidOCR on the page — get word-level bounding boxes and confidence scores
2. Run Tesseract on the same page — get word-level bounding boxes and confidence scores
3. Align words spatially using intersection-over-union matching on bounding boxes
4. For each aligned word pair, keep the result with the higher confidence score
5. Reconstruct lines from the winning words
6. Report engine as "ensemble (rapidocr+tesseract)"

Ensemble mode reduces OCR errors by 30-50% compared to a single engine, at the cost of roughly double the processing time.

## File Type Routing
The tool should detect file type and route conversion through the best local method available.

Routing model:
- PDFs: docling (AI layout) → pymupdf4llm → pymupdf+OCR fallback
- DOCX and Word files: docling → mammoth → python-docx fallback
- Excel and CSV files: openpyxl/xlrd → pandas table builder
- PowerPoint: python-pptx (slides, tables, images, speaker notes)
- EPUB: ebooklib + BeautifulSoup (chapters, images, TOC)
- HTML: markdownify → BeautifulSoup fallback
- DXF: ezdxf (layers, text, dimensions, SVG preview)
- Images: RapidOCR with Tesseract fallback (OpenCV preprocessing pipeline)
- Searchable PDF output: ocrmypdf with custom RapidOCR plugin

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

## PowerPoint (PPTX) Conversion Rules

PowerPoint files are converted slide by slide using python-pptx.

### Slide Order
- Slides are processed in presentation order (slide 1, slide 2, etc.)
- Each slide becomes a section headed with `## Slide N: Title`

### Shape Reading Order
- Shapes within a slide are sorted by position: top-to-bottom first, then left-to-right
- This produces a natural reading order even for complex slide layouts

### Slide Content Mapping
- Slide title shape text becomes the section heading
- Text frames and text boxes become body paragraphs
- Bold, italic, and combined formatting are preserved as Markdown inline syntax
- Tables within slides are converted to Markdown table syntax
- Images are extracted to the assets folder and linked in Markdown
- Speaker notes are included as blockquotes at the end of each slide section
- SmartArt and grouped shapes have text extracted on a best-effort basis

### PPTX Limitations
- Animations and transitions are not represented in output
- Chart data is not extracted (charts appear as images if image preservation is on)
- Audio and video embeds are noted but not extracted

## EPUB Conversion Rules

EPUB e-books are converted chapter by chapter using ebooklib and BeautifulSoup.

### Reading Order
- Chapters are processed in spine order (the reading sequence defined by the EPUB)
- Each chapter or document item becomes a DocumentSection

### HTML to Markdown Element Mapping
| HTML Element | Markdown Output |
|-------------|-----------------|
| `<h1>` through `<h6>` | `#` through `######` headings |
| `<p>` | Paragraphs |
| `<ul>`, `<ol>` | Unordered and ordered lists (nested lists supported) |
| `<table>` | Markdown tables |
| `<img>` | Image extracted from EPUB archive, saved to assets, linked in Markdown |
| `<blockquote>` | `>` blockquotes |
| `<code>`, `<pre>` | Inline code or fenced code blocks |
| `<strong>`, `<b>` | `**bold**` |
| `<em>`, `<i>` | `*italic*` |
| `<a>` | `[text](url)` links |

### TOC Extraction
- Table of contents is extracted from the EPUB NCX or nav document when available
- Nested TOC entries preserve their hierarchy
- When no formal TOC exists, headings from chapter content are used

### Image Extraction
- Images embedded in the EPUB archive are extracted and saved to the assets folder
- Image references in Markdown use relative paths to the assets folder
- Supported image formats: PNG, JPEG, GIF, SVG (SVG saved as-is)

## Post-Processor Pipeline

Post-processors run between raw text extraction and output assembly. They clean and enhance the extracted text before it becomes the final output.

### Processing Order
Processors run in this fixed sequence to avoid conflicts:

1. **Remove headers and footers** — Scans all pages for repeated text at the top and bottom. Lines appearing on 60% or more of pages (minimum 3) are classified as headers or footers and removed.

2. **Skip blank pages** — Removes pages with fewer than 10 non-whitespace characters. Catches empty separator pages and blank backs of double-sided scans.

3. **Strip line numbers** — Detects and removes sequential line numbers in the left margin. Only strips when numbers form a sequential ascending pattern with at least 5 numbers to avoid removing real content.

4. **Detect code blocks** — Identifies source code by indentation patterns, high symbol density, and common code keywords. Wraps detected code in fenced code blocks with language hints when possible.

5. **Detect footnotes** — Finds footnote references and definitions. Converts numbered footnotes to Markdown `[^N]` reference and `[^N]: text` definition syntax.

6. **Detect equations** — Identifies mathematical expressions by Greek letters, math operators, and formula patterns. Wraps inline math in `$...$` and display math in `$$...$$` LaTeX delimiters. Skips content inside code blocks.

### Pipeline Behavior
- Each processor can be toggled on or off independently via Settings
- Processors that operate on pages (headers/footers, blank pages) split text at page markers and reassemble after processing
- Processors that operate on full text (code blocks, footnotes, equations) run on the assembled Markdown
- The pipeline is skipped entirely when all toggles are off (no performance cost)

### Converter Integration
- **PDF (docling path):** Text is split on `<a id="page-N">` markers for page-level processors, then rejoined
- **PDF (pymupdf path):** Page texts are collected during extraction, then processed as a batch
- **DOCX:** All processors run on the assembled monolithic text (DOCX has no natural page boundaries for header/footer detection in most cases)
- **PPTX and EPUB:** Post-processors are not applied (content structure differs from paginated documents)

## RAG Chunks Output Format

The RAG Chunks format produces JSONL (JSON Lines) output designed for ingestion into vector databases and AI retrieval pipelines.

### Chunking Strategy
1. Split the document by sections first (natural document boundaries from headings)
2. Within sections, split by word count if the section exceeds the chunk size
3. Apply overlap: include the last N words from the previous chunk at the start of each new chunk
4. Preserve heading context: each chunk records its parent heading

### Default Parameters
- Chunk size: 512 words
- Chunk overlap: 50 words

### Chunk Schema
Each line in the JSONL output is a self-contained JSON object:

```json
{
    "id": "filename_chunk_001",
    "text": "chunk content here...",
    "metadata": {
        "source": "original_filename.pdf",
        "section": "Section 2.1 — Methods",
        "chunk_index": 0,
        "total_chunks": 42,
        "confidence": "High"
    }
}
```

### RAG Chunks Behavior
- Page numbers are included in chunk metadata when page number preservation is enabled
- TOC entries are included as a special first chunk when TOC reconstruction is enabled
- Confidence data is included per-chunk when confidence reporting is enabled
- Empty chunks (all whitespace) are excluded from output

## Searchable PDF Conversion Rules

Searchable PDF output uses ocrmypdf to add an invisible OCR text layer to PDF files.

### Processing Pipeline
1. Input PDF is analyzed to detect which pages already contain text
2. Pages without text are processed through OCR (unless Force OCR is enabled, which re-OCRs all pages)
3. Deskew correction is applied when enabled (straightens tilted scans)
4. Page cleaning removes speckles and noise when enabled
5. Background removal strips colored backgrounds when enabled (OpenCV preprocessing)
6. OCR engine produces text and bounding box data
7. Invisible text layer is composited onto each page at the correct positions
8. Output is optimized according to the selected level
9. PDF/A conversion is applied when enabled
10. Sidecar text file is written alongside the PDF when enabled

### ocrmypdf Integration
- Uses the `ocrmypdf.ocr()` Python API directly (not a subprocess call)
- Custom plugin (`ocrmypdf_rapidocr.py`) routes OCR through RapidOCR with GPU acceleration
- On macOS, an Apple Vision plugin is used when available
- Not thread-safe — requires multiprocessing isolation on Windows and macOS
- Returns structured result data: pages processed, pages skipped, confidence data

### Auto-Chunking
Documents exceeding 30 pages are automatically split into chunks for parallel processing:
- Chunk size: 20-30 pages, determined by available RAM
- Worker count: `min(cpu_cores - 1, int((ram_gb - 2) / 1.5))`, clamped to 1-8
- Uses `ProcessPoolExecutor` for chunk-level parallelism
- Chunks are reassembled into a single output PDF after processing
- Progress callback reports per-chunk status to the conversion progress bar

### Sidecar and RAG Output
When sidecar text is enabled:
- Primary output: `document.pdf` (searchable)
- Sidecar: `document_sidecar.txt` (extracted OCR text, plain UTF-8)
- Optional: `document_rag.jsonl` (RAG chunks generated from sidecar text)

The sidecar text preserves page boundaries with markers. RAG chunks follow the same schema as the standard RAG Chunks output format.

### Background Removal
When enabled, a preprocessing pipeline runs before OCR:
1. Convert page image to grayscale
2. Apply adaptive threshold to separate foreground from background
3. Morphological cleaning to remove noise
4. Generate background mask
5. Replace background with white

This is an aggressive operation. The tooltip warns users that it may affect document appearance and should only be used for scanned documents with colored paper or heavy noise.

### Searchable PDF Output Structure
```text
output/
  document_name/
    document_name.pdf              # Searchable PDF with OCR text layer
    document_name_sidecar.txt      # Plain text OCR output (optional)
    document_name_rag.jsonl         # RAG chunks from sidecar (optional)
    confidence_report.txt           # Per-file confidence scores
    conversion_log.txt              # Detailed conversion log
```

## Quality Preset Behavior

Quality presets control the tradeoff between conversion speed and output accuracy.

### Fast
- Overrides conversion mode to Standard (no OCR processing)
- Skips docling AI-powered layout analysis
- Uses the fastest available text extraction method
- For Searchable PDF: uses lowest optimization level, skips deskew and cleaning
- Best for: large batches of digital-native documents where speed matters more than formatting

### Balanced
- Uses standard conversion with limited fallbacks
- Logs when fallback engines are needed but does not skip them
- For Searchable PDF: applies deskew, standard optimization
- Best for: general-purpose conversion with reasonable speed

### Quality
- Full pipeline with all engines enabled (current default behavior)
- OCR fallback is available when needed
- Advanced table detection with pdfplumber and camelot
- AI-powered layout analysis via docling
- For Searchable PDF: applies deskew, cleaning, highest optimization
- Best for: documents where accuracy and structure preservation are critical
