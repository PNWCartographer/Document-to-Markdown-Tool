# GUI Requirements

## Design Goal
The GUI should be clean, simple, and modern. The preferred visual direction is an Apple like interface with clear spacing, simple controls, readable text, and minimal clutter.

## Theme Options
The GUI should include:
- Light mode
- Dark mode
- System default option if practical

## Main Screens
The GUI should eventually include these areas:

### Home Screen
The home screen should let the user select files or folders and choose the output location.

### Settings Screen
The settings screen should allow the user to configure conversion behavior.

### Conversion Screen
The conversion screen should show progress, current file, current stage, errors, warnings, and completion status.

### Results Screen
The results screen should show final output location, confidence report summary, warnings, and buttons to open output files.

## Required Controls
The GUI should include:
- File picker
- Folder picker
- Output folder selector
- Dropdown menus
- Checkboxes
- Tooltips
- Language selection dropdown
- Conversion mode dropdown
- Theme selection
- Start conversion button
- Cancel conversion button if practical
- Open output folder button

## Tooltip Requirements

Every setting, option, or control that affects conversion behavior must have a tooltip. Tooltips are required, not optional.

### Tooltip Standards

Tooltips must:
- Use plain language that a non-technical user can understand
- Explain what the setting does and why it matters
- Note any tradeoffs, risks, or situations where the setting should be changed
- Be short enough to read at a glance (2 to 4 sentences maximum)
- Never use internal technical terms without explaining them

Tooltips must not:
- Repeat the label text without adding context
- Use jargon such as "parser", "xref", "pipeline", or "engine" without explanation
- Assume the user knows what OCR, DPI, or encoding means

### Settings That Require Tooltips

Every setting on the Settings screen requires a tooltip. Required tooltip coverage includes but is not limited to:

**Conversion Mode**
```
Conversion Mode:
Controls how the tool reads and converts your document. Standard mode works
for most documents. OCR mode is needed for scanned documents or images where
the text cannot be selected. Using OCR on a document that already has
selectable text may reduce quality.
```

**Preserve Images**
```
Preserve Images:
Extracts images, diagrams, and drawings from the source document and saves
them in an assets folder next to your Markdown file. The Markdown output will
include links to these images. Turn this off if you only need the text content.
```

**Preserve Page Numbers**
```
Preserve Page Numbers:
Inserts a page marker at each page boundary in the Markdown output. This lets
you cross-reference the Markdown file against the original document by page
number. Recommended for textbooks, manuals, and any document where page
references matter.
```

**Rebuild Table of Contents**
```
Rebuild Table of Contents:
If your document has a table of contents, this option extracts it and places a
navigable version at the top of the Markdown output. Each entry links directly
to the correct page in the document. Only available when a table of contents
or heading structure is detected in the source file.
```

**OCR Language**
```
OCR Language:
Sets the language the OCR engine uses when reading text from scanned pages or
images. Choose the language that matches your document. Using the wrong
language may produce garbled or incorrect text. This setting only affects
files that require OCR processing.
```

**Overwrite Existing Files**
```
Overwrite Existing Files:
If a Markdown file with the same name already exists in the output folder, this
option replaces it. If turned off, the tool will skip files that already exist
and leave the originals unchanged. Turn this on carefully if you want to
re-convert files you have already edited.
```

**Output Subfolder Structure**
```
Output Subfolder Structure:
Creates a separate folder for each converted document inside your output
location. Each folder contains the Markdown file, extracted assets, a
confidence report, and a conversion log. Turning this off places all output
files directly in the output folder, which can become difficult to manage with
multiple documents.
```

**Handle Low Confidence Results**
```
Handle Low Confidence Results:
Controls what happens when the tool is not confident about a conversion result,
such as unclear OCR text or a table that could not be read cleanly. Ask me
will pause and show you a choice. Keep and flag will include the uncertain
content and mark it for review. Skip will leave it out entirely.
```

**Remove Headers and Footers**
```
Remove Headers and Footers:
Removes repeated headers and footers that appear on every page. This prevents
the same text from cluttering your Markdown output. Turn this off if headers
or footers contain important content you want to keep.
```

