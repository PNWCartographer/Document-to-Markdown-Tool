# Doc to Markdown

**v1.2.0** | **by Darksquare**

A professional desktop tool that converts documents into clean, structured Markdown or Searchable PDF for human review, AI upload, memory systems, knowledgebase repositories, and scanned document archival.

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
| Images | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.tif`, `.webp`, `.gif` | RapidOCR with Tesseract fallback |

### Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| Markdown | `.md` | Structured Markdown with headings, tables, image links, TOC |
| JSON | `.json` | Sections, TOC, confidence data as structured JSON |
| HTML | `.html` | Standalone HTML document with styling |
| Plain Text | `.txt` | Clean text without formatting |
| AI-Ready Chunks | `.jsonl` | Chunked JSONL for vector databases and AI retrieval pipelines |
| Searchable PDF | `.pdf` | Invisible OCR text layer for full-text search and copy-paste |

## Features

### Conversion Engine
- Multi-engine pipeline with automatic fallback chains for every format
- OCR support for scanned documents and images (RapidOCR + Tesseract)
- Ensemble OCR mode — runs both engines and keeps the highest-confidence result per word
- Platform-aware OCR routing (RapidOCR on Windows/Linux, Apple Vision on macOS, Tesseract universal fallback)
- GPU auto-detection and acceleration (CUDA for NVIDIA, DirectML for AMD/Intel, CoreML for macOS)
- OpenCV preprocessing pipeline (deskew, contrast, denoise, threshold, background removal)
- Searchable PDF creation via ocrmypdf with invisible OCR text layer
- Auto-chunking for large documents (30+ pages split and processed in parallel)
- System hardware detection (CPU, RAM, GPU) for automatic performance configuration
- Auto-detection of file types and best conversion method
- Batch conversion with configurable parallel workers and cancel support
- PDF page range selection for converting specific pages instead of full documents
- Quality presets (Fast, Balanced, Quality) to control speed vs. accuracy
- DXF engineering drawing conversion with SVG preview rendering

### Content Handling
- Image preservation with asset extraction and Markdown links
- Image caption detection — auto-identifies figure captions adjacent to extracted images
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
- Six output formats: Markdown, JSON, HTML, Plain Text, AI-Ready Chunks, Searchable PDF
- Searchable PDF with deskew, page cleaning, force OCR, optimization levels, and PDF/A compliance
- Sidecar text output alongside Searchable PDF with optional AI-Ready chunk generation
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
- Parallel workers (1, 2, 4, 8, 12, 16, or Auto) for batch processing — Auto (default) uses the system-recommended count based on detected CPU cores and RAM
- Thread-safe output writing with file locking
- GPU acceleration via ONNX Runtime (CUDA, DirectML, CoreML) — transparent to user
- Auto-chunking splits large documents (30+ pages) into parallel chunks
- System hardware detection for automatic worker and chunk configuration
- Quality presets: Fast skips OCR, Quality enables all engines
- Lazy model loading (AI models download once, cached locally)

### Interface
- Darksquare dark and light themes with Windows DWM title bar integration
- Cross-platform DPI scaling (Windows, Linux, macOS)
- Drag-and-drop file input (tkinterdnd2 with graceful fallback)
- Five main screens: Home, Settings, Conversion, Results, Watch Folder
- Collapsible settings sections with persistent expand/collapse state
- Conditional settings visibility (format-specific options appear only when relevant)
- System performance card in Settings showing detected CPU, RAM, GPU, and accelerator
- Per-file results list with mixed content badges (Text, Tables, Images, OCR, Scanned) color-coded by confidence with colorblind-accessible shapes (▲ high, ● medium, ▼ low)
- Preview window with rich Markdown rendering and review tools
  - Syntax highlighting for headings, code blocks, inline code, blockquotes, links, tables, lists, horizontal rules, image references, and YAML front matter
  - Inline image thumbnails with click-to-zoom full-size viewer
  - Source pages panel with rendered PDF page thumbnails and image previews
  - Source info panel with file metadata and per-dimension confidence breakdown
  - Find and Replace bar (Ctrl+F) with regex support, match navigation, and Replace All
  - Copy Markdown (raw) or Copy Rich (formatted HTML for Word/Docs/email)
  - Spell check toggle with offline dictionary (misspelled words underlined in red)
  - Confidence heatmap overlay — color-codes text, tables, and images by extraction confidence
- Elapsed timer on the Conversion screen showing live M:SS or H:MM:SS duration
- Debug Info window with Export Log (saves full conversion diagnostics to a text file)
- PDF page range selector — visual thumbnail grid with click and Shift+click range selection
- Watch Folder mode for automated batch conversion with format indicator and OCR status
- Completion notification — Results nav button flashes when conversion finishes while viewing another screen
- Keyboard shortcuts: Ctrl+Enter to start conversion from Home, Escape to cancel active conversion
- Post-processing Rules Editor with named profiles
- Tooltip system for every setting with detailed descriptions
- Settings persistence across sessions
- About window with license status and quick-start guide
- Global error handler with crash reporting

## Quick Start

### Prerequisites
- Python 3.10 or later
- Windows 10/11, Linux, or macOS
- **Tesseract OCR** — used for fallback and Ensemble OCR. **Bundled with the Windows installer** — no separate install needed. When running from source, the setup script installs it automatically on Windows; on Linux/macOS install via your package manager (`apt install tesseract-ocr` / `brew install tesseract`)
- **Ghostscript** — required only for the optional Searchable PDF feature. Not bundled (AGPL-licensed); the app guides you to install it from [ghostscript.com](https://ghostscript.com/releases/gsdnld.html) the first time you use Searchable PDF

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

The first run may download AI models for docling and RapidOCR (approximately 1-2 GB). Models are cached locally after download and all processing remains offline.

### Basic Usage

1. **Add Files** — Click "Add Files" or drag documents onto the Home screen
2. **Set Output** — Choose an output folder for converted files
3. **Configure** — Adjust settings if needed (defaults work well for most documents)
4. **Convert** — Click "Convert" and monitor progress in the Conversion screen
5. **Review** — Check confidence scores in Results, preview output with syntax highlighting, spell check, confidence heatmap, and image zoom in the Preview window

## Licensing

Doc to Markdown is commercial software by Darksquare.

- **Free tier**: 10 document conversions at no cost to evaluate the tool
- **Licensed**: Unlimited conversions with a purchased license key

License keys are validated offline — no internet connection required. Visit [darksquare.dev](https://darksquare.dev) to purchase a license.

See the `LICENSE` file for full terms.

## Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| **Conversion** | | |
| Conversion Mode | Auto-detect | How the tool reads documents (Auto-detect, Standard, OCR) |
| Quality Preset | Quality | Speed vs. accuracy tradeoff (Fast, Balanced, Quality) |
| **Content Handling** | | |
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
| **OCR** | | |
| OCR Engine | Auto | Preferred OCR engine (Auto, RapidOCR, Tesseract, Ensemble, Apple Vision) |
| OCR Language | English | Language for OCR text recognition |
| **Output** | | |
| Output Format | Markdown | Output file format (Markdown, JSON, HTML, Plain Text, AI-Ready Chunks, Searchable PDF) |
| Markdown Flavor | GFM | Markdown output style — visible when format is Markdown |
| YAML Front Matter | On | Prepend metadata block — visible when format is Markdown |
| Overwrite Existing | Off | Replace existing output files |
| Output Subfolder | On | Create per-document subfolders in output |
| **Searchable PDF** | | *Visible when Output Format is Searchable PDF* |
| Deskew | On | Straighten tilted scanned pages |
| Clean Pages | Off | Remove speckles and scan artifacts |
| Force OCR | Off | Re-OCR pages that already have text |
| Optimize | 1 | Output compression level (0 = none, 3 = maximum) |
| PDF/A Compliance | Off | Produce PDF/A-compliant archival output |
| Sidecar Text | Off | Save extracted OCR text as a separate text file |
| AI-Ready from Sidecar | Off | Generate AI-Ready chunks from sidecar text |
| Background Removal | Off | Remove colored backgrounds before OCR |
| **Performance** | | |
| Parallel Workers | Auto | Number of files to convert simultaneously (1, 2, 4, 8, 12, 16, Auto). Auto uses system-detected recommendation |
| Low Confidence Action | Ask me | Behavior when conversion confidence is low |
| **Post-Processing** | | |
| Rules Profile | None | Post-processing rules profile to apply |
| **Interface** | | |
| Theme | System | Interface theme (System, Dark, Light) |

## Output Structure

With subfolder output enabled, each converted document produces:

**Markdown and other text formats:**
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

**Searchable PDF format:**
```
output/
  document_name/
    document_name.pdf              # Searchable PDF with OCR text layer
    document_name_sidecar.txt      # Extracted OCR text (optional)
    document_name_rag.jsonl        # AI-Ready chunks from sidecar (optional)
    confidence_report.txt          # Per-file confidence scores
    conversion_log.txt             # Detailed conversion log
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
    ocr_engine.py             # OCR orchestration (RapidOCR + Tesseract + Ensemble)
    ocr_ensemble.py           # OCR ensemble — word-level RapidOCR + Tesseract merge
    ocr_platform.py           # Platform-aware OCR engine routing (Win/Linux/macOS)
    searchable_pdf.py         # ocrmypdf wrapper, auto-chunking, sidecar output
    ocrmypdf_rapidocr.py      # Custom ocrmypdf plugin for RapidOCR backend
    system_info.py            # CPU/RAM/GPU detection, performance auto-config
    language_tools.py         # Language detection + offline translation
    table_extractor.py        # Advanced PDF table structure extraction
    post_processors.py        # Text cleaning (headers, code blocks, footnotes, etc.)
    rules_engine.py           # Named post-processing rule profiles
    output_formats.py         # Output builders (Markdown, JSON, HTML, Text, AI-Ready Chunks, Searchable PDF)
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

