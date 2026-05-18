# Documentation to Markdown Converter Tool

A local desktop utility that converts documents into clean, structured Markdown for human review, AI upload, memory systems, and knowledgebase repositories.

Built with Python and tkinter. All processing happens on your machine — no cloud services, no telemetry, no external APIs.

## Supported File Types

### Input Formats

| Format | Extensions | Engine |
|--------|-----------|--------|
| PDF | `.pdf` | docling (AI layout analysis) with pymupdf4llm and pymupdf+OCR fallbacks |
| Word | `.docx`, `.doc` | docling with mammoth and python-docx fallbacks |
| Excel | `.xlsx`, `.xls` | openpyxl / xlrd with pandas table building |
| CSV | `.csv` | pandas with stdlib csv fallback |
| PowerPoint | `.pptx` | python-pptx (slides, tables, images, speaker notes) |
| EPUB | `.epub` | ebooklib + BeautifulSoup (chapters, images, TOC) |
| DXF | `.dxf` | ezdxf (layers, text, dimensions, title block, SVG preview) |
| Images | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.tif`, `.webp`, `.gif` | PaddleOCR with Tesseract fallback |

### Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Markdown | `.md` | Structured Markdown with headings, tables, image links, TOC |
| JSON | `.json` | Sections, TOC, confidence data as structured JSON |
| HTML | `.html` | Standalone HTML document with styling |
| Plain Text | `.txt` | Clean text without formatting |
| RAG Chunks | `.jsonl` | Chunked JSONL for vector databases and AI retrieval pipelines |

## Features

### Conversion
- Multi-engine pipeline with automatic fallback chains
- OCR support for scanned documents and images (PaddleOCR + Tesseract)
- Auto-detection of file types and best conversion method
- Batch conversion with parallel workers and cancel support
- DXF engineering drawing conversion with SVG preview rendering

### Content Handling
- Image preservation with asset extraction and Markdown links
- Image embedding as base64 data URIs
- Page number preservation with HTML anchors
- Table of contents reconstruction from document headings
- Header and footer removal (auto-detects repeated page text)
- Blank page skipping (removes empty separator pages)
- Line number stripping (for legal and academic documents)
- Code block detection (monospace font and pattern analysis)
- Footnote handling (converts to Markdown footnote syntax)
- Equation detection (preserves math as LaTeX notation)
- Offline translation of non-English OCR text

### Output
- Five output formats: Markdown, JSON, HTML, Plain Text, RAG Chunks
- Markdown flavor selection (GFM, CommonMark, Basic)
- Optional YAML front matter with conversion metadata
- Confidence reporting across six dimensions
- Per-file conversion logging
- Organized subfolder output structure
- Post-processing rules engine with named profiles

### Quality Validation
- Structural summary (heading, table, image, page, word counts)
- Heading hierarchy validation (detects skipped levels)
- Broken link detection
- Missing alt-text flagging
- Flesch-Kincaid readability scoring

### Performance
- Parallel workers (1, 2, 4, or Auto) for batch processing
- Quality presets (Fast, Balanced, Quality) to control speed vs. accuracy
- Fast mode skips OCR and advanced analysis for quick text extraction
- Quality mode enables all engines for maximum accuracy

### Interface
- Darksquare light and dark themes with Windows title bar integration
- Drag-and-drop file input (tkinterdnd2)
- Preview window with syntax-highlighted Markdown output
  - Code blocks, inline code, blockquotes, links, headings, tables, lists
  - Image thumbnails rendered inline
  - Ctrl+F search with live debounced highlighting
  - Copy Markdown to clipboard
- Debug Info window with Export Log
- Watch Folder mode for automated conversion
- Tooltip system for every setting
- Settings persistence across sessions
- Global error handler with visible crash reporting

## Quick Start

### Prerequisites
- Python 3.10 or later
- Windows 10 or Windows 11

### Installation

1. Clone or download this repository.

2. Run the setup script to install dependencies and configure Tesseract:

   ```
   python setup.py
   ```

3. Launch the application:

   ```
   python app/main.py
   ```

The first run may download AI models for docling and PaddleOCR (approximately 1-2 GB). Models are cached locally after download and all processing remains offline.

## Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| Conversion Mode | Auto-detect | How the tool reads documents (Auto-detect, Standard, OCR) |
| Preserve Images | On | Extract and save images from source documents |
| Embed Images | On | Embed images as base64 data URIs in output |
| Preserve Page Numbers | On | Insert page markers at page boundaries |
| Rebuild TOC | On | Generate table of contents from heading structure |
| Remove Headers/Footers | On | Strip repeated page headers and footers |
| Skip Blank Pages | On | Remove pages with little or no content |
| Strip Line Numbers | Off | Remove margin line numbers from legal/academic docs |
| Detect Code Blocks | On | Wrap source code sections in code fences |
| Detect Footnotes | On | Convert footnotes to Markdown footnote syntax |
| Detect Equations | On | Preserve math expressions as LaTeX notation |
| Auto Translate | On | Translate non-English OCR text to English offline |
| DXF SVG Preview | On | Render SVG preview images for DXF drawings |
| OCR Engine | Auto | Preferred OCR engine (Auto, PaddleOCR, Tesseract) |
| Parallel Workers | 1 | Number of files to convert simultaneously (1, 2, 4, Auto) |
| Quality Preset | Quality | Speed vs. accuracy tradeoff (Fast, Balanced, Quality) |
| OCR Language | English | Language for OCR text recognition |
| Markdown Flavor | GFM | Markdown output style (GFM, CommonMark, Basic) |
| YAML Front Matter | Off | Prepend metadata block to output files |
| Output Format | Markdown | Output file format |
| Overwrite Existing | Off | Replace existing output files |
| Output Subfolder | Off | Create per-document subfolders in output |
| Rules Profile | None | Post-processing rules profile to apply |
| Theme | Dark | Interface theme (Dark, Light) |
| Low Confidence Action | Ask me | What to do when conversion confidence is low |

## Output Structure

With subfolder output enabled, each converted document produces:

```
output/
  document_name/
    document_name.md
    assets/
      image_001.png
      image_002.png
    confidence_report.json
    conversion.log
