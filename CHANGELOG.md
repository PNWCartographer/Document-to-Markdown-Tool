# Changelog

All notable changes to Markwell are documented in this file.

## [1.0.0] - 2026-06-08 (Markwell — Initial Public Release)

First public release under the name **Markwell** (by Darksquare). Versions
0.1.0–0.3.0 below are the pre-launch development history under the project's
former working name.

### Added
- Rebranded the product to **Markwell** across the app, installer, and documentation
- Bundled Tesseract OCR engine (Apache 2.0) in the Windows installer — fallback and Ensemble OCR now work fully offline with no separate install
- Runtime binary resolver (`app/engine/vendor.py`) — prefers bundled engines, falls back to system installs
- Ghostscript guidance for the optional Searchable PDF feature: an install-time courtesy page and an in-app runtime gate, both linking to the official download page (Ghostscript is not bundled, per its AGPL license)
- `installer/stage_vendor.py` — stages and trims Tesseract into the build for bundling
- Themed, DPI-scaled, anti-aliased dialogs replacing native message boxes; crisp pill buttons app-wide
- Clear first-run messaging for the one-time AI-model download, so it no longer looks frozen
- Quick Start Guide (`Guide.html`) opened in the browser after install, with screenshots

### Changed
- Free tier limit set to 10 conversions
- Per-user data folder is now `%APPDATA%\Markwell`
- `THIRD_PARTY_LICENSES` documents the bundled Tesseract runtime libraries and the not-bundled Ghostscript arrangement

## [0.3.0] - 2026-05-27 (Searchable PDF & OCR Overhaul)

### Added
- Searchable PDF output format — adds invisible OCR text layer to scanned PDFs for full-text search
- RapidOCR engine replacing PaddlePaddle — 90% smaller install, same accuracy, cross-platform GPU support
- Ensemble OCR mode — runs RapidOCR and Tesseract together, keeps highest-confidence result per word
- GPU auto-detection and acceleration (CUDA for NVIDIA, DirectML for AMD/Intel, CoreML for macOS)
- System hardware detection (CPU, RAM, GPU) with automatic performance configuration
- Platform-aware OCR routing (RapidOCR on Windows/Linux, Apple Vision prep for macOS, Tesseract universal fallback)
- Auto-chunking for large documents (30+ pages split into parallel chunks)
- Sidecar text output alongside Searchable PDF with optional RAG chunk generation
- Searchable PDF settings: deskew, clean pages, force OCR, optimize level, PDF/A compliance, background removal
- Collapsible settings sections with persistent expand/collapse state
- Conditional settings visibility (format-specific options appear only when relevant)
- Performance info card in Settings showing detected CPU, RAM, GPU, and accelerator
- Mixed content badges in Results screen (Text, Tables, Images, OCR, Scanned)
- Watch Folder format indicator showing current output format
- OCR Engine dropdown expanded: Auto, RapidOCR, Tesseract, Ensemble
- Parallel workers expanded to 1, 2, 4, 8, 12, 16, Auto
- Indeterminate progress bar for long-running conversions
- Responsive cancel with mid-file interruption support
- Composite overall progress bar blending per-file progress into batch total
- Conversion elapsed timer on the Conversion screen
- Per-file results badges on the Results screen with confidence-colored chips
- Keyboard shortcuts: Escape to cancel, Ctrl+Enter to start conversion

### Changed
- OCR engine swapped from PaddlePaddle/PaddleOCR to RapidOCR (ONNX Runtime)
- Settings screen reorganized into collapsible sections
- Output Format dropdown includes Searchable PDF option
- About window updated with GPU acceleration and Searchable PDF
- Fast quality preset now skips docling entirely for faster text-based PDF conversion

### Dependencies Added
- rapidocr-onnxruntime >= 1.2.0 (replaces paddlepaddle and paddleocr)
- ocrmypdf >= 17.0.0
- psutil >= 5.9.0
- nvidia-ml-py >= 12.0.0 (optional, NVIDIA GPU detection)

### Dependencies Removed
- paddlepaddle
- paddleocr

## [0.2.0] - 2026-05-14 (Feature Expansion)

### Added
- Header and footer removal: auto-detects and strips repeated page text across all pages
- Blank page skipping: removes empty separator pages and blank backs of double-sided scans
- Line number stripping: removes margin line numbers from legal and academic documents
- Code block detection: identifies source code by monospace font, indentation, and symbol patterns
- Footnote handling: converts footnotes and endnotes to Markdown footnote syntax
- Equation detection: preserves mathematical expressions as LaTeX notation
- PowerPoint (.pptx) file support with slide titles, tables, images, and speaker notes
- EPUB (.epub) e-book support with chapter order, images, and table of contents
- RAG Chunks output format (.jsonl) for vector database and AI retrieval ingestion
- Debug/Preview mode on the Results screen showing engine details, confidence scores, and warnings
- Parallel workers setting (1, 2, 4, 8, 12, 16, Auto) for faster batch processing
- Conversion quality presets (Fast, Balanced, Quality) controlling speed vs. accuracy tradeoff
- Post-processor pipeline running between conversion and output writing
- 8 new tooltip texts for new settings
- Performance section on the Settings screen
- View Debug Info button on the Results screen

### Changed
- Content Handling section expanded with 6 new toggles
- Output Format dropdown includes RAG Chunks option
- Converter routing now supports .pptx and .epub extensions
- File picker dialogs accept .pptx and .epub files
- Conversion job supports ThreadPoolExecutor for parallel file processing
- Quality preset modifies engine selection: Fast skips OCR and docling, Balanced limits fallbacks

### Dependencies Added
- python-pptx >= 1.0.0
- ebooklib >= 0.18
- beautifulsoup4 >= 4.12.0

## [0.1.0] - 2026-05-06 (Initial Development Release)

### Added
- PDF conversion with multi-engine fallback chain (docling, pymupdf4llm, pymupdf+OCR)
- DOCX/DOC conversion with multi-engine fallback (docling, mammoth, python-docx)
- XLSX/XLS spreadsheet conversion with openpyxl and xlrd
- CSV conversion with pandas
- Image OCR conversion for PNG, JPG, BMP, TIFF, WebP, GIF (OCR engine + Tesseract)
- Markdown output with heading hierarchy, tables, image links, and TOC
- JSON structured output format
- HTML standalone output format
- Plain Text output format
- Confidence reporting across 6 dimensions (text, tables, images, placement, order, OCR)
- Per-file conversion logging
- Batch conversion with progress tracking and cancel support
- Light and dark themes with Windows title bar integration
- Settings persistence via JSON with auto-save
- Tooltip system for all settings
- OCR language selection (English, Spanish, French, German, Chinese, Japanese, Korean, Auto-detect)
- Conversion mode selection (Auto-detect, Standard, OCR)
- Low confidence action options (Ask me, Keep and flag, Skip)
- Home, Settings, Conversion, and Results screens
- File picker with single file, multi-file, and folder selection
- Output folder selection