For Searchable PDF: GUI -> ConversionJob -> ocrmypdf (with RapidOCR plugin) -> Sidecar/AI-Ready Writers

Post-processors run in a fixed order: headers/footers, blank pages, line numbers, code blocks, footnotes, equations.

### OCR Engine Architecture

```
ocr_platform.py (platform router)
  ├── Windows/Linux
  │   ├── RapidOCR (ONNX Runtime: CUDA > DirectML > CPU)
  │   ├── Tesseract (fallback)
  │   └── Ensemble (RapidOCR + Tesseract confidence voting)
  └── macOS
      ├── Apple Vision (Neural Engine via ocrmac)
      ├── RapidOCR (CoreML provider)
      └── Tesseract (fallback)
```

## Local Processing

This tool processes all files locally on your machine. There are no cloud services, no external APIs, no telemetry, and no remote file uploads. Source documents never leave your computer.

The only network activity occurs on first run when AI models are downloaded and cached locally. After that, the tool operates fully offline. GPU acceleration (CUDA, DirectML, CoreML) is detected and used automatically when available.

## Cross-Platform Support

Doc to Markdown targets Windows 10/11, Linux, and macOS:

- **Windows**: Full support including DWM dark title bar, Per-Monitor DPI awareness, console window hiding, CUDA and DirectML GPU acceleration
- **Linux**: Tk scaling-based DPI detection, Button-4/5 scroll bindings, XDG-compliant data directories, CUDA GPU acceleration
- **macOS**: Tk scaling DPI, native font selection (Helvetica Neue / Menlo), `open` command for folder navigation, Apple Vision Framework OCR via Neural Engine, CoreML acceleration

