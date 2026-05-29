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
- Write output files (Markdown, JSON, HTML, Plain Text, AI-Ready Chunks, Searchable PDF) to the selected output folder
- Create extracted asset folders
- Create sidecar text and AI-Ready chunk files alongside Searchable PDF output
- Create logs
- Store local settings
- Use locally installed dependencies
- Use local OCR or conversion engines (RapidOCR, Tesseract, Apple Vision)
- Use local ONNX Runtime with GPU acceleration (CUDA, DirectML, CoreML)
- Detect system hardware (CPU, RAM, GPU) for performance auto-configuration
- Query ONNX Runtime for available execution providers
- Query NVIDIA GPU info via nvidia-ml-py for VRAM detection

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

## GPU and Hardware Detection Privacy
System hardware detection (CPU, RAM, GPU) is used only for local performance auto-configuration:
- Results are displayed in the Settings performance card and About window
- Results are never transmitted externally
- No hardware fingerprinting or unique identifiers are collected
- GPU model and VRAM info is used only to select the optimal ONNX Runtime execution provider

## Model and Engine Privacy
- RapidOCR models are downloaded once and cached locally (same as previous PaddleOCR behavior)
- ONNX Runtime is a local inference engine with no network activity after installation
- ocrmypdf processes all PDFs locally with no external calls
- Apple Vision Framework (macOS) is a system API that runs entirely on-device
