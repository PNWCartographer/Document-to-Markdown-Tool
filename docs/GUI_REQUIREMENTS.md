# GUI Requirements

## Design Goal
The GUI should be clean, simple, and modern. The preferred visual direction is an Apple like interface with clear spacing, simple controls, readable text, and minimal clutter.

## Theme Options
The GUI should include:
- Light mode
- Dark mode
- System default option if practical

## Main Screens
The GUI includes five main areas:

### Home Screen
The home screen lets the user select files or folders and choose the output location. Supports drag-and-drop file input.

### Settings Screen
The settings screen allows the user to configure conversion behavior. Settings are organized into collapsible sections with chevron toggles. Format-specific settings are shown or hidden based on the selected output format.

### Conversion Screen
The conversion screen shows progress, current file, current stage, errors, warnings, and completion status. An elapsed timer displays live conversion duration in M:SS or H:MM:SS format, starting when conversion begins and stopping at completion.

### Results Screen
The results screen shows final output location, confidence report summary, warnings, mixed content badges per file, and buttons to preview output, view debug info, and open the output folder.

### Watch Folder Screen
The watch folder screen allows automated batch conversion of files dropped into a monitored folder. Displays the current output format and OCR status.

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
them in an assets folder next to your output file. The output will
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
If an output file with the same name already exists in the output folder, this
option replaces it. If turned off, the tool will skip files that already exist
and leave the originals unchanged. Turn this on carefully if you want to
re-convert files you have already edited.
```

**Output Subfolder Structure**
```
Output Subfolder Structure:
Creates a separate folder for each converted document inside your output
location. Each folder contains the converted file, extracted assets, a
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
Controls how many files are converted at the same time. Auto uses the
recommended worker count based on your CPU cores and available RAM. Decrease
to 1 if you experience memory pressure on large files.
```

**Quality Preset**
```
Quality Preset:
Controls the tradeoff between conversion speed and output quality. Fast skips
OCR and advanced table detection. Balanced uses standard processing. Quality
enables all analysis engines for the most accurate results.
```

**OCR Engine**
```
OCR Engine:
Selects which text recognition engine processes scanned pages and images.
Auto picks the best available engine for your system. RapidOCR uses AI models
with GPU acceleration when available. Tesseract is a traditional engine that
works everywhere. Ensemble runs both engines and keeps the most confident
result for each word — slower but more accurate. Apple Vision is available
on macOS only and uses the built-in Neural Engine.
```

**Searchable PDF — Deskew**
```
Deskew:
Straightens pages that were scanned at a slight angle. Improves OCR accuracy
on tilted scans. Recommended for most scanned documents. Has minimal effect
on pages that are already straight.
```

**Searchable PDF — Clean Pages**
```
Clean Pages:
Removes speckles, noise, and scan artifacts from page images before OCR.
Can improve accuracy on dirty or degraded scans but may remove fine details
like thin lines or small dots. Off by default. Turn on for old or
low-quality scans.
```

**Searchable PDF — Force OCR**
```
Force OCR:
Re-runs OCR on every page, even pages that already contain selectable text.
Normally the tool skips pages with existing text. Use this when the existing
text layer is incorrect or was generated by a different OCR engine.
```

**Searchable PDF — Optimize**
```
Optimize:
Controls how much the output PDF is compressed. Level 0 does no optimization.
Level 1 applies lossless compression. Higher levels reduce file size further
but may slightly reduce image quality. Level 1 is recommended for most uses.
```

**Searchable PDF — PDF/A Compliance**
```
PDF/A Compliance:
Produces a PDF/A-compliant output file. PDF/A is an archival standard that
ensures the file can be opened reliably in the future. Some organizations
require PDF/A for long-term document storage. Off by default.
```

**Searchable PDF — Sidecar Text**
```
Sidecar Text:
Saves a plain text file alongside the Searchable PDF containing all OCR text
extracted from the document. Useful for indexing, search systems, or review
of OCR results without opening the PDF.
```

**Searchable PDF — AI-Ready from Sidecar**
```
AI-Ready from Sidecar:
Generates chunked JSONL output from the sidecar text for use with AI retrieval
systems and vector databases. Only available when Sidecar Text is enabled.
Each chunk includes source metadata and confidence data.
```

**Searchable PDF — Background Removal**
```
Background Removal:
Removes colored backgrounds and heavy noise from scanned pages before OCR.
Useful for documents scanned on colored paper or with visible stains. May
alter the appearance of the output PDF. Use with caution on documents where
background color is intentional.
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

The Settings screen is organized into collapsible sections. Each section has a clickable header with a chevron icon (▸ collapsed, ▾ expanded). Collapse state is persisted across sessions.

### Section Order

1. **CONVERSION** — (default: expanded)
   - Conversion Mode dropdown
   - Quality Preset dropdown

2. **CONTENT HANDLING** — (default: collapsed)
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
   - Auto Translate (on)
   - DXF SVG Preview (on)

3. **OCR** — (default: expanded)
   - OCR Engine dropdown: Auto, RapidOCR, Tesseract, Ensemble, Apple Vision (macOS only)
   - OCR Language dropdown

4. **OUTPUT** — (default: expanded)
   - Output Format dropdown: Markdown, JSON, HTML, Plain Text, AI-Ready Chunks, Searchable PDF
   - Markdown Flavor dropdown (visible only when Output Format is Markdown)
   - YAML Front Matter toggle (visible only when Output Format is Markdown)
   - Overwrite Existing toggle
   - Output Subfolder toggle