All file paths, font selections, scroll bindings, platform APIs, and OCR engine selection are guarded with `sys.platform` checks.

## Documentation

Detailed specifications are available in the `docs/` folder:

| Document | Description |
|----------|-------------|
| `PROJECT_SPEC.md` | Project vision, scope, and goals |
| `FEATURE_REQUIREMENTS.md` | Required features and capabilities |
| `GUI_REQUIREMENTS.md` | Interface design, screens, and tooltips |
| `CONVERSION_REQUIREMENTS.md` | Conversion behavior, output rules, Searchable PDF pipeline |
| `CONFIDENCE_REPORTING.md` | Confidence scoring dimensions |
| `LOCAL_PROCESSING_RULES.md` | Local-only processing requirements |
| `LOGGING_REQUIREMENTS.md` | Logging requirements |
| `INSTALLER_UNINSTALLER_REQUIREMENTS.md` | Install and uninstall expectations |
| `DEVELOPMENT_WORKFLOW.md` | Build and development workflow |
| `CLAUDE_PROMPT_TEMPLATES.md` | Reusable prompts for Claude Code sessions |

## License

Copyright (c) 2025 Darksquare. All rights reserved.

This software is proprietary. Free tier allows 10 conversions for evaluation. A license key is required for unlimited use. See the `LICENSE` file for full terms.

Third-party component licenses are listed in `THIRD_PARTY_LICENSES`.