**Skip Blank Pages**
```
Skip Blank Pages:
Skips pages that contain little or no meaningful text. This removes empty
separator pages and blank backs of double-sided scans. Turn this off if blank
pages are intentional and should be preserved.
```

**Strip Line Numbers**
```
Strip Line Numbers:
Removes line numbers that appear in the margins of legal documents, code
listings, or academic papers. Off by default because most documents do not
have line numbers. Turn this on only if your source has numbered lines.
```

**Detect Code Blocks**
```
Detect Code Blocks:
Identifies sections of source code or terminal output and wraps them in code
blocks in the Markdown output. Uses font changes and indentation patterns to
distinguish code from normal text. Recommended for technical documents.
```

**Detect Footnotes**
```
Detect Footnotes:
Finds footnotes and endnotes in the document and converts them into Markdown
footnote syntax. Links each reference number to its footnote text at the
bottom of the section. Recommended for academic and legal documents.
```

**Detect Equations**
```
Detect Equations:
Detects mathematical equations, formulas, and expressions and preserves them
using LaTeX notation in the Markdown output. Looks for Greek letters, math
symbols, and formula patterns. Recommended for scientific and engineering
documents.
```

**Parallel Workers**
```
Parallel Workers:
Controls how many files are converted at the same time. Higher values convert
batches faster but use more memory and CPU. Start with 1 and increase if you
are converting many files and have available system resources.
```

**Quality Preset**
```
Quality Preset:
Controls the tradeoff between conversion speed and output quality. Fast skips
OCR and advanced table detection. Balanced uses standard processing. Quality
enables all analysis engines for the most accurate results.
```

### Tooltip Implementation Notes

Tooltips should appear when the user hovers over the setting label or a small
info icon placed next to the label. A small circle with an "i" or a question
mark is the recommended icon.

Tooltip delay should be short, around 400 to 600 milliseconds, so the tooltip
appears quickly without flickering on accidental hover.

Tooltips should respect the current theme and use the same color palette as
the rest of the interface.

## Language Dropdown
The language dropdown should allow users to select OCR or conversion language options when supported by the local engine. Translation should not be assumed unless a local translation capability is intentionally added later.

The GUI should distinguish between:
- OCR language recognition
- Output language translation

Local processing remains required.

## User Friendly Error Messages
Errors should be readable by non technical users.

Bad example:

```text
Exception: parser failed at object xref 271
```

Better example:

```text
The PDF could not be fully read. The file may be damaged, encrypted, or contain unsupported content. Try enabling OCR fallback or review the log file.
```

## Settings Screen Layout

The Settings screen is organized into sections with consistent spacing and layout.

### Section Order
1. **Conversion** — Conversion mode dropdown
2. **Content Handling** — 10 checkboxes controlling content processing:
   - Preserve Images (on)
   - Embed Images (on)
   - Preserve Page Numbers (on)
   - Rebuild Table of Contents (on)
   - Remove Headers and Footers (on)
   - Skip Blank Pages (on)
   - Strip Line Numbers (off)
   - Detect Code Blocks (on)
   - Detect Footnotes (on)
   - Detect Equations (on)
3. **Performance** — 2 dropdowns:
   - Parallel Workers: 1, 2, 4, Auto
   - Quality Preset: Fast, Balanced, Quality
4. **OCR** — OCR language dropdown
5. **Output** — Output format dropdown (Markdown, JSON, HTML, Plain Text, RAG Chunks), overwrite toggle, subfolder toggle, low confidence action
6. **Reset** — Reset to Defaults button

Each setting has a tooltip icon that displays help text on hover.

## Debug/Preview Button

The Results screen includes a "View Debug Info" button in the button row alongside "Open Output Folder" and other action buttons.

When clicked, it opens a diagnostic window showing:
- Engine used for each file
- Overall and per-dimension confidence scores
- Warnings and notes from the conversion process
- Current settings snapshot at the time of conversion

This is not a persistent setting. It is a diagnostic tool available after each conversion completes.

## Output Format Options

The Output Format dropdown includes:
- Markdown (.md)
- JSON (.json)
- HTML (.html)
- Plain Text (.txt)
- RAG Chunks (.jsonl)

RAG Chunks produces JSONL output designed for AI retrieval systems and vector databases. Each line is a self-contained text chunk with metadata about its source, section, and position.
