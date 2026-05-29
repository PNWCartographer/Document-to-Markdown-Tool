# Logging Requirements

## Logging Goal
The tool should create detailed logs that help users and developers understand what happened during conversion.

Logs should be useful for troubleshooting without exposing unnecessary document content.

## Log Location
The application log is stored in the user's application data directory:

```text
%APPDATA%\DocToMarkdown\app.log
```

This avoids permission issues with Program Files and ensures logs are accessible without administrator rights.

## Log Types
The tool uses two logger classes:

- **AppLogger** — Application-level logger. Writes to `app.log` in the app data directory. Captures startup, shutdown, settings changes, system detection, errors, and general application events.
- **ConversionLogger** — Per-file conversion logger. Writes to the GUI log panel during conversion and optionally writes a per-file log file in the output directory alongside the converted file. Captures conversion stages, engine selection, OCR activity, confidence results, warnings, and errors for each file.

## Information to Log
Logs should include:
- Start time
- End time
- Source file name
- Source file type
- Output path
- Output format (Markdown, JSON, HTML, Plain Text, AI-Ready Chunks, Searchable PDF)
- Conversion engine used
- OCR engine used and execution provider (e.g., "RapidOCR via CUDA", "Tesseract", "Ensemble")
- Settings used
- Processing stages
- Auto-chunking activity (chunk count, pages per chunk, workers used)
- Pages OCR'd vs pages skipped (for Searchable PDF)
- Sidecar and AI-Ready chunk output paths when generated
- System hardware detected (CPU, RAM, GPU, accelerator)
- Warnings
- Errors
- Confidence results
- Manual review recommendations

## Information to Avoid by Default
Logs should avoid storing full extracted document content by default.

Verbose logging may be added later as an optional troubleshooting setting.

## Example Log Entry

```text
2026-05-06 10:22:14 | INFO | Started conversion | file=example.pdf
2026-05-06 10:22:17 | INFO | Detected file type | type=PDF
2026-05-06 10:22:21 | WARNING | Low OCR confidence | page=4 confidence=Low
2026-05-06 10:22:25 | INFO | Markdown created | output=example.md
```

## Searchable PDF Logging
Searchable PDF conversions generate additional log entries:
- ocrmypdf exit code and status
- Per-page OCR status (processed, skipped, failed)
- Deskew angle applied per page (when deskew is enabled)
- Optimization results (input size vs output size)
- PDF/A validation result (when PDF/A is enabled)
- Background removal activity (pages processed, when enabled)
- Ensemble mode details (per-word engine selection counts, when ensemble is used)

## Error Reporting
Errors should be logged with enough detail for debugging and shown to the user in plain language.
