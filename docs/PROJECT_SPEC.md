# Project Specification

## Project Name
Documentation to Markdown Converter Tool

## Project Summary
The Documentation to Markdown Converter Tool is a local desktop utility intended to convert complex documents into clean Markdown or Searchable PDF. The output should be suitable for human reading, AI upload, memory systems, documentation repositories, knowledgebase use, and archival.

The tool began as a rudimentary PDF to Markdown converter. It has grown into a broader document conversion tool that handles PDFs, Word documents, DOCX files, Excel files, CSV files, datasets, tables, matrices, images with text, electrical drawings with text, and embedded content inside source documents. It also produces Searchable PDFs with invisible OCR text layers for scanned document archival and full-text search.

## Main Goal
The main goal is not just text extraction. The main goal is structured conversion.

The output should preserve the source document structure as much as practical. This includes document order, headings, paragraphs, tables, matrices, images, drawings, captions, page context, and embedded content references.

For Searchable PDF output, the goal is to add an invisible OCR text layer to scanned or image-based PDFs so they become full-text searchable while preserving the original visual appearance.

## Primary Users
The expected users are people who need to convert documents into Markdown or Searchable PDF for:
- AI analysis
- Knowledgebase storage
- Documentation cleanup
- Technical documentation review
- Internal research
- Document indexing
- Human readable archives
- Scanned document archival with full-text search
- Automated batch OCR processing via Watch Folder

## Operating Model
The tool must run locally. Source files should remain on the user's machine. The tool should not depend on cloud conversion services or remote file processing unless explicitly approved in the future.

## High Level Workflow
1. User opens the GUI.
2. Tool detects system hardware (CPU, RAM, GPU) and configures performance automatically.
3. User selects one or more source files or a folder.
4. User chooses conversion settings (output format, OCR options, content handling).
5. Tool detects file types.
6. Tool selects the best local conversion method and OCR engine for the platform.
7. Tool extracts text, tables, images, drawings, and other structured content.
8. Tool builds organized output (Markdown, Searchable PDF, JSON, HTML, Plain Text, or RAG Chunks).
9. Tool creates a confidence report.
10. Tool saves output, extracted assets, logs, and reports to the selected output location.
11. User reviews final results with syntax-highlighted preview, confidence heatmap, and spell check.

## Success Criteria
The project is successful when users can convert mixed document types into readable Markdown or Searchable PDF while preserving structure well enough for AI upload, documentation work, knowledgebase ingestion, or scanned document archival with full-text search.

## Cross-Platform Target
The tool targets Windows 10/11, Linux, and macOS. All features must work cross-platform with platform-specific optimizations:
- **Windows**: Full support including DWM dark title bar, DPI awareness, CUDA/DirectML GPU acceleration
- **Linux**: Tk scaling DPI, XDG directories, CUDA GPU acceleration
- **macOS**: Native fonts, Apple Vision Framework OCR via Neural Engine, CoreML acceleration