5. **SEARCHABLE PDF** — (visible only when Output Format is Searchable PDF)
   - Deskew toggle (on)
   - Clean Pages toggle (off)
   - Force OCR toggle (off)
   - Optimize Level dropdown: 0, 1, 2, 3 (default: 1)
   - PDF/A Compliance toggle (off)
   - Sidecar Text toggle (off)
   - AI-Ready from Sidecar toggle (off, visible only when Sidecar Text is on)
   - Background Removal toggle (off, with warning tooltip)

6. **PERFORMANCE** — (default: expanded)
   - Parallel Workers dropdown: 1, 2, 4, 8, 12, 16, Auto
   - Low Confidence Action dropdown

7. **POST-PROCESSING** — (default: collapsed)
   - Rules Profile dropdown
   - Edit Rules button

8. **RESET** — Reset to Defaults button

### Conditional Visibility
- Markdown Flavor and YAML Front Matter are only visible when Output Format is "Markdown"
- The entire SEARCHABLE PDF section is only visible when Output Format is "Searchable PDF"
- AI-Ready from Sidecar is only visible when Sidecar Text is enabled
- Apple Vision appears in the OCR Engine dropdown only on macOS

### Performance Info Card
A system information card is displayed at the bottom of the Settings screen (always visible, not collapsible):

```
┌─ SYSTEM ───────────────────────────────────┐
│  CPU: Intel i7-12700K (16 cores)           │
│  RAM: 32 GB                                │
│  GPU: NVIDIA RTX 3080 (10 GB VRAM)         │
│  Accelerator: CUDA                         │
│  Recommended workers: 4                    │
└────────────────────────────────────────────┘
```

Detected once at startup and cached. Also shown as a summary line in the About window.

Each setting has a tooltip that displays help text on hover.

## Results Screen Features

### Action Buttons
The Results screen includes three action buttons:
- **Preview Output** — Opens the preview window with syntax highlighting, search, spell check, confidence heatmap, and image zoom
- **Debug Info** — Opens a diagnostic window with engine info, confidence scores, warnings, and settings snapshot. Includes an Export Log button to save diagnostics to a text file.
- **Open Folder** — Opens the output folder in the system file manager

### Per-File Results List
The Results screen displays a scrollable per-file list showing each converted file with its content type badges. Each row contains the filename and its detected content badges.

### Mixed Content Badges
Each file in the Results list displays small badge indicators for detected content types:
- `[Text]` `[Tables]` `[Images]` `[OCR]` `[Scanned]`
- Color-coded by confidence: green (high), yellow (medium), red (low)
- Colorblind-accessible shapes accompany each badge: ▲ (high), ● (medium), ▼ (low)
- Derived from the conversion confidence report data

### Completion Notification
When a conversion finishes while the user is viewing a screen other than Conversion, the Results nav button flashes with the accent color for 2 seconds to draw attention without force-navigating away from the current screen. If the user is still on the Conversion screen, navigation switches to Results automatically.

## Preview Window Features
The preview window provides rich output review:
- Syntax highlighting for headings, code blocks, inline code, blockquotes, links, tables, lists, horizontal rules, image references, and YAML front matter
- Inline image thumbnails with click-to-zoom full-size viewer
- Source pages panel with rendered PDF page thumbnails
- Source info panel with file metadata and per-dimension confidence breakdown
- Find and Replace bar (Ctrl+F) with regex support, match navigation, and Replace All
- Copy Markdown (raw) and Copy Rich (formatted HTML for Word/Docs/email)
- Spell check toggle with offline dictionary (misspelled words underlined in red)
- Confidence heatmap overlay — color-codes text, tables, and images by extraction confidence

### Preview Toolbar Organization
The preview toolbar is divided into three visually separated zones:
1. **File selector** — dropdown to switch between converted files
2. **Clipboard** — Copy Markdown and Copy Rich buttons
3. **Analysis** — Heatmap toggle, Spell Check toggle

A status bar at the bottom shows keyboard shortcut hints.

## Watch Folder Screen
The Watch Folder screen supports automated batch conversion:
- Folder selector for input and output directories
- Start/Stop monitoring button
- Progress bar and activity log
- Format indicator showing the current output format (e.g., "Output: Searchable PDF")
- When format is Searchable PDF, shows "OCR will be applied to incoming files"

## Output Format Options

The Output Format dropdown includes:
- Markdown (.md)
- JSON (.json)
- HTML (.html)
- Plain Text (.txt)
- AI-Ready Chunks (.jsonl)
- Searchable PDF (.pdf)

AI-Ready Chunks produces JSONL output designed for AI retrieval systems and vector databases. Each line is a self-contained text chunk with metadata about its source, section, and position.

Searchable PDF adds an invisible OCR text layer to scanned or image-based PDFs, enabling full-text search while preserving the original visual appearance.

## Keyboard Shortcuts

The GUI provides keyboard shortcuts for common actions:

| Shortcut | Context | Action |
|----------|---------|--------|
| Ctrl+Enter | Home screen | Start conversion (when files and output are selected) |
| Escape | Conversion screen | Cancel active conversion |

Shortcuts only fire when the focus widget is in the main application window (not inside dialog windows or Toplevel windows like Preview).
