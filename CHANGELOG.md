# Changelog

All notable changes to the Documentation to Markdown Converter Tool are documented in this file.

## [1.1.0] - 2026-05-14 (Feature Expansion)

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
- Parallel workers setting (1, 2, 4, or Auto) for faster batch processing
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

## [1.0.0] - 2026-05-06 (Initial Release)

### Added
- PDF conversion with multi-engine fallback chain (docling, pymupdf4llm, pymupdf+OCR)
- DOCX/DOC conversion with multi-engine fallback (docling, mammoth, python-docx)
- XLSX/XLS spreadsheet conversion with openpyxl and xlrd
- CSV conversion with pandas
- Image OCR conversion for PNG, JPG, BMP, TIFF, WebP, GIF (PaddleOCR + Tesseract)
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