```

## Architecture Overview

```
app/
  main.py               # Entry point: DPI awareness, console hide, crash guard
  gui/
    app.py               # tkinter GUI (Home, Settings, Conversion, Results screens)
    widgets.py           # Custom widgets (PillButton, ToggleSwitch, GlassScrollbar,
                         #   GlassDropdown, PillProgressBar, Tooltip)
    theme.py             # Dark and light theme color definitions
  config/
    settings.py          # Settings persistence, defaults, and load/save
  engine/
    converter.py         # Conversion job orchestration, parallel workers, quality presets
    pdf_converter.py     # PDF conversion (docling -> pymupdf4llm -> pymupdf+OCR)
    docx_converter.py    # DOCX conversion (docling -> mammoth -> python-docx)
    xlsx_converter.py    # Excel conversion (openpyxl -> pandas fallback)
    csv_converter.py     # CSV conversion (pandas -> stdlib csv fallback)
    pptx_converter.py    # PowerPoint conversion
    epub_converter.py    # EPUB e-book conversion
    dxf_converter.py     # DXF engineering drawing conversion (ezdxf + SVG preview)
    image_converter.py   # Image OCR conversion
    ocr_engine.py        # OCR orchestration (PaddleOCR + Tesseract)
    language_tools.py    # Offline translation (argostranslate)
    table_extractor.py   # Advanced table structure extraction
    post_processors.py   # Text cleaning pipeline (headers, code blocks, footnotes, etc.)
    rules_engine.py      # Named post-processing rule profiles
    output_formats.py    # Output format builders (Markdown, JSON, HTML, Text, RAG Chunks)
    markdown_writer.py   # Markdown assembly and asset management
    confidence.py        # Confidence scoring and reporting
    validation.py        # Output quality validation (structure, links, readability)
    logger.py            # Per-file conversion logging and app-level logging
    watch_folder.py      # Watch Folder automated conversion (watchdog)
```

The conversion pipeline flows: **GUI -> ConversionJob -> Engine Converters -> Post-Processors -> Output Writers**.

Post-processors run in a fixed order to avoid conflicts: headers/footers, blank pages, line numbers, code blocks, footnotes, equations.

## Local Processing

This tool processes all files locally on your machine. There are no cloud services, no external APIs, no telemetry, and no remote file uploads. Source documents never leave your computer.

See `docs/LOCAL_PROCESSING_RULES.md` for the full local processing policy.

## Documentation

Detailed specifications are available in the `docs/` folder:

- `docs/PROJECT_SPEC.md` — Project vision and scope
- `docs/FEATURE_REQUIREMENTS.md` — Required features and capabilities
- `docs/GUI_REQUIREMENTS.md` — Interface design and tooltip specifications
- `docs/CONVERSION_REQUIREMENTS.md` — Conversion behavior and output rules
- `docs/CONFIDENCE_REPORTING.md` — Confidence scoring dimensions
- `docs/LOCAL_PROCESSING_RULES.md` — Local-only processing requirements
- `docs/LOGGING_REQUIREMENTS.md` — Logging requirements
- `docs/DEVELOPMENT_WORKFLOW.md` — Build and development workflow

## License

TBD
