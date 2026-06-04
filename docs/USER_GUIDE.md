<!-- Source for the installer's "Quick Start Guide" (Guide.html).
     Curated for end users — keep it friendly and non-technical.
     Build with: python installer/make_guide_html.py -->

## Welcome to Markwell

Markwell turns your documents — PDFs, Word files, spreadsheets, images, scans, and more — into clean, organized **Markdown** (and several other formats) that's easy to read, search, and feed to AI tools or a knowledgebase.

Everything happens **on your computer**. Your files are never uploaded anywhere.

<div class="tip"><strong>New here?</strong> You don't need to change any settings to get started — the defaults work well for most documents. Just add files, pick an output folder, and click Convert.</div>

---

## Get started in 4 steps

1. **Add your files.** On the **Home** screen, click *Add Files* or drag documents into the window.
2. **Choose where output goes.** Pick an output folder for your converted files.
3. **Adjust settings (optional).** Open **Settings** only if you want to change the output format or fine-tune things.
4. **Convert and review.** Click *Convert*, watch progress, then review the results and open your files.

![The Home screen — add files and choose an output folder](assets/guide/home.png)

---

## The five screens

| Screen | What it's for |
|--------|---------------|
| **Home** | Add files and choose your output folder |
| **Settings** | Change the output format and conversion options |
| **Conversion** | Live progress, current file, and elapsed time |
| **Results** | Confidence scores, per-file badges, and buttons to preview or open output |
| **Watch Folder** | Automatically convert any file dropped into a folder you choose |

---

## Choosing an output format

Set this under **Settings → Output → Output Format**. Markdown is the default.

| Format | Best for |
|--------|----------|
| **Markdown** (.md) | Reading, editing, AI upload, knowledgebases |
| **JSON** (.json) | Feeding structured data into scripts or pipelines |
| **HTML** (.html) | A self-contained page you can open in any browser |
| **Plain Text** (.txt) | Simple text with no formatting |
| **AI-Ready Chunks** (.jsonl) | Vector databases and AI retrieval systems |
| **Searchable PDF** (.pdf) | Making a scanned PDF full-text searchable while keeping its look |

---

## Key settings, in plain language

Every setting has a hover tooltip in the app. These are the ones most worth knowing:

- **Conversion Mode** — *Auto-detect* figures out the best method. Use *OCR* only for scans or images where text can't be selected.
- **Quality Preset** — *Fast* is quickest (skips deep analysis), *Quality* is the most accurate. *Balanced* sits in between.
- **Preserve Images** — saves pictures and diagrams alongside your Markdown and links to them.
- **Preserve Page Numbers** — adds page markers so you can cross-reference the original.
- **Rebuild Table of Contents** — recreates a clickable contents list at the top.
- **OCR Engine** — leave on *Auto*. *Ensemble* is the most accurate for tough scans (a little slower).

![The Settings screen — collapsible sections with a tooltip for every option](assets/guide/settings.png)

---

## Scanned documents & images (OCR)

When a page is a scan or an image, the tool reads the text using **OCR** (Optical Character Recognition). This works **out of the box** — the recognition engines are built in, nothing to install.

- **RapidOCR** — the fast, accurate default, with automatic graphics-card acceleration when available.
- **Tesseract** — a reliable fallback, bundled with the app.
- **Ensemble** — runs both and keeps the best result for each word. Most accurate; choose it for difficult scans.

---

## Searchable PDF (one free add-on)

The **Searchable PDF** format adds an invisible text layer to a scanned PDF so you can search and copy from it — while it still looks exactly the same.

<div class="note"><strong>One-time setup:</strong> Searchable PDF uses a free tool called <strong>Ghostscript</strong> that isn't bundled with the app. The first time you choose Searchable PDF, the app shows a window with a button to download it. Install it once, click <em>Re-check</em>, and you're set. Every other feature works without it.</div>

---

## Understanding confidence

After each conversion, the tool tells you how sure it is — so you know where to double-check. Each file shows badges on the **Results** screen, colored and shaped for clarity:

<p>
<span class="badge high">▲ High</span> looks great &nbsp;
<span class="badge med">● Medium</span> worth a glance &nbsp;
<span class="badge low">▼ Low</span> review recommended
</p>

Badges cover the content types found in each file — **Text**, **Tables**, **Images**, **OCR**, and **Scanned** — so you can tell at a glance what was detected and how well it came through.

![The Results screen — per-file confidence badges](assets/guide/results.png)

---

## Reviewing your output

Click **Preview Output** on the Results screen to open the review window:

- **Syntax highlighting** for headings, tables, code, links, and more
- **Inline image thumbnails** you can click to zoom
- **Confidence heatmap** — color-codes the text by how confident the tool is
- **Spell check** — underlines likely OCR mistakes
- **Find & Replace** (Ctrl+F) with regex support
- **Copy** as Markdown, or as rich text to paste into Word, Google Docs, or email

![The Preview window — rich rendering with review tools](assets/guide/preview.png)

---

## Watch Folder (hands-off conversion)

On the **Watch Folder** screen, pick a folder to monitor and a folder for output, then click *Start*. Any file you drop into the watched folder is converted automatically using your current settings. Great for ongoing batches.

---

## Licensing

- **Free tier:** 10 conversions, so you can evaluate the tool.
- **Licensed:** unlimited conversions with a license key.

License keys are checked **offline** — no internet needed. Enter yours in the **About** window. Visit [darksquare.dev](https://darksquare.dev) to purchase.

---

## Your privacy

Everything is processed locally. No documents, data, or usage information ever leave your computer. The only time the app uses the internet is a one-time download of AI models on first run (after that it works fully offline).

---

## Need help?

- Website: [darksquare.dev](https://darksquare.dev)
- Email: **darksquare.ai@gmail.com**
