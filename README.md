# Doc to Markdown

**by Darksquare**

A professional desktop tool that converts documents into clean, structured Markdown for human review, AI upload, memory systems, and knowledgebase repositories.

Built with Python and tkinter. All processing happens on your machine — no cloud services, no telemetry, no external APIs.

## Supported Formats

### Input Formats

| Format | Extensions | Engine |
|--------|-----------|--------|
| PDF | `.pdf` | docling (AI layout) with pymupdf4llm and pymupdf+OCR fallbacks |
| Word | `.docx`, `.doc` | docling with mammoth and python-docx fallbacks |
| RTF | `.rtf` | striprtf with regex fallback |
| Excel | `.xlsx`, `.xls` | openpyxl / xlrd with pandas table building |
| CSV | `.csv` | pandas with stdlib csv fallback |
| PowerPoint | `.pptx` | python-pptx (slides, tables, images, speaker notes) |
| EPUB | `.epub` | ebooklib + BeautifulSoup (chapters, images, TOC) |
| HTML | `.html`, `.htm` | markdownify with BeautifulSoup fallback |
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

### Conversion Engine
- Multi-engine pipeline with automatic fallback chains for every format
- OCR support for scanned documents and images (PaddleOCR + Tesseract)
- OpenCV preprocessing pipeline (deskew, contrast, denoise, threshold)
- Auto-detection of file types and best conversion method
- Batch conversion with configurable parallel workers and cancel support
- PDF page range selection for converting specific pages instead of full documents
- Quality presets (Fast, Balanced, Quality) to control speed vs. accuracy
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
- Offline language detection and translation for non-English text
- Spell checking with offline dictionary for post-conversion proofreading

### Output
- Five output formats: Markdown, JSON, HTML, Plain Text, RAG Chunks
- Markdown flavor selection (GFM, Obsidian, Pandoc)
- Optional YAML front matter with conversion metadata
- Per-file confidence report (`confidence_report.txt`) in output folder
- Per-file conversion log (`conversion_log.txt`) in output folder
- Organized subfolder output structure with separate assets directory
- Post-processing rules engine with named profiles

### Quality and Validation
- Confidence scoring across six dimensions per file
- Batch-level aggregate confidence with worst-case rollup
- Structural summary (heading, table, image, page, word counts)
- Heading hierarchy validation (detects skipped levels)
- Broken link detection
- Missing alt-text flagging
- Flesch-Kincaid readability scoring
- Confidence heatmap visualization — color-codes preview content by extraction quality

### Performance
- Parallel workers (1, 2, 4, or Auto) for batch processing
- Thread-safe output writing with file locking
- Quality presets: Fast skips OCR, Quality enables all engines
- Lazy model loading (AI models download once, cached locally)

### Interface
- Darksquare dark and light themes with Windows DWM title bar integration
- Cross-platform DPI scaling (Windows, Linux, macOS)
- Drag-and-drop file input (tkinterdnd2 with graceful fallback)
- Five main screens: Home, Settings, Conversion, Results, Watch Folder
- Preview window with rich Markdown rendering and review tools
  - Syntax highlighting for headings, code blocks, inline code, blockquotes, links, tables, lists, horizontal rules, image references, and YAML front matter
  - Inline image thumbnails with click-to-zoom full-size viewer
  - Source pages panel with rendered PDF page thumbnails and image previews
  - Source info panel with file metadata and per-dimension confidence breakdown
  - Find and Replace bar (Ctrl+F) with regex support, match navigation, and Replace All
  - Copy Markdown (raw) or Copy Rich (formatted HTML for Word/Docs/email)
  - Spell check toggle with offline dictionary (misspelled words underlined in red)
  - Confidence heatmap overlay — color-codes text, tables, and images by extraction confidence
- Debug Info window with Export Log (saves full conversion diagnostics to a text file)
- PDF page range selector — visual thumbnail grid with click and Shift+click range selection
- Watch Folder mode for automated batch conversion
- Post-processing Rules Editor with named profiles
- Tooltip system for every setting with detailed descriptions
- Settings persistence across sessions
- About window with license status and quick-start guide
- Global error handler with crash reporting

## Quick Start

### Prerequisites
- Python 3.10 or later
- Windows 10/11, Linux, or macOS

### Installation

1. Clone or download this repository.

2. Run the setup script to install dependencies:

   ```
   python setup.py
   ```

3. Launch the application:

   ```
   python app/main.py
   ```

The first run may download AI models for docling and PaddleOCR (approximately 1-2 GB). Models are cached locally after download and all processing remains offline.

### Basic Usage

1. **Add Files** — Click "Add Files" or drag documents onto the Home screen
2. **Set Output** — Choose an output folder for converted files
3. **Configure** — Adjust settings if needed (defaults work well for most documents)
4. **Convert** — Click "Convert" and monitor progress in the Conversion screen
5. **Review** — Check confidence scores in Results, preview output with syntax highlighting, spell check, confidence heatmap, and image zoom in the Preview window

## Licensing

Doc to Markdown is commercial software by Darksquare.

- **Free tier**: 5 document conversions at no cost to evaluate the tool
- **Licensed**: Unlimited conversions with a purchased license key

