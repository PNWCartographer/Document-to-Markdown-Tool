# Feature Requirements

## Required File Inputs
The tool should eventually support:
- PDF files
- Word documents
- DOCX files
- Excel files
- CSV files
- Dataset files
- PowerPoint presentations (.pptx) — slides, tables, images, speaker notes
- EPUB e-books (.epub) — chapters, images, TOC, metadata
- RTF files (.rtf)
- HTML files (.html, .htm)
- DXF files (.dxf) — CAD drawing layer/text/dimension extraction
- Images with text
- Electrical drawings with text
- Tables
- Matrices
- Embedded images inside source documents
- Embedded drawings or diagrams inside source documents

## Required Outputs
The tool should produce:
- Markdown files
- JSON structured output
- HTML standalone documents
- Plain Text output
- RAG Chunks (.jsonl) — chunked JSONL for vector databases and AI retrieval
- Searchable PDF (.pdf) — adds invisible OCR text layer to scanned/image-based PDFs for full-text search
- Sidecar text files (optional, alongside Searchable PDF output)
- Sidecar RAG chunks (optional, generated from sidecar text when Searchable PDF is the output format)
- Extracted image assets when needed
- Linked image references inside Markdown
- Confidence reports
- Detailed logs
- Error reports when conversion issues occur

## Required User Functions
The user should be able to:
- Select a single file
- Select multiple files
- Select a folder
- Choose an output folder
- Select conversion mode
- Select language options
- Choose whether to preserve images
- Choose whether to OCR images
- Choose how to handle low confidence results
- Toggle header and footer removal
- Toggle blank page skipping
- Toggle line number stripping
- Toggle code block detection
- Toggle footnote detection
- Toggle equation detection
- Select parallel worker count for batch processing
- Select quality preset (Fast, Balanced, Quality)
- Select output format (Markdown, JSON, HTML, Plain Text, RAG Chunks, Searchable PDF)
- Configure Searchable PDF options (deskew, clean, force OCR, optimize, PDF/A, sidecar, background removal)
- Select OCR engine (Auto, RapidOCR, Tesseract, Ensemble, Apple Vision on macOS)
- View system hardware detection (CPU, RAM, GPU, accelerator) in Settings
- Expand and collapse settings sections for cleaner navigation
- View conversion status
- View final success or error messages with mixed content badges
- View debug/diagnostic information on the Results screen
- Preview output with syntax highlighting, search, spell check, confidence heatmap, and image zoom
- Open output folder after conversion

## Required Conversion Behavior
The tool should attempt to preserve:
- Reading order
- Headings
- Paragraphs
- Tables
- Matrices
- Captions
- Images
- Electrical drawings
- Diagram placement
- Page level context
- File names and source traceability

## Edge Case Handling
When the tool is uncertain, it should present a clear user choice instead of silently making a poor conversion decision.

Examples:
- Low OCR confidence
- Table structure is unclear
- Image contains text but OCR is uncertain
- Embedded drawing cannot be converted cleanly
- Source file has mixed orientation pages
- File is encrypted or locked
- File type is unsupported

## OCR Engine Architecture
The tool uses a multi-engine OCR architecture with platform-aware routing:

- **RapidOCR** (primary) — ONNX Runtime-based OCR using PaddleOCR models. Cross-platform GPU acceleration via CUDA (NVIDIA), DirectML (AMD/Intel on Windows), CoreML (macOS), or CPU fallback. Replaces PaddlePaddle for smaller install size and broader GPU support.
- **Tesseract** (fallback) — Traditional OCR engine. Universal cross-platform support. Requires external binary.
- **Apple Vision** (macOS only) — Apple's Neural Engine OCR via the Vision framework. Fastest option on Apple Silicon Macs.
- **Ensemble mode** (opt-in) — Runs RapidOCR and Tesseract on the same page, compares word-level confidence scores, and keeps the higher-confidence result for each word. Reduces OCR errors by 30-50% at the cost of processing time.

Engine selection is automatic by default. The tool detects available engines and GPU providers at startup and selects the best option for the platform.

## System Detection
The tool automatically detects system hardware at startup:
- CPU model and core count
- Available RAM
- GPU model and VRAM (NVIDIA via nvidia-ml-py, others via ONNX Runtime provider detection)
- Available ONNX Runtime execution providers (CUDA, DirectML, CoreML, CPU)

System information is used to:
- Auto-configure parallel worker count based on available CPU cores and RAM
- Select the optimal ONNX Runtime execution provider for GPU acceleration
- Determine auto-chunking parameters for large documents
- Display system capabilities in the Settings performance card and About window

## Batch Conversion
The tool should support batch processing. Batch output should keep files organized by source file name.

Example output structure:

```text
output/
  SourceDocumentName/
    SourceDocumentName.md
    assets/
    confidence_report.txt
    conversion_log.txt
```

### Auto-Chunking for Large Documents
Documents exceeding 30 pages are automatically split into chunks of 20-30 pages (determined by available RAM), processed in parallel via multiple worker processes, and reassembled into a single output file. This is fully automatic with no user-facing setting.

## Searchable PDF Output
The Searchable PDF format uses ocrmypdf to add an invisible OCR text layer to scanned or image-based PDFs. The original visual appearance is preserved while enabling full-text search, copy-paste, and accessibility.

### Searchable PDF Features
- Deskew correction for tilted scans
- Page cleaning for scan artifacts (optional, off by default)
- Force OCR mode to re-OCR pages that already have text
- Optimization levels (0-3) for output file size
- PDF/A compliance for archival standards (optional)
- Sidecar text file with extracted OCR text
- RAG chunks generated from sidecar text (optional)
- Background removal for scanned documents with colored paper (optional, with warning)
- Auto-chunking for documents over 30 pages
- Watch Folder support for automated batch OCR

### Searchable PDF Engine
- Uses ocrmypdf Python API (not subprocess)
- Custom RapidOCR plugin routes OCR through ONNX Runtime instead of Tesseract
- On macOS, Apple Vision Framework plugin is used when available
- Not thread-safe — uses ProcessPoolExecutor for parallel processing
- Multiprocessing guard required on Windows and macOS

## Future Feature Ideas
Future versions may include:
- DOCX export
- Accessibility tagging for Searchable PDF (PDF/UA)
- AI ready formatting profiles
- Knowledgebase export presets
- Saved user profiles
