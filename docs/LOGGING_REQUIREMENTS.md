# Logging Requirements

## Logging Goal
The tool should create detailed logs that help users and developers understand what happened during conversion.

Logs should be useful for troubleshooting without exposing unnecessary document content.

## Log Folder
The installed application should include a logs folder.

Recommended location:

```text
C:\Program Files\Documentation to Markdown Converter Tool\logs\
```

If permission issues occur with Program Files, the tool may need to write user specific logs to a safe local application data folder.

## Log Types
The tool should support:
- General application log
- Conversion log per file
- Error log
- Installer log
- Uninstaller log

## Information to Log
Logs should include:
- Start time
- End time
- Source file name
- Source file type
- Output path
- Conversion engine used
- Settings used
- Processing stages
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

## Error Reporting
Errors should be logged with enough detail for debugging and shown to the user in plain language.
