# Local Processing Rules

## Local Only Requirement
The tool must process files locally on the user's machine.

Do not add:
- Cloud conversion services
- Remote OCR services
- External AI processing APIs
- Telemetry
- Automatic upload of user documents
- Background transmission of file contents

unless the user explicitly approves that change later.

## User File Privacy
Source files may contain sensitive personal, academic, business, technical, or operational information. The tool should treat all source files as private.

## Allowed Local Behavior
The tool may:
- Read files selected by the user
- Write Markdown output to the selected output folder
- Create extracted asset folders
- Create logs
- Store local settings
- Use locally installed dependencies
- Use local OCR or conversion engines

## Settings Storage
Settings should be stored locally. Settings should not include source file contents unless necessary and approved.

## Logging Privacy
Logs should capture useful technical information without unnecessarily copying large amounts of source document content.

Logs may include:
- File names
- File paths when useful
- Conversion steps
- Warnings
- Errors
- Confidence results
- Engine used
- Processing duration

Logs should avoid storing full extracted document text unless the user explicitly enables verbose diagnostic logging.