License keys are validated offline — no internet connection required. Visit [darksquare.dev](https://darksquare.dev) to purchase a license.

See the `LICENSE` file for full terms.

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
| Markdown Flavor | GFM | Markdown output style (GFM, Obsidian, Pandoc) |
| YAML Front Matter | On | Prepend metadata block to output files |
| Output Format | Markdown | Output file format |
| Overwrite Existing | Off | Replace existing output files |
| Output Subfolder | On | Create per-document subfolders in output |
| Rules Profile | None | Post-processing rules profile to apply |
| Theme | Dark | Interface theme (Dark, Light) |
| Page Range | All pages | Select specific PDF pages to convert (right-click a PDF file) |
| Low Confidence Action | Ask me | Behavior when conversion confidence is low |

## Output Structure

With subfolder output enabled, each converted document produces:

```
output/
  document_name/
    document_name.md          # Converted Markdown output
    assets/                   # Extracted images and media
      image_001.png
      image_002.png
    confidence_report.txt     # Per-file confidence scores
    conversion_log.txt        # Detailed conversion log
```

## Architecture

```
app/
  main.py                     # Entry point: DPI awareness, console hide, crash guard
  gui/
    app.py                    # tkinter GUI (Home, Settings, Conversion, Results, Watch)
    widgets.py                # Custom widgets (PillButton, ToggleSwitch, GlassScrollbar,
                              #   GlassDropdown, PillProgressBar)
    tooltip.py                # Hover tooltip with theme support
    theme.py                  # Dark and light theme color definitions
  config/
    settings.py               # Settings persistence, defaults, load/save
  engine/
    converter.py              # Conversion job orchestration, parallel workers
    pdf_converter.py          # PDF (docling -> pymupdf4llm -> pymupdf+OCR)
    docx_converter.py         # DOCX (docling -> mammoth -> python-docx)
    rtf_converter.py          # RTF (striprtf -> regex fallback)
    xlsx_converter.py         # Excel (openpyxl -> xlrd -> pandas)
    csv_converter.py          # CSV (pandas -> stdlib csv)
    pptx_converter.py         # PowerPoint slides, tables, images, notes
    epub_converter.py         # EPUB chapters, images, TOC
    html_converter.py         # HTML (markdownify -> BeautifulSoup)
    dxf_converter.py          # DXF engineering drawings + SVG preview
    image_converter.py        # Image OCR with preprocessing pipeline
    ocr_engine.py             # OCR orchestration (PaddleOCR + Tesseract)
    language_tools.py         # Language detection + offline translation
    table_extractor.py        # Advanced PDF table structure extraction
    post_processors.py        # Text cleaning (headers, code blocks, footnotes, etc.)
    rules_engine.py           # Named post-processing rule profiles
    output_formats.py         # Output builders (Markdown, JSON, HTML, Text, RAG)
    markdown_writer.py        # Markdown assembly and asset management
    confidence.py             # Confidence scoring and reporting
    validation.py             # Output quality validation
    logger.py                 # Per-file and app-level logging
    watch_folder.py           # Watch Folder automated conversion
    license_manager.py        # License validation and usage tracking
installer/
  doctomarkdown.spec          # PyInstaller build spec
  doctomarkdown.iss           # InnoSetup installer wizard script
  build_installer.bat         # One-click Windows installer build
```

**Pipeline flow**: GUI -> ConversionJob -> Engine Converters -> Post-Processors -> Output Writers

Post-processors run in a fixed order: headers/footers, blank pages, line numbers, code blocks, footnotes, equations.

## Local Processing

This tool processes all files locally on your machine. There are no cloud services, no external APIs, no telemetry, and no remote file uploads. Source documents never leave your computer.

The only network activity occurs on first run when AI models are downloaded and cached locally. After that, the tool operates fully offline.

## Cross-Platform Support

Doc to Markdown targets Windows 10/11, Linux, and macOS:

- **Windows**: Full support including DWM dark title bar, Per-Monitor DPI awareness, and console window hiding
- **Linux**: Tk scaling-based DPI detection, Button-4/5 scroll bindings, XDG-compliant data directories
- **macOS**: Tk scaling DPI, native font selection (Helvetica Neue / Menlo), `open` command for folder navigation

All file paths, font selections, scroll bindings, and platform APIs are guarded with `sys.platform` checks.

## Documentation

Detailed specifications are available in the `docs/` folder:

| Document | Description |
|----------|-------------|
| `PROJECT_SPEC.md` | Project vision, scope, and goals |
| `FEATURE_REQUIREMENTS.md` | Required features and capabilities |
| `GUI_REQUIREMENTS.md` | Interface design, screens, and tooltips |
| `CONVERSION_REQUIREMENTS.md` | Conversion behavior and output rules |
| `CONFIDENCE_REPORTING.md` | Confidence scoring dimensions |
| `LOCAL_PROCESSING_RULES.md` | Local-only processing requirements |
| `LOGGING_REQUIREMENTS.md` | Logging requirements |
| `INSTALLER_UNINSTALLER_REQUIREMENTS.md` | Install and uninstall expectations |
| `DEVELOPMENT_WORKFLOW.md` | Build and development workflow |

## License

Copyright (c) 2025 Darksquare. All rights reserved.

This software is proprietary. Free tier allows 5 conversions for evaluation. A license key is required for unlimited use. See the `LICENSE` file for full terms.

Third-party component licenses are listed in `THIRD_PARTY_LICENSES`.
