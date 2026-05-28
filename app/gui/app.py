import math
import os
import re
import sys
import time
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox, simpledialog
from . import theme as themes
from .tooltip import Tooltip
from .widgets import (PillButton, ToggleSwitch, GlassScrollbar, GlassDropdown,
                      PillProgressBar, _draw_circle)
import config.settings as _cfg_mod
import engine.converter as _converter_mod
import engine.watch_folder as _watch_mod
import engine.rules_engine as _rules_mod
import engine.validation as _validation_mod
import engine.license_manager as _license_mod
import engine.system_info as _sysinfo_mod

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False

SCREENS = ["Home", "Settings", "Conversion", "Results", "Watch"]

ICONS = {
    "Home":       "⌂",
    "Settings":   "⚙",
    "Conversion": "▶",
    "Results":    "✓",
    "Watch":      "◉",
}

_SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".rtf", ".xlsx", ".xls", ".csv",
                   ".pptx", ".epub", ".dxf", ".html", ".htm",
                   ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp",
                   ".webp", ".gif"}

_FILETYPES = [
    ("Supported files",  "*.pdf *.docx *.doc *.rtf *.xlsx *.xls *.csv *.pptx *.epub *.dxf *.html *.htm *.png *.jpg *.jpeg *.tiff *.tif *.bmp *.webp *.gif"),
    ("PDF files",        "*.pdf"),
    ("Word documents",   "*.docx *.doc *.rtf"),
    ("PowerPoint files", "*.pptx"),
    ("EPUB e-books",     "*.epub"),
    ("HTML files",       "*.html *.htm"),
    ("DXF drawings",     "*.dxf"),
    ("Excel files",      "*.xlsx *.xls"),
    ("CSV files",        "*.csv"),
    ("Image files",      "*.png *.jpg *.jpeg *.tiff *.tif *.bmp *.webp *.gif"),
    ("All files",        "*.*"),
]

_FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else (
    "Helvetica Neue" if sys.platform == "darwin" else "sans-serif")

_FONT_TITLE    = (_FONT_FAMILY, 13, "bold")
_FONT_HEADING  = (_FONT_FAMILY, 22, "bold")
_FONT_BODY     = (_FONT_FAMILY, 13)
_FONT_NAV      = (_FONT_FAMILY, 12)
_FONT_NAV_ACT  = (_FONT_FAMILY, 12, "bold")
_FONT_SMALL    = (_FONT_FAMILY, 11)
_FONT_BTN      = (_FONT_FAMILY, 13, "bold")
_FONT_SECTION  = (_FONT_FAMILY, 10, "bold")
_FONT_MONO     = ("Consolas" if sys.platform == "win32" else
                  "Menlo" if sys.platform == "darwin" else "monospace")

_CONF_AREAS = [
    "Overall",
    "Text extraction",
    "Table structure",
    "Image extraction",
    "Image placement",
    "Document order",
]

_TIPS = {
    "conversion_mode": (
        "Controls how the tool reads and converts your document. Standard mode works for most "
        "documents. OCR mode is needed for scanned documents or images where the text cannot be "
        "selected. Using OCR on a document that already has selectable text may reduce quality."
    ),
    "preserve_images": (
        "Extracts images, diagrams, and drawings from the source document and saves them in an "
        "assets folder next to your Markdown file. The Markdown output will include links to these "
        "images. Turn this off if you only need the text content."
    ),
    "preserve_page_numbers": (
        "Inserts a page marker at each page boundary in the Markdown output. This lets you "
        "cross-reference the Markdown file against the original document by page number. "
        "Recommended for textbooks, manuals, and any document where page references matter."
    ),
    "rebuild_toc": (
        "If your document has a table of contents, this option extracts it and places a navigable "
        "version at the top of the Markdown output. Each entry links directly to the correct page "
        "in the document. Only available when a table of contents or heading structure is detected."
    ),
    "ocr_language": (
        "Sets the language the OCR engine uses when reading text from scanned pages or images. "
        "Choose the language that matches your document. Using the wrong language may produce "
        "garbled or incorrect text. This setting only affects files that require OCR processing."
    ),
    "overwrite_existing": (
        "If a Markdown file with the same name already exists in the output folder, this option "
        "replaces it. If turned off, the tool will skip files that already exist and leave the "
        "originals unchanged. Turn this on carefully if you want to re-convert files you have "
        "already edited."
    ),
    "output_subfolder": (
        "Creates a separate folder for each converted document inside your output location. Each "
        "folder contains the Markdown file, extracted assets, a confidence report, and a conversion "
        "log. Turning this off places all output files directly in the output folder, which can "
        "become difficult to manage with multiple documents."
    ),
    "low_confidence_action": (
        "Controls what happens when the tool is not confident about a conversion result, such as "
        "unclear OCR text or a table that could not be read cleanly. 'Ask me' will pause and show "
        "you a choice. 'Keep and flag' will include the uncertain content and mark it for review. "
        "'Skip' will leave it out entirely."
    ),
    "output_format": (
        "Choose the file format for your converted output. Markdown is the default and works "
        "best for human reading and AI upload. JSON produces structured data that can be "
        "processed by scripts, APIs, and AI pipelines. HTML creates a self-contained web page "
        "viewable in any browser. Plain Text strips all formatting for simple reading or "
        "search indexing. Searchable PDF adds an invisible OCR text layer to scanned PDFs "
        "so they become full-text searchable (PDF input only)."
    ),
    "markdown_flavor": (
        "Controls which Markdown dialect is used for the output file. GFM (GitHub Flavored "
        "Markdown) is the most widely compatible and works in GitHub, VS Code, and most "
        "viewers. Obsidian mode uses [[wikilinks]], adds tags in front matter, and formats "
        "internal links for Obsidian vaults. Pandoc mode uses extended syntax with footnote "
        "definitions and cross-reference support for academic workflows."
    ),
    "yaml_front_matter": (
        "Adds a YAML metadata block at the top of the Markdown file containing the document "
        "title, source filename, conversion date, engine used, and confidence level. This "
        "metadata is used by tools like Obsidian, Hugo, Jekyll, and MkDocs for organizing "
        "and displaying documents. Recommended for knowledge base workflows."
    ),
    "embed_images": (
        "Encodes images directly inside the Markdown file. The output is fully self-contained "
        "— no separate assets folder needed, images appear in their original position.\n\n"
        "⚠ Raw text editors (Notepad, WordPad) will show base64 data as walls of characters. "
        "This is normal — the file is not broken. Open it in a Markdown viewer to see images correctly.\n\n"
        "Notepad++: Plugins → Plugins Admin → search 'MarkdownViewer' → Install → restart "
        "Notepad++ → open file → click the Markdown icon in the toolbar.\n\n"
        "Free alternatives: VS Code (Ctrl+Shift+V for preview), Obsidian, Typora.\n\n"
        "Turn this off to save images as separate files in an assets folder instead "
        "(smaller .md file, but assets folder must stay alongside it)."
    ),
    "remove_headers_footers": (
        "Removes repeated headers and footers that appear on every page. "
        "This prevents the same text from cluttering your Markdown output. "
        "Turn this off if headers or footers contain important content you want to keep."
    ),
    "skip_blank_pages": (
        "Skips pages that contain little or no meaningful text. "
        "This removes empty separator pages and blank backs of double-sided scans. "
        "Turn this off if blank pages are intentional and should be preserved."
    ),
    "strip_line_numbers": (
        "Removes line numbers that appear in the margins of legal documents, "
        "code listings, or academic papers. Off by default because most documents "
        "do not have line numbers. Turn this on only if your source has numbered lines."
    ),
    "detect_code_blocks": (
        "Identifies sections of source code or terminal output and wraps them in "
        "code blocks in the Markdown output. Uses font changes and indentation patterns "
        "to distinguish code from normal text. Recommended for technical documents."
    ),
    "detect_footnotes": (
        "Finds footnotes and endnotes in the document and converts them into "
        "Markdown footnote syntax. Links each reference number to its footnote text "
        "at the bottom of the section. Recommended for academic and legal documents."
    ),
    "detect_equations": (
        "Detects mathematical equations, formulas, and expressions and preserves them "
        "using LaTeX notation in the Markdown output. Looks for Greek letters, math "
        "symbols, and formula patterns. Recommended for scientific and engineering documents."
    ),
    "parallel_workers": (
        "Controls how many files are converted at the same time. Higher values "
        "convert batches faster but use more memory and CPU. Auto uses the "
        "recommended worker count shown in the System card at the bottom of "
        "this page, based on your CPU cores and available RAM."
    ),
    "quality_preset": (
        "Controls the tradeoff between conversion speed and output quality. "
        "Fast skips OCR and advanced table detection for maximum speed. "
        "Balanced uses standard processing at medium OCR resolution. "
        "Quality enables all analysis engines at maximum OCR resolution "
        "for the most accurate results."
    ),
    "auto_translate": (
        "Automatically translates non-English text found in images and "
        "engineering drawings to English using offline translation (Argos "
        "Translate). The original text is always preserved alongside the "
        "translation in a side-by-side table. Turn this off if you only "
        "need the original language text, or to speed up conversion."
    ),
    "dxf_svg_preview": (
        "Generates a visual SVG preview of DXF engineering drawings and "
        "embeds it in the Markdown output. The preview shows the full "
        "drawing layout including geometry, dimensions, and annotations. "
        "Turn this off to speed up conversion of very complex drawings, "
        "or if you only need the extracted text and metadata."
    ),
    "ocr_engine": (
        "Select the preferred OCR engine for text extraction from images "
        "and scanned pages. Auto picks the best available engine for your "
        "system. RapidOCR uses AI models with GPU acceleration when "
        "available. Tesseract is a traditional engine that works "
        "everywhere. Ensemble runs both engines and keeps the most "
        "confident result for each word — slower but more accurate."
    ),
    "spdf_deskew": (
        "Straightens pages that were scanned at a slight angle. Improves OCR accuracy "
        "on tilted scans. Recommended for most scanned documents. Has minimal effect "
        "on pages that are already straight."
    ),
    "spdf_clean": (
        "Removes speckles, noise, and scan artifacts from page images before OCR. "
        "Can improve accuracy on dirty or degraded scans but may remove fine details "
        "like thin lines or small dots. Off by default. Turn on for old or "
        "low-quality scans."
    ),
    "spdf_force_ocr": (
        "Re-runs OCR on every page, even pages that already contain selectable text. "
        "Normally the tool skips pages with existing text. Use this when the existing "
        "text layer is incorrect or was generated by a different OCR engine."
    ),
    "spdf_optimize": (
        "Controls how much the output PDF is compressed. Level 0 does no optimization. "
        "Level 1 applies lossless compression. Higher levels reduce file size further "
        "but may slightly reduce image quality. Level 1 is recommended for most uses."
    ),
    "spdf_pdfa": (
        "Produces a PDF/A-compliant output file. PDF/A is an archival standard that "
        "ensures the file can be opened reliably in the future. Some organizations "
        "require PDF/A for long-term document storage. Off by default."
    ),
    "spdf_sidecar": (
        "Saves a plain text file alongside the Searchable PDF containing all OCR text "
        "extracted from the document. Useful for indexing, search systems, or review "
        "of OCR results without opening the PDF."
    ),
    "spdf_rag_sidecar": (
        "Generates chunked JSONL output from the sidecar text for use with AI retrieval "
        "systems and vector databases. Only available when Sidecar Text is enabled. "
        "Each chunk includes source metadata and confidence data."
    ),
    "spdf_bg_removal": (
        "Removes colored backgrounds and heavy noise from scanned pages before OCR. "
        "Useful for documents scanned on colored paper or with visible stains. May "
        "alter the appearance of the output PDF. Use with caution on documents where "
        "background color is intentional."
    ),
}


class App:
    def __init__(self):
        self.root = TkinterDnD.Tk() if _HAS_DND else tk.Tk()

        # ── High-fidelity DPI scaling ────────────────────────
        # With per-monitor DPI awareness (set in main.py), tkinter
        # auto-detects display DPI for font/widget scaling.  We read the
        # real system DPI so we can scale window geometry, sidebar width,
        # and custom widget dimensions to match.
        self._is_windows = (sys.platform == "win32")
        if self._is_windows:
            try:
                import ctypes
                _sys_dpi = ctypes.windll.user32.GetDpiForSystem()
                self._dpi = _sys_dpi / 96.0
            except Exception:
                self._dpi = 1.0
        else:
            # Cross-platform fallback: Tk's 'scaling' reports pixels per point.
            # 1 point = 1/72 inch; at 96 DPI the factor is ~1.333.
            try:
                _tk_scaling = self.root.tk.call('tk', 'scaling')
                self._dpi = float(_tk_scaling) / 1.333333
                if self._dpi < 0.5 or self._dpi > 5.0:
                    self._dpi = 1.0
            except Exception:
                self._dpi = 1.0

        from .widgets import set_dpi_scale
        set_dpi_scale(self._dpi)

        self.root.title("Document to Markdown Converter")
        self.root.geometry(f"{int(960 * self._dpi)}x{int(640 * self._dpi)}")
        self.root.minsize(int(720 * self._dpi), int(500 * self._dpi))

        # Window icon
        _icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets", "app_icon.ico")
        if not os.path.isfile(_icon_path):
            # Fallback: look relative to project root
            _icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "assets", "app_icon.ico")
        if os.path.isfile(_icon_path):
            try:
                self.root.iconbitmap(_icon_path)
            except Exception:
                pass

        # Load config first — theme preference is stored here
        self._cfg = _cfg_mod.load()

        theme_pref = self._cfg.get("theme", "system")
        if theme_pref == "system":
            self._dark = self._detect_system_dark_mode()
        else:
            self._dark = (theme_pref == "dark")
        self._t = themes.DARK if self._dark else themes.LIGHT
        self._nav_btns: dict[str, tk.Button] = {}
        self._frames:   dict[str, tk.Frame]  = {}
        self._current   = "Home"

        # Home screen state
        self._selected_files: list[str] = []
        self._file_aliases:   dict[str, str] = {}   # path → custom output name
        self._file_page_ranges: dict[str, list[int]] = {}  # path → selected pages
        self._output_path: str = self._cfg.get("last_output_folder", "")

        # Settings state (config already loaded above)
        self._setting_vars:        dict = {}
        self._settings_section_hdrs: list[tk.Label]  = []
        self._settings_dividers:     list[tk.Frame]  = []
        self._settings_info_labels:  list[tk.Label]  = []
        self._settings_name_labels:  list[tk.Label]  = []
        self._settings_toggles:   list[tk.Widget] = []
        self._settings_dropdowns:    list[tk.Widget] = []
        self._settings_default_lbls: list[tk.Label]  = []
        self._collapse_sections: dict = {}
        self._current_section_id: str = ""
        self._markdown_only_widgets: list[tk.Widget] = []
        self._sidecar_only_widgets: list[tk.Widget] = []
        self._sysinfo_labels: list[tk.Label] = []
        self._sysinfo_card: "tk.Frame | None" = None

        # Per-file results list (Item 1: badges)
        self._results_files_inner: "tk.Frame | None" = None
        self._results_files_canvas: "tk.Canvas | None" = None

        # Elapsed timer state (Item 3)
        self._elapsed_start: float = 0.0
        self._elapsed_after_id = None
        # Results nav flash state (Item 5)
        self._results_notify_id = None
        # Watch folder flash state
        self._watch_notify_id = None
        # Batch result for re-populating results screen
        self._last_batch_result = None
        # Guard flag for resetting defaults
        self._resetting_defaults = False

        # Custom widget tracking (filled by _build_* methods, themed in _apply_theme)
        self._primary_pills:    list = []   # filled accent PillButtons
        self._secondary_pills:  list = []   # outline PillButtons
        self._glass_scrollbars: list = []   # GlassScrollbar instances

        # Engine state
        self._active_job: "Optional[_converter_mod.ConversionJob]" = None
        self._last_output_root: str = ""

        # Watch folder state
        self._watcher: "Optional[_watch_mod.FolderWatcher]" = None
        self._watch_input_path: str = ""
        self._watch_output_path: str = ""

        # Centralized scroll target to avoid bind_all/unbind_all conflicts.
        # Each scrollable area sets this on <Enter>; the single global
        # mousewheel handler scrolls whichever canvas is active.
        self._scroll_target = None

        # ── Global error handler — show crashes instead of dying silently ─
        def _on_tk_error(exc_type, exc_value, exc_tb):
            import traceback as _tb
            msg = "".join(_tb.format_exception(exc_type, exc_value, exc_tb))
            # Log to stderr (visible when console isn't hidden)
            sys.stderr.write(f"Unhandled error:\n{msg}\n")
            # Also log to the app log file
            try:
                from engine.logger import AppLogger
                AppLogger().error(f"GUI callback error: {msg}")
            except Exception:
                pass
            # Show a non-blocking messagebox so the app can continue
            try:
                messagebox.showerror(
                    "Unexpected Error",
                    f"An error occurred:\n\n{exc_value}\n\n"
                    "The error has been logged. The app will try to continue.",
                )
            except Exception:
                pass

        self.root.report_callback_exception = _on_tk_error

        # ── Global mousewheel: scroll whichever canvas owns focus ──
        def _global_mousewheel(e):
            target = self._scroll_target
            if target:
                target.yview_scroll(self._scroll_units(e), "units")
        self.root.bind_all("<MouseWheel>", _global_mousewheel)
        # Linux uses Button-4 / Button-5 for scroll events
        self.root.bind_all("<Button-4>",
                           lambda e: self._scroll_target.yview_scroll(-3, "units")
                           if self._scroll_target else None)
        self.root.bind_all("<Button-5>",
                           lambda e: self._scroll_target.yview_scroll(3, "units")
                           if self._scroll_target else None)

        self._build_layout()
        self._apply_theme()
        self._show("Home")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Keyboard shortcuts ────────────────────────────────
        self.root.bind_all("<Escape>", self._shortcut_escape)
        self.root.bind_all("<Control-Return>", self._shortcut_ctrl_enter)

        # Non-blocking startup checks (run after mainloop starts)
        self.root.after(500, self._startup_checks)

    # ── Layout ──────────────────────────────────────────────

    def _build_layout(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=0)  # sidebar
        self.root.grid_columnconfigure(1, weight=0)  # 1px border
        self.root.grid_columnconfigure(2, weight=1)  # content

        # Use clam so any remaining ttk widgets get flat styling
        self._ttk_style = ttk.Style()
        self._ttk_style.theme_use('clam')

        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        self._sidebar = tk.Frame(self.root, width=int(196 * self._dpi))
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._sidebar.grid_columnconfigure(0, weight=1)
        self._sidebar.grid_rowconfigure(9, weight=1)

        self._lbl_title = tk.Label(
            self._sidebar,
            text="Doc → Markdown",
            font=_FONT_TITLE,
            anchor="w",
            padx=16,
            pady=18,
        )
        self._lbl_title.grid(row=0, column=0, sticky="ew")

        self._div_top = tk.Frame(self._sidebar, height=1)
        self._div_top.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        for idx, name in enumerate(SCREENS):
            btn = tk.Button(
                self._sidebar,
                text=f"  {ICONS[name]}   {name}",
                font=_FONT_NAV,
                anchor="w",
                bd=0,
                relief="flat",
                padx=8,
                pady=9,
                cursor="hand2",
                command=lambda n=name: self._show(n),
            )
            btn.grid(row=idx + 2, column=0, sticky="ew", padx=8, pady=2)
            self._nav_btns[name] = btn

        self._sidebar_spacer = tk.Frame(self._sidebar)
        self._sidebar_spacer.grid(row=9, column=0, sticky="nsew")

        # About / License button
        self._about_btn_frame = tk.Frame(self._sidebar)
        self._about_btn_frame.grid(row=10, column=0, sticky="ew", padx=10, pady=(6, 2))

        self._about_btn = tk.Label(
            self._about_btn_frame, text="",
            font=(_FONT_FAMILY, 9), cursor="hand2",
            padx=10, pady=6, anchor="center",
        )
        self._about_btn.pack(fill="x")
        self._about_btn.bind("<Button-1>", lambda _: self._show_about_window())
        self._about_btn.bind("<Enter>", lambda _: self._about_btn.config(
            bg=self._t["nav_hover_bg"]))
        self._about_btn.bind("<Leave>", lambda _: self._about_btn.config(
            bg=self._t["sidebar_bg"]))

        self._license_status_lbl = self._about_btn  # alias for update method
        self._update_license_status()

        self._div_bot = tk.Frame(self._sidebar, height=1)
        self._div_bot.grid(row=11, column=0, sticky="ew", padx=12, pady=(0, 4))

        # Theme toggle: [sun] [toggle] [moon]
        self._theme_row = tk.Frame(self._sidebar)
        self._theme_row.grid(row=12, column=0, sticky="ew", padx=8, pady=(0, 14))
        self._theme_inner = tk.Frame(self._theme_row)
        self._theme_inner.pack(anchor="center")

        _icon_s = round(32 * self._dpi)
        self._sun_canvas = tk.Canvas(
            self._theme_inner, width=_icon_s, height=_icon_s,
            highlightthickness=0, bd=0)
        self._sun_canvas.pack(side="left", padx=(0, 6))

        self._theme_dark_var = tk.BooleanVar(value=self._dark)
        self._theme_toggle = ToggleSwitch(
            self._theme_inner, variable=self._theme_dark_var,
            command=self._toggle_theme)
        self._theme_toggle.pack(side="left")

        self._moon_canvas = tk.Canvas(
            self._theme_inner, width=_icon_s, height=_icon_s,
            highlightthickness=0, bd=0)
        self._moon_canvas.pack(side="left", padx=(6, 0))

        self._border_line = tk.Frame(self.root, width=1)
        self._border_line.grid(row=0, column=1, sticky="nsew")

    def _build_content(self):
        self._content = tk.Frame(self.root)
        self._content.grid(row=0, column=2, sticky="nsew")
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

        self._build_home()
        self._build_settings()
        self._build_conversion()
        self._build_results()
        self._build_watch()

        # Initial format label on Watch screen (needs setting_vars from _build_settings)
        self._update_watch_format()

    # ── Screens ─────────────────────────────────────────────

    def _new_screen(self, name: str) -> tk.Frame:
        f = tk.Frame(self._content)
        f.grid(row=0, column=0, sticky="nsew")
        f.grid_columnconfigure(0, weight=1)
        self._frames[name] = f
        return f

    def _heading(self, parent, title, subtitle, title_row=0, sub_row=1):
        tk.Label(parent, text=title, font=_FONT_HEADING, anchor="w").grid(
            row=title_row, column=0, sticky="w", padx=32, pady=(28, 2))
        tk.Label(parent, text=subtitle, font=_FONT_BODY, anchor="w",
                 wraplength=560, justify="left").grid(
            row=sub_row, column=0, sticky="w", padx=32, pady=(0, 20))

    def _build_home(self):
        f = self._new_screen("Home")
        # rows: 0=title, 1=subtitle, 2=toolbar, 3=file list, 4=count, 5=output, 6=start
        f.grid_rowconfigure(3, weight=1)

        self._heading(f, "Home", "Select files or a folder and choose an output location.")

        # ── Toolbar ─────────────────────────────────────────
        self._home_toolbar = tk.Frame(f)
        self._home_toolbar.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 4))
        self._home_toolbar.grid_columnconfigure(3, weight=1)  # spacer col

        self._btn_add_files = PillButton(
            self._home_toolbar,
            text="+ Add Files",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._pick_files,
        )
        self._btn_add_files.grid(row=0, column=0, padx=(0, 6))
        self._secondary_pills.append(self._btn_add_files)

        self._btn_add_folder = PillButton(
            self._home_toolbar,
            text="+ Add Folder",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._pick_folder_input,
        )
        self._btn_add_folder.grid(row=0, column=1, padx=(0, 6))
        self._secondary_pills.append(self._btn_add_folder)

        self._btn_rename = PillButton(
            self._home_toolbar,
            text="Rename…",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            state="disabled",
            command=self._rename_selected_file,
        )
        self._btn_rename.grid(row=0, column=2, padx=(0, 6))
        self._secondary_pills.append(self._btn_rename)

        # spacer at column 3

        self._btn_clear = PillButton(
            self._home_toolbar,
            text="Clear All",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._clear_files,
        )
        self._btn_clear.grid(row=0, column=4)
        self._secondary_pills.append(self._btn_clear)

        # ── File list ────────────────────────────────────────
        self._file_list_frame = tk.Frame(f, highlightthickness=1)
        self._file_list_frame.grid(row=3, column=0, sticky="nsew", padx=32, pady=(0, 2))
        self._file_list_frame.grid_rowconfigure(0, weight=1)
        self._file_list_frame.grid_columnconfigure(0, weight=1)
        self._file_list_frame.grid_propagate(True)

        # Empty state label (shown when no files are selected)
        self._lbl_empty = tk.Label(
            self._file_list_frame,
            text="No files selected.\nDrag files here, or use '+ Add Files' / '+ Add Folder'.",
            font=_FONT_SMALL,
            justify="center",
        )
        self._lbl_empty.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=32)

        # Listbox + scrollbar (hidden until files are added)
        self._file_listbox = tk.Listbox(
            self._file_list_frame,
            selectmode=tk.EXTENDED,
            bd=0,
            relief="flat",
            activestyle="none",
            font=_FONT_SMALL,
            highlightthickness=0,
        )
        self._file_listbox.bind("<Button-3>", self._on_listbox_right_click)
        self._file_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)
        self._file_scrollbar = GlassScrollbar(
            self._file_list_frame,
            orient="vertical",
            command=self._file_listbox.yview,
        )
        self._glass_scrollbars.append(self._file_scrollbar)
        self._file_listbox.config(yscrollcommand=self._file_scrollbar.set)
        self._bind_scroll(self._file_listbox)

        # ── File count ───────────────────────────────────────
        self._lbl_file_count = tk.Label(f, text="0 files selected", font=_FONT_SMALL, anchor="w")
        self._lbl_file_count.grid(row=4, column=0, sticky="w", padx=32, pady=(2, 10))

        # ── Output folder row ────────────────────────────────
        self._home_out_row = tk.Frame(f)
        self._home_out_row.grid(row=5, column=0, sticky="ew", padx=32, pady=(0, 8))
        self._home_out_row.grid_columnconfigure(0, weight=1)

        self._out_path_frame = tk.Frame(self._home_out_row, highlightthickness=1)
        self._out_path_frame.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._out_path_frame.grid_columnconfigure(0, weight=1)

        self._lbl_output_path = tk.Label(
            self._out_path_frame,
            text=self._output_path if self._output_path else "No output folder selected",
            font=_FONT_SMALL,
            anchor="w",
            padx=10,
            pady=6,
        )
        self._lbl_output_path.grid(row=0, column=0, sticky="ew")

        self._btn_browse = PillButton(
            self._home_out_row,
            text="Browse…",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._pick_output_folder,
        )
        self._btn_browse.grid(row=0, column=1)
        self._secondary_pills.append(self._btn_browse)

        # ── Start button ─────────────────────────────────────
        self._btn_start = PillButton(
            f,
            text="Start Conversion",
            font=_FONT_BTN,
            style="primary",
            padx=26, pady=10,
            state="disabled",
            command=self._on_start,
        )
        self._btn_start.grid(row=6, column=0, sticky="w", padx=32, pady=(0, 28))
        self._primary_pills.append(self._btn_start)

        # ── Drag and drop ────────────────────────────────────
        if _HAS_DND:
            self._file_list_frame.drop_target_register(DND_FILES)
            self._file_list_frame.dnd_bind("<<DropEnter>>", self._on_drop_enter)
            self._file_list_frame.dnd_bind("<<DropLeave>>", self._on_drop_leave)
            self._file_list_frame.dnd_bind("<<Drop>>", self._on_drop)

    def _build_settings(self):
        f = self._new_screen("Settings")
        f.grid_rowconfigure(2, weight=1)

        self._heading(
            f, "Settings",
            "Configure conversion mode, OCR language, image handling, and output options.",
        )

        # ── Build tk.Vars from loaded config ─────────────────
        self._setting_vars = {
            "conversion_mode":        tk.StringVar(value=self._cfg["conversion_mode"]),
            "preserve_images":        tk.BooleanVar(value=self._cfg["preserve_images"]),
            "preserve_page_numbers":  tk.BooleanVar(value=self._cfg["preserve_page_numbers"]),
            "rebuild_toc":            tk.BooleanVar(value=self._cfg["rebuild_toc"]),
            "embed_images":           tk.BooleanVar(value=self._cfg["embed_images"]),
            "remove_headers_footers": tk.BooleanVar(value=self._cfg["remove_headers_footers"]),
            "skip_blank_pages":       tk.BooleanVar(value=self._cfg["skip_blank_pages"]),
            "strip_line_numbers":     tk.BooleanVar(value=self._cfg["strip_line_numbers"]),
            "detect_code_blocks":     tk.BooleanVar(value=self._cfg["detect_code_blocks"]),
            "detect_footnotes":       tk.BooleanVar(value=self._cfg["detect_footnotes"]),
            "detect_equations":       tk.BooleanVar(value=self._cfg["detect_equations"]),
            "parallel_workers":       tk.StringVar(value=self._cfg["parallel_workers"]),
            "quality_preset":         tk.StringVar(value=self._cfg["quality_preset"]),
            "ocr_language":           tk.StringVar(value=self._cfg["ocr_language"]),
            "output_format":          tk.StringVar(value=self._cfg["output_format"]),
            "markdown_flavor":        tk.StringVar(value=self._cfg["markdown_flavor"]),
            "yaml_front_matter":      tk.BooleanVar(value=self._cfg["yaml_front_matter"]),
            "overwrite_existing":     tk.BooleanVar(value=self._cfg["overwrite_existing"]),
            "output_subfolder":       tk.BooleanVar(value=self._cfg["output_subfolder"]),
            "low_confidence_action":  tk.StringVar(value=self._cfg["low_confidence_action"]),
            "auto_translate":         tk.BooleanVar(value=self._cfg["auto_translate"]),
            "dxf_svg_preview":        tk.BooleanVar(value=self._cfg["dxf_svg_preview"]),
            "ocr_engine":             tk.StringVar(value=self._cfg["ocr_engine"]),
            "rules_profile":          tk.StringVar(value=self._cfg.get("rules_profile", "None")),
            "spdf_deskew":            tk.BooleanVar(value=self._cfg.get("spdf_deskew", True)),
            "spdf_clean":             tk.BooleanVar(value=self._cfg.get("spdf_clean", False)),
            "spdf_force_ocr":         tk.BooleanVar(value=self._cfg.get("spdf_force_ocr", False)),
            "spdf_optimize":          tk.StringVar(value=str(self._cfg.get("spdf_optimize", 1))),
            "spdf_pdfa":              tk.BooleanVar(value=self._cfg.get("spdf_pdfa", False)),
            "spdf_sidecar":           tk.BooleanVar(value=self._cfg.get("spdf_sidecar", False)),
            "spdf_rag_sidecar":       tk.BooleanVar(value=self._cfg.get("spdf_rag_sidecar", False)),
            "spdf_bg_removal":        tk.BooleanVar(value=self._cfg.get("spdf_bg_removal", False)),
        }
        self._rule_profiles: list[_rules_mod.RuleProfile] = _rules_mod.load_profiles()
        for var in self._setting_vars.values():
            var.trace_add("write", self._on_setting_changed)

        # ── Scrollable content frame ───────────────────────────
        self._settings_scroll_outer = tk.Frame(f)
        self._settings_scroll_outer.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 8))
        self._settings_scroll_outer.grid_rowconfigure(0, weight=1)
        self._settings_scroll_outer.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(self._settings_scroll_outer, bd=0, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb = GlassScrollbar(self._settings_scroll_outer, orient="vertical", command=canvas.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self._glass_scrollbars.append(vsb)
        canvas.configure(yscrollcommand=vsb.set)

        self._settings_content = tk.Frame(canvas)
        self._settings_canvas_window = canvas.create_window(
            (0, 0), window=self._settings_content, anchor="nw")

        def _on_content_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_configure(event):
            canvas.itemconfig(self._settings_canvas_window, width=event.width)
        self._settings_content.bind("<Configure>", _on_content_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        self._bind_scroll(self._settings_scroll_outer, target=canvas)
        self._bind_scroll(canvas)
        self._settings_content.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', canvas))

        self._settings_canvas = canvas

        # col 0 = ⓘ icon, col 1 = label (expands), col 2 = control, col 3 = default hint
        self._settings_content.grid_columnconfigure(1, weight=1)

        row = 0

        # ── Section: CONVERSION (expanded) ────────────────────
        row = self._settings_add_section(
            self._settings_content, "Conversion", row,
            first=True, section_id="conversion")
        row = self._settings_add_dropdown(
            self._settings_content, "conversion_mode", "Conversion Mode",
            ["Standard", "OCR", "Auto-detect"],
            _TIPS["conversion_mode"], row,
            default_hint="default: Auto-detect",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "quality_preset", "Conversion Quality",
            ["Fast", "Balanced", "Quality"],
            _TIPS["quality_preset"], row,
            default_hint="default: Quality",
        )

        # ── Section: CONTENT HANDLING (collapsed) ─────────────
        row = self._settings_add_section(
            self._settings_content, "Content Handling", row,
            section_id="content_handling")
        row = self._settings_add_checkbox(
            self._settings_content, "preserve_images", "Preserve Images",
            _TIPS["preserve_images"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "embed_images", "Embed Images in File (Base64)",
            _TIPS["embed_images"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "preserve_page_numbers", "Preserve Page Numbers",
            _TIPS["preserve_page_numbers"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "rebuild_toc", "Rebuild Table of Contents",
            _TIPS["rebuild_toc"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "remove_headers_footers", "Remove Headers and Footers",
            _TIPS["remove_headers_footers"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "skip_blank_pages", "Skip Blank Pages",
            _TIPS["skip_blank_pages"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "strip_line_numbers", "Strip Line Numbers",
            _TIPS["strip_line_numbers"], row, default_hint="default: off",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "detect_code_blocks", "Detect Code Blocks",
            _TIPS["detect_code_blocks"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "detect_footnotes", "Detect Footnotes",
            _TIPS["detect_footnotes"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "detect_equations", "Detect Equations",
            _TIPS["detect_equations"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "auto_translate", "Auto-Translate OCR Text",
            _TIPS["auto_translate"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "dxf_svg_preview", "DXF Drawing Preview",
            _TIPS["dxf_svg_preview"], row, default_hint="default: on",
        )

        # ── Section: OCR (expanded) ───────────────────────────
        row = self._settings_add_section(
            self._settings_content, "OCR", row, section_id="ocr")
        row = self._settings_add_dropdown(
            self._settings_content, "ocr_engine", "OCR Engine",
            ["Auto", "RapidOCR", "Tesseract", "Ensemble"],
            _TIPS["ocr_engine"], row, default_hint="default: Auto",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "ocr_language", "OCR Language",
            ["English", "French", "German", "Spanish", "Italian", "Portuguese",
             "Dutch", "Auto-detect"],
            _TIPS["ocr_language"], row, default_hint="default: English",
        )

        # ── Section: OUTPUT (expanded) ────────────────────────
        row = self._settings_add_section(
            self._settings_content, "Output", row, section_id="output")
        row = self._settings_add_dropdown(
            self._settings_content, "output_format", "Output Format",
            ["Markdown", "JSON", "HTML", "Plain Text", "RAG Chunks", "Searchable PDF"],
            _TIPS["output_format"], row, default_hint="default: Markdown",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "markdown_flavor", "Markdown Flavor",
            ["GFM", "Obsidian", "Pandoc"],
            _TIPS["markdown_flavor"], row, default_hint="default: GFM",
            conditional="markdown",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "yaml_front_matter", "YAML Front Matter",
            _TIPS["yaml_front_matter"], row, default_hint="default: on",
            conditional="markdown",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "overwrite_existing", "Overwrite Existing Files",
            _TIPS["overwrite_existing"], row, default_hint="default: off",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "output_subfolder", "Output Subfolder Structure",
            _TIPS["output_subfolder"], row, default_hint="default: on",
        )

        # ── Section: SEARCHABLE PDF (conditional) ─────────────
        row = self._settings_add_section(
            self._settings_content, "Searchable PDF", row,
            section_id="searchable_pdf")
        row = self._settings_add_checkbox(
            self._settings_content, "spdf_deskew", "Deskew",
            _TIPS["spdf_deskew"], row, default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "spdf_clean", "Clean Pages",
            _TIPS["spdf_clean"], row, default_hint="default: off",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "spdf_force_ocr", "Force OCR",
            _TIPS["spdf_force_ocr"], row, default_hint="default: off",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "spdf_optimize", "Optimize Level",
            ["0", "1", "2", "3"],
            _TIPS["spdf_optimize"], row, default_hint="default: 1",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "spdf_pdfa", "PDF/A Compliance",
            _TIPS["spdf_pdfa"], row, default_hint="default: off",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "spdf_sidecar", "Sidecar Text",
            _TIPS["spdf_sidecar"], row, default_hint="default: off",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "spdf_rag_sidecar", "RAG from Sidecar",
            _TIPS["spdf_rag_sidecar"], row, default_hint="default: off",
            conditional="sidecar",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "spdf_bg_removal", "Background Removal",
            _TIPS["spdf_bg_removal"], row, default_hint="default: off",
        )

        # ── Section: PERFORMANCE (expanded) ───────────────────
        row = self._settings_add_section(
            self._settings_content, "Performance", row,
            section_id="performance")
        row = self._settings_add_dropdown(
            self._settings_content, "parallel_workers", "Parallel Workers",
            ["1", "2", "4", "8", "12", "16", "Auto"],
            _TIPS["parallel_workers"], row, default_hint="default: Auto",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "low_confidence_action", "Handle Low Confidence Results",
            ["Ask me", "Keep and flag", "Skip"],
            _TIPS["low_confidence_action"], row, default_hint="default: Ask me",
        )

        # ── Section: POST-PROCESSING (collapsed) ─────────────
        row = self._settings_add_section(
            self._settings_content, "Post-Processing", row,
            section_id="post_processing")

        info = tk.Label(self._settings_content, text="ⓘ", font=(_FONT_FAMILY, 12), cursor="question_arrow")
        info.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 4))
        Tooltip(info, (
            "Apply regex find/replace rules to the converted output. Rules run after "
            "conversion and can normalize text, strip unwanted patterns, or reformat "
            "content. Create named profiles for different document types."
        ), lambda: self._t)

        lbl = tk.Label(self._settings_content, text="Active Profile", font=_FONT_SMALL, anchor="w")
        lbl.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        profile_names = ["None"] + [p.name for p in self._rule_profiles]
        self._rules_profile_dd = GlassDropdown(
            self._settings_content,
            options=profile_names,
            variable=self._setting_vars["rules_profile"],
        )
        self._rules_profile_dd.grid(row=row, column=2, sticky="e", pady=4, padx=(0, 8))
        self._settings_dropdowns.append(self._rules_profile_dd)
        self._settings_info_labels.append(info)
        self._settings_name_labels.append(lbl)
        if self._current_section_id in self._collapse_sections:
            self._collapse_sections[self._current_section_id]["children"].extend(
                [info, lbl, self._rules_profile_dd])
        row += 1

        self._btn_manage_rules = PillButton(
            self._settings_content,
            text="Manage Rules…",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._show_rules_editor,
        )
        self._btn_manage_rules.grid(row=row, column=1, columnspan=3, sticky="w", pady=(4, 8))
        self._secondary_pills.append(self._btn_manage_rules)
        if self._current_section_id in self._collapse_sections:
            self._collapse_sections[self._current_section_id]["children"].append(
                self._btn_manage_rules)
        row += 1

        # ── Section: RESET (not collapsible) ──────────────────
        row = self._settings_add_section(
            self._settings_content, "Reset", row,
            section_id="reset", collapsible=False)
        self._btn_reset_defaults = PillButton(
            self._settings_content,
            text="Reset to Defaults",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._on_reset_defaults,
        )
        self._btn_reset_defaults.grid(
            row=row, column=1, columnspan=3, sticky="w", pady=(4, 8))
        self._secondary_pills.append(self._btn_reset_defaults)
        row += 1

        # ── System Info Card (always visible) ─────────────────
        row = self._build_system_info_card(self._settings_content, row)

        # ── Apply initial collapse states ─────────────────────
        for sid, sec in self._collapse_sections.items():
            if sec["collapsed"]:
                for w in sec["children"]:
                    w.grid_remove()

        # ── Apply initial format visibility ───────────────────
        self._update_format_visibility()

        # ── Trace output_format for conditional visibility ────
        def _on_format_change(*_):
            self._update_format_visibility()
            self._update_watch_format()
        self._setting_vars["output_format"].trace_add("write", _on_format_change)

        # ── Trace spdf_sidecar for RAG-from-sidecar visibility ──
        self._setting_vars["spdf_sidecar"].trace_add(
            "write", lambda *_: self._update_sidecar_visibility())

    def _settings_add_section(self, parent, title: str, row: int,
                              first=False, section_id: str = "",
                              collapsible: bool = True) -> int:
        top_pad = 8 if first else 18
        sid = section_id or title.lower().replace(" ", "_").replace("-", "_")
        self._current_section_id = sid if collapsible else ""

        if collapsible:
            collapsed_states = self._cfg.get("_collapsed_sections", {})
            is_collapsed = collapsed_states.get(sid, False)
            chevron = "▸" if is_collapsed else "▾"
            lbl = tk.Label(
                parent, text=f" {chevron}  {title.upper()}",
                font=_FONT_SECTION, anchor="w", cursor="hand2",
            )
            lbl.bind("<Button-1>", lambda _e, s=sid: self._toggle_section(s))
            self._collapse_sections[sid] = {
                "header": lbl, "sep": None, "title": title.upper(),
                "collapsed": is_collapsed, "children": [],
            }
        else:
            lbl = tk.Label(parent, text=title.upper(), font=_FONT_SECTION, anchor="w")

        lbl.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(top_pad, 2))
        sep = tk.Frame(parent, height=1)
        sep.grid(row=row + 1, column=0, columnspan=4, sticky="ew", pady=(0, 2))

        if collapsible:
            self._collapse_sections[sid]["sep"] = sep

        self._settings_section_hdrs.append(lbl)
        self._settings_dividers.append(sep)
        return row + 2

    def _settings_add_checkbox(self, parent, key, label, tip, row,
                                default_hint="", conditional="") -> int:
        info = tk.Label(parent, text="ⓘ", font=(_FONT_FAMILY, 12), cursor="question_arrow")
        info.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 4))
        Tooltip(info, tip, lambda: self._t)

        lbl = tk.Label(parent, text=label, font=_FONT_SMALL, anchor="w")
        lbl.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        var = self._setting_vars[key]
        cb = ToggleSwitch(parent, variable=var)
        cb.grid(row=row, column=2, sticky="e", pady=4, padx=(0, 8))

        hint_lbl = tk.Label(parent, text=default_hint, font=(_FONT_FAMILY, 9), anchor="e")
        hint_lbl.grid(row=row, column=3, sticky="e", pady=4, padx=(0, 4))

        self._settings_info_labels.append(info)
        self._settings_name_labels.append(lbl)
        self._settings_toggles.append(cb)
        self._settings_default_lbls.append(hint_lbl)

        all_widgets = [info, lbl, cb, hint_lbl]
        if self._current_section_id in self._collapse_sections:
            self._collapse_sections[self._current_section_id]["children"].extend(all_widgets)
        if conditional == "markdown":
            self._markdown_only_widgets.extend(all_widgets)
        elif conditional == "sidecar":
            self._sidecar_only_widgets.extend(all_widgets)
        return row + 1

    def _settings_add_dropdown(self, parent, key, label, options, tip, row,
                                default_hint="", conditional="") -> int:
        info = tk.Label(parent, text="ⓘ", font=(_FONT_FAMILY, 12), cursor="question_arrow")
        info.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 4))
        Tooltip(info, tip, lambda: self._t)

        lbl = tk.Label(parent, text=label, font=_FONT_SMALL, anchor="w")
        lbl.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        var = self._setting_vars[key]
        menu = GlassDropdown(parent, variable=var, options=options,
                             font=_FONT_SMALL)
        menu.grid(row=row, column=2, sticky="e", pady=3, padx=(0, 8))

        hint_lbl = tk.Label(parent, text=default_hint, font=(_FONT_FAMILY, 9), anchor="e")
        hint_lbl.grid(row=row, column=3, sticky="e", pady=4, padx=(0, 4))

        self._settings_info_labels.append(info)
        self._settings_name_labels.append(lbl)
        self._settings_dropdowns.append(menu)
        self._settings_default_lbls.append(hint_lbl)

        all_widgets = [info, lbl, menu, hint_lbl]
        if self._current_section_id in self._collapse_sections:
            self._collapse_sections[self._current_section_id]["children"].extend(all_widgets)
        if conditional == "markdown":
            self._markdown_only_widgets.extend(all_widgets)
        return row + 1

    def _on_setting_changed(self, *_):
        if self._resetting_defaults:
            return
        for key, var in self._setting_vars.items():
            val = var.get()
            # Keep numeric settings as int for consistency with settings.load()
            if key in ("spdf_optimize",):
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            self._cfg[key] = val
        _cfg_mod.save(self._cfg)

    def _on_reset_defaults(self):
        """Reset conversion settings to factory defaults. Theme is NOT changed."""
        self._resetting_defaults = True
        defaults = _cfg_mod.DEFAULTS
        for key, val in defaults.items():
            if key in self._setting_vars:
                self._setting_vars[key].set(val)
        self._resetting_defaults = False
        self._on_setting_changed()
        default_collapse = _cfg_mod.DEFAULTS.get("_collapsed_sections", {})
        for sid, sec in self._collapse_sections.items():
            want = default_collapse.get(sid, False)
            if sec["collapsed"] != want:
                sec["collapsed"] = want
                chevron = "▸" if want else "▾"
                sec["header"].configure(text=f" {chevron}  {sec['title']}")
                for w in sec["children"]:
                    if want:
                        w.grid_remove()
                    else:
                        w.grid()
        self._cfg["_collapsed_sections"] = dict(default_collapse)
        _cfg_mod.save(self._cfg)
        self._update_format_visibility()

    # ── Collapsible sections ──────────────────────────────────

    def _toggle_section(self, section_id: str):
        sec = self._collapse_sections.get(section_id)
        if not sec:
            return
        sec["collapsed"] = not sec["collapsed"]
        chevron = "▸" if sec["collapsed"] else "▾"
        sec["header"].configure(text=f" {chevron}  {sec['title']}")
        if sec["collapsed"]:
            for w in sec["children"]:
                w.grid_remove()
        else:
            for w in sec["children"]:
                w.grid()
            self._update_format_visibility()
        states = dict(self._cfg.get("_collapsed_sections", {}))
        states[section_id] = sec["collapsed"]
        self._cfg["_collapsed_sections"] = states
        _cfg_mod.save(self._cfg)

    def _update_format_visibility(self):
        """Show/hide settings that depend on the selected output format."""
        if not self._setting_vars:
            return
        fmt = self._setting_vars["output_format"].get()
        is_markdown = (fmt == "Markdown")
        is_spdf = (fmt == "Searchable PDF")

        output_sec = self._collapse_sections.get("output", {})
        output_collapsed = output_sec.get("collapsed", False)

        for w in self._markdown_only_widgets:
            if is_markdown and not output_collapsed:
                w.grid()
            else:
                w.grid_remove()

        spdf_sec = self._collapse_sections.get("searchable_pdf")
        if spdf_sec:
            if is_spdf:
                spdf_sec["header"].grid()
                spdf_sec["sep"].grid()
                if not spdf_sec["collapsed"]:
                    for w in spdf_sec["children"]:
                        w.grid()
                    self._update_sidecar_visibility()
                else:
                    for w in spdf_sec["children"]:
                        w.grid_remove()
            else:
                spdf_sec["header"].grid_remove()
                spdf_sec["sep"].grid_remove()
                for w in spdf_sec["children"]:
                    w.grid_remove()

    def _update_sidecar_visibility(self):
        """Show/hide RAG-from-sidecar widgets based on sidecar toggle state."""
        if not self._setting_vars:
            return
        sidecar_on = self._setting_vars["spdf_sidecar"].get()
        for w in self._sidecar_only_widgets:
            if sidecar_on:
                w.grid()
            else:
                w.grid_remove()

    def _build_system_info_card(self, parent, row: int) -> int:
        """Build the system hardware info card at the bottom of Settings."""
        card = tk.Frame(parent, highlightthickness=1, padx=12, pady=8)
        card.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(18, 16))

        hdr = tk.Label(card, text="SYSTEM", font=_FONT_SECTION, anchor="w")
        hdr.pack(anchor="w", pady=(0, 4))
        self._sysinfo_labels.append(hdr)

        info = _sysinfo_mod.detect_system()
        lines = [
            f"CPU: {info.cpu_name} ({info.cpu_cores} cores)",
            f"RAM: {info.ram_gb} GB",
        ]
        if info.gpu_name:
            vram = f" ({info.gpu_vram_gb} GB VRAM)" if info.gpu_vram_gb else ""
            lines.append(f"GPU: {info.gpu_name}{vram}")
        else:
            lines.append("GPU: None detected")
        provider_labels = {
            "cuda": "CUDA", "directml": "DirectML",
            "coreml": "CoreML", "cpu": "CPU only",
        }
        lines.append(f"Accelerator: {provider_labels.get(info.gpu_provider, info.gpu_provider)}")
        lines.append(f"Recommended workers: {info.recommended_workers}")

        for line in lines:
            lbl = tk.Label(card, text=line, font=(_FONT_FAMILY, 10), anchor="w")
            lbl.pack(anchor="w", pady=1)
            self._sysinfo_labels.append(lbl)

        self._sysinfo_card = card
        return row + 1

    def _build_conversion(self):
        f = self._new_screen("Conversion")
        f.grid_rowconfigure(7, weight=1)

        self._heading(
            f, "Conversion",
            "Monitor progress, current file, conversion stage, warnings, and completion status.",
        )

        # ── Overall progress ─────────────────────────────────
        self._conv_overall_row = tk.Frame(f)
        self._conv_overall_row.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 4))
        self._conv_overall_row.grid_columnconfigure(1, weight=1)

        self._conv_overall_lbl = tk.Label(
            self._conv_overall_row, text="Overall Progress", font=_FONT_SMALL, anchor="w")
        self._conv_overall_lbl.grid(row=0, column=0, sticky="w")

        self._conv_overall_count_lbl = tk.Label(
            self._conv_overall_row, text="0 of 0 files", font=_FONT_SMALL, anchor="e")
        self._conv_overall_count_lbl.grid(row=0, column=1, sticky="e")

        self._conv_elapsed_lbl = tk.Label(
            self._conv_overall_row, text="", font=_FONT_SMALL, anchor="e")
        self._conv_elapsed_lbl.grid(row=0, column=2, sticky="e", padx=(12, 0))

        self._conv_overall_bar = PillProgressBar(f, height=10)
        self._conv_overall_bar.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 16))

        # ── Current file + stage ─────────────────────────────
        self._conv_file_row = tk.Frame(f)
        self._conv_file_row.grid(row=4, column=0, sticky="ew", padx=32, pady=(0, 4))
        self._conv_file_row.grid_columnconfigure(0, weight=1)

        self._conv_file_name_lbl = tk.Label(
            self._conv_file_row, text="No conversion in progress",
            font=_FONT_BODY, anchor="w")
        self._conv_file_name_lbl.grid(row=0, column=0, sticky="w")

        self._conv_stage_lbl = tk.Label(
            self._conv_file_row, text="", font=_FONT_SMALL, anchor="w")
        self._conv_stage_lbl.grid(row=1, column=0, sticky="w")

        # ── Per-file progress ────────────────────────────────
        self._conv_file_bar = PillProgressBar(f, height=6)
        self._conv_file_bar.grid(row=5, column=0, sticky="ew", padx=32, pady=(0, 16))

        # ── Log panel ────────────────────────────────────────
        self._conv_log_lbl = tk.Label(f, text="Log", font=_FONT_SMALL, anchor="w")
        self._conv_log_lbl.grid(row=6, column=0, sticky="w", padx=32, pady=(0, 4))

        self._conv_log_frame = tk.Frame(f, highlightthickness=1)
        self._conv_log_frame.grid(row=7, column=0, sticky="nsew", padx=32, pady=(0, 8))
        self._conv_log_frame.grid_rowconfigure(0, weight=1)
        self._conv_log_frame.grid_columnconfigure(0, weight=1)

        self._conv_log = tk.Text(
            self._conv_log_frame,
            bd=0, relief="flat",
            font=_FONT_SMALL,
            state="disabled",
            highlightthickness=0,
            wrap="word",
            padx=8, pady=6,
        )
        self._conv_log_sb = GlassScrollbar(
            self._conv_log_frame, orient="vertical", command=self._conv_log.yview)
        self._glass_scrollbars.append(self._conv_log_sb)
        self._conv_log.config(yscrollcommand=self._conv_log_sb.set)
        self._conv_log.grid(row=0, column=0, sticky="nsew")
        self._conv_log_sb.grid(row=0, column=1, sticky="ns")
        self._bind_scroll(self._conv_log)

        # ── Cancel button ────────────────────────────────────
        self._btn_cancel = PillButton(
            f,
            text="Cancel",
            font=_FONT_BTN,
            style="secondary",
            padx=26, pady=10,
            command=self._on_cancel_conversion,
        )
        self._btn_cancel.grid(row=8, column=0, sticky="w", padx=32, pady=(0, 28))
        self._secondary_pills.append(self._btn_cancel)

    def _build_results(self):
        f = self._new_screen("Results")
        f.grid_rowconfigure(2, weight=1)

        self._heading(
            f, "Results",
            "View the output location, confidence report summary, warnings, and open the output folder.",
        )

        # ── Scrollable container (same pattern as Settings) ──
        self._results_scroll_outer = tk.Frame(f)
        self._results_scroll_outer.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 0))
        self._results_scroll_outer.grid_rowconfigure(0, weight=1)
        self._results_scroll_outer.grid_columnconfigure(0, weight=1)

        r_canvas = tk.Canvas(self._results_scroll_outer, bd=0, highlightthickness=0)
        r_canvas.grid(row=0, column=0, sticky="nsew")
        r_vsb = GlassScrollbar(self._results_scroll_outer, orient="vertical",
                                command=r_canvas.yview)
        r_vsb.grid(row=0, column=1, sticky="ns")
        self._glass_scrollbars.append(r_vsb)
        r_canvas.configure(yscrollcommand=r_vsb.set)

        rc = tk.Frame(r_canvas)
        self._results_canvas_window = r_canvas.create_window(
            (0, 0), window=rc, anchor="nw")

        def _on_rc_configure(event):
            r_canvas.configure(scrollregion=r_canvas.bbox("all"))
        def _on_rcanvas_configure(event):
            r_canvas.itemconfig(self._results_canvas_window, width=event.width)
        rc.bind("<Configure>", _on_rc_configure)
        r_canvas.bind("<Configure>", _on_rcanvas_configure)

        self._bind_scroll(self._results_scroll_outer, target=r_canvas)
        self._bind_scroll(r_canvas)
        rc.bind("<Enter>", lambda _e: setattr(self, '_scroll_target', r_canvas))

        self._results_canvas = r_canvas
        self._results_content = rc
        rc.grid_columnconfigure(0, weight=1)

        # All content below lives inside rc (the scrollable inner frame)
        # instead of f (the screen frame).

        # ── Status banner ────────────────────────────────────
        self._results_status_frame = tk.Frame(rc, highlightthickness=1)
        self._results_status_frame.grid(row=0, column=0, sticky="ew", padx=32, pady=(8, 16))
        self._results_status_frame.grid_columnconfigure(0, weight=1)

        self._results_status_lbl = tk.Label(
            self._results_status_frame,
            text="No conversion has been run yet.",
            font=_FONT_SMALL,
            anchor="w",
            padx=12, pady=8,
        )
        self._results_status_lbl.grid(row=0, column=0, sticky="ew")

        # ── Output location row ──────────────────────────────
        self._results_out_row = tk.Frame(rc)
        self._results_out_row.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 16))
        self._results_out_row.grid_columnconfigure(0, weight=1)

        self._results_out_path_frame = tk.Frame(self._results_out_row, highlightthickness=1)
        self._results_out_path_frame.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._results_out_path_frame.grid_columnconfigure(0, weight=1)

        self._results_out_path_lbl = tk.Label(
            self._results_out_path_frame,
            text="Output location: —",
            font=_FONT_SMALL,
            anchor="w",
            padx=10, pady=6,
        )
        self._results_out_path_lbl.grid(row=0, column=0, sticky="ew")

        self._btn_open_folder = PillButton(
            self._results_out_row,
            text="Open Folder",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._on_open_output_folder,
        )
        self._btn_open_folder.grid(row=0, column=1)
        self._secondary_pills.append(self._btn_open_folder)
        Tooltip(self._btn_open_folder,
                "Open the output folder in your system file explorer.",
                lambda: self._t)

        # ── Per-file list with content badges ────────────────
        self._results_files_section_lbl = tk.Label(
            rc, text="FILES", font=_FONT_SECTION, anchor="w")
        self._results_files_section_lbl.grid(
            row=2, column=0, sticky="ew", padx=32, pady=(0, 2))

        self._results_files_div = tk.Frame(rc, height=1)
        self._results_files_div.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 6))

        self._results_files_outer = tk.Frame(rc, highlightthickness=1)
        self._results_files_outer.grid(
            row=4, column=0, sticky="ew", padx=32, pady=(0, 16))
        self._results_files_outer.grid_rowconfigure(0, weight=1)
        self._results_files_outer.grid_columnconfigure(0, weight=1)

        files_canvas = tk.Canvas(
            self._results_files_outer, bd=0, highlightthickness=0,
            height=int(120 * self._dpi))
        files_canvas.grid(row=0, column=0, sticky="nsew")
        files_vsb = GlassScrollbar(
            self._results_files_outer, orient="vertical",
            command=files_canvas.yview)
        files_vsb.grid(row=0, column=1, sticky="ns")
        self._glass_scrollbars.append(files_vsb)
        files_canvas.configure(yscrollcommand=files_vsb.set)

        self._results_files_inner = tk.Frame(files_canvas)
        files_canvas.create_window((0, 0), window=self._results_files_inner, anchor="nw")
        self._results_files_inner.bind(
            "<Configure>",
            lambda _e: files_canvas.configure(scrollregion=files_canvas.bbox("all")))
        files_canvas.bind(
            "<Configure>",
            lambda e: files_canvas.itemconfig(
                files_canvas.find_all()[0], width=e.width)
            if files_canvas.find_all() else None)

        self._results_files_canvas = files_canvas

        self._bind_scroll(files_canvas, parent_target=r_canvas)
        self._results_files_inner.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', files_canvas))

        # Placeholder when no results yet
        self._results_files_placeholder = tk.Label(
            self._results_files_inner,
            text="No files converted yet.",
            font=_FONT_SMALL, anchor="w", padx=10, pady=8,
        )
        self._results_files_placeholder.pack(anchor="w")

        # ── Confidence summary ───────────────────────────────
        self._results_conf_section_lbl = tk.Label(
            rc, text="CONFIDENCE SUMMARY", font=_FONT_SECTION, anchor="w")
        self._results_conf_section_lbl.grid(
            row=5, column=0, sticky="ew", padx=32, pady=(0, 2))

        self._results_conf_div = tk.Frame(rc, height=1)
        self._results_conf_div.grid(row=6, column=0, sticky="ew", padx=32, pady=(0, 6))

        self._results_conf_frame = tk.Frame(rc)
        self._results_conf_frame.grid(row=7, column=0, sticky="ew", padx=32, pady=(0, 16))
        self._results_conf_frame.grid_columnconfigure(0, weight=1)

        self._results_conf_level_lbls: list[tk.Label] = []
        for idx, area in enumerate(_CONF_AREAS):
            tk.Label(
                self._results_conf_frame, text=area, font=_FONT_SMALL, anchor="w",
            ).grid(row=idx, column=0, sticky="w", pady=2)

            lvl = tk.Label(
                self._results_conf_frame, text="—", font=_FONT_SMALL, anchor="e")
            lvl.grid(row=idx, column=1, sticky="e", pady=2)
            self._results_conf_level_lbls.append(lvl)

        # ── Validation summary ────────────────────────────────
        self._results_val_section_lbl = tk.Label(
            rc, text="VALIDATION", font=_FONT_SECTION, anchor="w")
        self._results_val_section_lbl.grid(
            row=8, column=0, sticky="ew", padx=32, pady=(0, 2))

        self._results_val_div = tk.Frame(rc, height=1)
        self._results_val_div.grid(row=9, column=0, sticky="ew", padx=32, pady=(0, 6))

        self._results_val_frame = tk.Frame(rc)
        self._results_val_frame.grid(row=10, column=0, sticky="ew", padx=32, pady=(0, 16))
        self._results_val_frame.grid_columnconfigure(1, weight=1)

        _val_rows = [
            ("Headings", "heading_count",
             "Number of headings (H1–H6) found in the converted Markdown. "
             "Skipped heading levels (e.g. H1 → H3) are flagged as issues below."),
            ("Tables", "table_count",
             "Number of Markdown tables detected in the output. Compares against "
             "tables in the source document to check for extraction accuracy."),
            ("Images", "image_count",
             "Number of images referenced in the output Markdown. Missing alt-text "
             "on any image is flagged as an accessibility issue below."),
            ("Pages", "page_count",
             "Number of page-break anchors inserted during conversion. Useful for "
             "cross-referencing the Markdown against the original document by page."),
            ("Words", "word_count",
             "Total word count of the converted Markdown output, excluding code "
             "blocks and front matter. Gives a quick sense of document size."),
            ("Readability", "readability",
             "Flesch-Kincaid Grade Level estimates the US school grade needed to "
             "understand the text. Grade 5 = very easy, 8 = easy, 12 = standard, "
             "16 = college level, 16+ = graduate level. Technical documents "
             "typically score 12–16."),
        ]
        self._results_val_count_lbls: dict[str, tk.Label] = {}
        for idx, (label, key, tip) in enumerate(_val_rows):
            name_lbl = tk.Label(
                self._results_val_frame, text=label, font=_FONT_SMALL, anchor="w",
            )
            name_lbl.grid(row=idx, column=0, sticky="w", pady=2)
            Tooltip(name_lbl, tip, lambda: self._t)
            val_lbl = tk.Label(
                self._results_val_frame, text="—", font=_FONT_SMALL, anchor="e")
            val_lbl.grid(row=idx, column=1, sticky="e", pady=2)
            self._results_val_count_lbls[key] = val_lbl

        # Validation issues (scrollable text box)
        self._results_val_issues_frame = tk.Frame(rc, highlightthickness=1)
        self._results_val_issues_frame.grid(
            row=11, column=0, sticky="nsew", padx=32, pady=(0, 8))
        self._results_val_issues_frame.grid_rowconfigure(0, weight=1)
        self._results_val_issues_frame.grid_columnconfigure(0, weight=1)

        self._results_val_issues_text = tk.Text(
            self._results_val_issues_frame,
            bd=0, relief="flat", font=_FONT_SMALL,
            state="disabled", highlightthickness=0,
            wrap="word", padx=8, pady=6, height=5,
        )
        self._results_val_issues_sb = GlassScrollbar(
            self._results_val_issues_frame, orient="vertical",
            command=self._results_val_issues_text.yview)
        self._glass_scrollbars.append(self._results_val_issues_sb)
        self._results_val_issues_text.config(
            yscrollcommand=self._results_val_issues_sb.set)
        self._results_val_issues_text.grid(row=0, column=0, sticky="nsew")
        self._results_val_issues_sb.grid(row=0, column=1, sticky="ns")
        self._bind_scroll(self._results_val_issues_text, parent_target=r_canvas)

        # ── Warnings ─────────────────────────────────────────
        self._results_warn_lbl = tk.Label(rc, text="Warnings", font=_FONT_SMALL, anchor="w")
        self._results_warn_lbl.grid(row=12, column=0, sticky="w", padx=32, pady=(0, 4))

        self._results_warn_frame = tk.Frame(rc, highlightthickness=1)
        self._results_warn_frame.grid(row=13, column=0, sticky="nsew", padx=32, pady=(0, 8))
        self._results_warn_frame.grid_rowconfigure(0, weight=1)
        self._results_warn_frame.grid_columnconfigure(0, weight=1)

        self._results_warn_text = tk.Text(
            self._results_warn_frame,
            bd=0, relief="flat",
            font=_FONT_SMALL,
            state="disabled",
            highlightthickness=0,
            wrap="word",
            padx=8, pady=6,
            height=4,
        )
        self._results_warn_sb = GlassScrollbar(
            self._results_warn_frame, orient="vertical",
            command=self._results_warn_text.yview)
        self._glass_scrollbars.append(self._results_warn_sb)
        self._results_warn_text.config(yscrollcommand=self._results_warn_sb.set)
        self._results_warn_text.grid(row=0, column=0, sticky="nsew")
        self._results_warn_sb.grid(row=0, column=1, sticky="ns")
        self._bind_scroll(self._results_warn_text, parent_target=r_canvas)

        # ── Button row ───────────────────────────────────────
        self._results_btn_row = tk.Frame(rc)
        self._results_btn_row.grid(row=14, column=0, sticky="ew", padx=32, pady=(0, 28))

        self._btn_open_output = PillButton(
            self._results_btn_row,
            text="Open Output Folder",
            font=_FONT_BTN,
            style="primary",
            padx=26, pady=10,
            command=self._on_open_output_folder,
        )
        self._btn_open_output.grid(row=0, column=0)
        self._primary_pills.append(self._btn_open_output)

        self._btn_new_conv = PillButton(
            self._results_btn_row,
            text="Start New Conversion",
            font=_FONT_BTN,
            style="secondary",
            padx=26, pady=10,
            command=lambda: self._show("Home"),
        )
        self._btn_new_conv.grid(row=0, column=1, padx=(12, 0))
        self._secondary_pills.append(self._btn_new_conv)

        self._btn_preview = PillButton(
            self._results_btn_row,
            text="Preview Output",
            font=_FONT_BTN,
            style="secondary",
            padx=26, pady=10,
            command=self._show_preview_window,
        )
        self._btn_preview.grid(row=1, column=0, pady=(10, 0))
        self._secondary_pills.append(self._btn_preview)
        Tooltip(self._btn_preview,
                "Open the preview window to review converted output with syntax highlighting, "
                "inline images, search and replace, spell check, and confidence heatmap.",
                lambda: self._t)

        self._btn_debug_info = PillButton(
            self._results_btn_row,
            text="View Debug Info",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=7,
            command=self._show_debug_window,
        )
        self._btn_debug_info.grid(row=1, column=1, padx=(12, 0), pady=(10, 0))
        self._secondary_pills.append(self._btn_debug_info)
        Tooltip(self._btn_debug_info,
                "View detailed conversion diagnostics — engine used, confidence breakdown, "
                "warnings, and settings snapshot. Export as a text file for troubleshooting.",
                lambda: self._t)

    # ── Watch Folder screen ─────────────────────────────────

    def _build_watch(self):
        f = self._new_screen("Watch")
        f.grid_rowconfigure(9, weight=1)

        self._heading(
            f, "Watch Folder",
            "Monitor a folder for new files and auto-convert them using your current settings.",
        )

        # ── Folder selection rows ────────────────────────────
        # Watch input folder
        self._watch_input_row = tk.Frame(f)
        self._watch_input_row.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 8))
        self._watch_input_row.grid_columnconfigure(1, weight=1)

        tk.Label(
            self._watch_input_row, text="Watch:", font=_FONT_SMALL, anchor="w", width=8,
        ).grid(row=0, column=0, sticky="w")

        self._watch_input_path_frame = tk.Frame(self._watch_input_row, highlightthickness=1)
        self._watch_input_path_frame.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self._watch_input_path_frame.grid_columnconfigure(0, weight=1)

        self._watch_input_path_lbl = tk.Label(
            self._watch_input_path_frame,
            text="No folder selected",
            font=_FONT_SMALL, anchor="w", padx=10, pady=6,
        )
        self._watch_input_path_lbl.grid(row=0, column=0, sticky="ew")

        self._btn_watch_browse_input = PillButton(
            self._watch_input_row,
            text="Browse",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._pick_watch_input,
        )
        self._btn_watch_browse_input.grid(row=0, column=2)
        self._secondary_pills.append(self._btn_watch_browse_input)

        # Watch output folder
        self._watch_output_row = tk.Frame(f)
        self._watch_output_row.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 16))
        self._watch_output_row.grid_columnconfigure(1, weight=1)

        tk.Label(
            self._watch_output_row, text="Output:", font=_FONT_SMALL, anchor="w", width=8,
        ).grid(row=0, column=0, sticky="w")

        self._watch_output_path_frame = tk.Frame(self._watch_output_row, highlightthickness=1)
        self._watch_output_path_frame.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self._watch_output_path_frame.grid_columnconfigure(0, weight=1)

        self._watch_output_path_lbl = tk.Label(
            self._watch_output_path_frame,
            text="No folder selected",
            font=_FONT_SMALL, anchor="w", padx=10, pady=6,
        )
        self._watch_output_path_lbl.grid(row=0, column=0, sticky="ew")

        self._btn_watch_browse_output = PillButton(
            self._watch_output_row,
            text="Browse",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._pick_watch_output,
        )
        self._btn_watch_browse_output.grid(row=0, column=2)
        self._secondary_pills.append(self._btn_watch_browse_output)

        # ── Format indicator ─────────────────────────────────
        self._watch_format_row = tk.Frame(f)
        self._watch_format_row.grid(row=4, column=0, sticky="ew", padx=32, pady=(0, 12))
        self._watch_format_row.grid_columnconfigure(0, weight=1)

        self._watch_format_lbl = tk.Label(
            self._watch_format_row, text="", font=_FONT_SMALL, anchor="w")
        self._watch_format_lbl.grid(row=0, column=0, sticky="w")

        self._watch_format_note_lbl = tk.Label(
            self._watch_format_row, text="", font=(_FONT_FAMILY, 9), anchor="w")
        self._watch_format_note_lbl.grid(row=1, column=0, sticky="w")

        # ── Controls row ─────────────────────────────────────
        self._watch_ctrl_row = tk.Frame(f)
        self._watch_ctrl_row.grid(row=5, column=0, sticky="ew", padx=32, pady=(0, 8))
        self._watch_ctrl_row.grid_columnconfigure(2, weight=1)

        self._btn_watch_start = PillButton(
            self._watch_ctrl_row,
            text="Start Watching",
            font=_FONT_BTN,
            style="primary",
            padx=26, pady=10,
            command=self._toggle_watch,
        )
        self._btn_watch_start.grid(row=0, column=0, padx=(0, 12))
        self._primary_pills.append(self._btn_watch_start)

        self._watch_status_lbl = tk.Label(
            self._watch_ctrl_row,
            text="Stopped",
            font=_FONT_SMALL,
            anchor="w",
        )
        self._watch_status_lbl.grid(row=0, column=1, sticky="w")

        self._watch_counts_lbl = tk.Label(
            self._watch_ctrl_row,
            text="",
            font=_FONT_SMALL,
            anchor="e",
        )
        self._watch_counts_lbl.grid(row=0, column=3, sticky="e")

        # ── Per-file progress section ────────────────────────
        self._watch_progress_row = tk.Frame(f)
        self._watch_progress_row.grid(row=6, column=0, sticky="ew", padx=32, pady=(0, 4))
        self._watch_progress_row.grid_columnconfigure(0, weight=1)

        self._watch_file_lbl = tk.Label(
            self._watch_progress_row, text="", font=_FONT_SMALL, anchor="w")
        self._watch_file_lbl.grid(row=0, column=0, sticky="w")

        self._watch_stage_lbl = tk.Label(
            self._watch_progress_row, text="", font=_FONT_SMALL, anchor="e")
        self._watch_stage_lbl.grid(row=0, column=1, sticky="e")

        self._watch_progress_bar = PillProgressBar(f, height=6)
        self._watch_progress_bar.grid(row=7, column=0, sticky="ew", padx=32, pady=(0, 12))

        # ── Activity log section label ───────────────────────
        self._watch_log_section_lbl = tk.Label(
            f, text="ACTIVITY LOG", font=_FONT_SECTION, anchor="w")
        self._watch_log_section_lbl.grid(
            row=8, column=0, sticky="ew", padx=32, pady=(0, 2))

        # ── Activity log ─────────────────────────────────────
        self._watch_log_frame = tk.Frame(f, highlightthickness=1)
        self._watch_log_frame.grid(row=9, column=0, sticky="nsew", padx=32, pady=(0, 8))
        self._watch_log_frame.grid_rowconfigure(0, weight=1)
        self._watch_log_frame.grid_columnconfigure(0, weight=1)

        self._watch_log = tk.Text(
            self._watch_log_frame,
            bd=0, relief="flat",
            font=_FONT_SMALL,
            state="disabled",
            highlightthickness=0,
            wrap="word",
            padx=8, pady=6,
        )
        self._watch_log_sb = GlassScrollbar(
            self._watch_log_frame, orient="vertical",
            command=self._watch_log.yview)
        self._glass_scrollbars.append(self._watch_log_sb)
        self._watch_log.config(yscrollcommand=self._watch_log_sb.set)
        self._watch_log.grid(row=0, column=0, sticky="nsew")
        self._watch_log_sb.grid(row=0, column=1, sticky="ns")
        self._bind_scroll(self._watch_log)

        # ── Bottom button row ────────────────────────────────
        self._watch_btn_row = tk.Frame(f)
        self._watch_btn_row.grid(row=10, column=0, sticky="ew", padx=32, pady=(0, 28))

        self._btn_watch_clear_log = PillButton(
            self._watch_btn_row,
            text="Clear Log",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._clear_watch_log,
        )
        self._btn_watch_clear_log.grid(row=0, column=0)
        self._secondary_pills.append(self._btn_watch_clear_log)

    # ── Watch Folder handlers ───────────────────────────────

    def _update_watch_format(self):
        """Update the Watch screen format indicator based on current settings."""
        if not self._setting_vars:
            return
        fmt = self._setting_vars["output_format"].get()
        self._watch_format_lbl.config(text=f"Output: {fmt}")
        if fmt == "Searchable PDF":
            self._watch_format_note_lbl.config(text="OCR will be applied to incoming files")
        else:
            self._watch_format_note_lbl.config(text="")

    # ── Elapsed timer helpers ─────────────────────────────

    def _start_elapsed_timer(self) -> None:
        self._elapsed_start = time.monotonic()
        self._conv_elapsed_lbl.config(text="0:00")
        self._tick_elapsed()

    @staticmethod
    def _format_elapsed(delta: int) -> str:
        if delta >= 3600:
            return f"{delta // 3600}:{(delta % 3600) // 60:02d}:{delta % 60:02d}"
        return f"{delta // 60}:{delta % 60:02d}"

    def _tick_elapsed(self) -> None:
        delta = int(time.monotonic() - self._elapsed_start)
        self._conv_elapsed_lbl.config(text=self._format_elapsed(delta))
        self._elapsed_after_id = self.root.after(1000, self._tick_elapsed)

    def _stop_elapsed_timer(self) -> None:
        if self._elapsed_after_id is not None:
            self.root.after_cancel(self._elapsed_after_id)
            self._elapsed_after_id = None
        delta = int(time.monotonic() - self._elapsed_start)
        self._conv_elapsed_lbl.config(text=self._format_elapsed(delta))

    def _pick_watch_input(self):
        path = filedialog.askdirectory(title="Select folder to watch")
        if path:
            self._watch_input_path = path
            self._watch_input_path_lbl.config(text=path)

    def _pick_watch_output(self):
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self._watch_output_path = path
            self._watch_output_path_lbl.config(text=path)

    def _toggle_watch(self):
        if self._watcher and self._watcher.is_running:
            self._stop_watch()
        else:
            self._start_watch()

    def _start_watch(self):
        if not self._watch_input_path:
            messagebox.showwarning("Watch Folder", "Please select a folder to watch.")
            return
        if not os.path.isdir(self._watch_input_path):
            messagebox.showwarning("Watch Folder", f"Watch folder does not exist:\n{self._watch_input_path}")
            return
        if not self._watch_output_path:
            messagebox.showwarning("Watch Folder", "Please select an output folder.")
            return

        cfg = dict(self._cfg)

        try:
            self._watcher = _watch_mod.FolderWatcher(
                watch_path=self._watch_input_path,
                output_path=self._watch_output_path,
                cfg=cfg,
                root=self.root,
                on_file_queued=self._watch_on_queued,
                on_file_started=self._watch_on_started,
                on_file_done=self._watch_on_done,
                on_file_progress=self._watch_on_progress,
                on_stage=self._watch_on_stage,
                on_error=self._watch_on_error,
            )
            self._watcher.start()
        except Exception as exc:
            messagebox.showerror(
                "Watch Folder",
                f"Could not start folder watcher:\n\n{exc}\n\n"
                "Make sure the 'watchdog' package is installed.",
            )
            return

        self._btn_watch_start.set_text("Stop Watching")
        self._watch_status_lbl.config(text="Watching...", fg=self._t.get("accent", "#7c3aed"))
        self._watch_log_append(f"Started watching: {self._watch_input_path}")
        self._watch_log_append(f"Output folder: {self._watch_output_path}")

    def _stop_watch(self):
        if self._watcher:
            self._watcher.stop()
        self._btn_watch_start.set_text("Start Watching")
        self._watch_status_lbl.config(text="Stopped", fg=self._t["text_secondary"])
        self._watch_file_lbl.config(text="")
        self._watch_stage_lbl.config(text="")
        self._watch_progress_bar.set_progress(0.0)
        self._watch_log_append("Stopped watching.")

    def _watch_on_queued(self, path: str):
        filename = os.path.basename(path)
        self._watch_log_append(f"Detected: {filename}")
        self._update_watch_counts()

    def _watch_on_started(self, path: str):
        filename = os.path.basename(path)
        self._watch_file_lbl.config(text=filename)
        self._watch_stage_lbl.config(text="Starting…")
        self._watch_progress_bar.set_progress(0.0)
        self._watch_log_append(f"Converting: {filename}...")

    def _watch_on_done(self, path: str, success: bool, message: str):
        prefix = "  ✓" if success else "  ✗"
        self._watch_log_append(f"{prefix} {message}")
        self._watch_progress_bar.set_progress(1.0 if success else 0.0)
        self._watch_file_lbl.config(text="")
        self._watch_stage_lbl.config(text="")
        self._update_watch_counts()
        if success:
            self._watch_notify(os.path.basename(path))

    def _watch_on_progress(self, fraction: float):
        self._watch_progress_bar.set_progress(fraction)

    def _watch_on_stage(self, stage: str):
        self._watch_stage_lbl.config(text=stage)

    def _watch_on_error(self, message: str):
        self._watch_log_append(f"Error: {message}")

    _MAX_LOG_LINES = 1000

    def _watch_log_append(self, text: str):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self._watch_log.config(state="normal")
        self._watch_log.insert("end", f"[{timestamp}] {text}\n")
        # Cap log size to prevent unbounded memory growth
        line_count = int(self._watch_log.index("end-1c").split(".")[0])
        if line_count > self._MAX_LOG_LINES:
            self._watch_log.delete("1.0", f"{line_count - self._MAX_LOG_LINES}.0")
        self._watch_log.see("end")
        self._watch_log.config(state="disabled")

    def _clear_watch_log(self):
        self._watch_log.config(state="normal")
        self._watch_log.delete("1.0", "end")
        self._watch_log.config(state="disabled")

    def _update_watch_counts(self):
        if self._watcher:
            c = self._watcher.completed_count
            f = self._watcher.failed_count
            self._watch_counts_lbl.config(
                text=f"Converted: {c}    Failed: {f}")

    def _watch_notify(self, filename: str):
        """Flash the Watch nav button briefly to signal a completed file."""
        btn = self._nav_btns.get("Watch")
        if btn and self._current != "Watch":
            # Cancel any pending restore before scheduling a new one
            pending = self._watch_notify_id
            if pending is not None:
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
            btn.config(fg=self._t.get("accent", "#7c3aed"))

            def _restore():
                self._watch_notify_id = None
                # Don't overwrite accent if Watch tab is now active
                if self._current != "Watch":
                    btn.config(fg=self._t["text"])
            self._watch_notify_id = self.root.after(2000, _restore)

    def _results_notify(self):
        """Flash the Results nav button briefly to signal conversion completion."""
        btn = self._nav_btns.get("Results")
        if btn and self._current != "Results":
            pending = getattr(self, "_results_notify_id", None)
            if pending is not None:
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
            btn.config(fg=self._t.get("accent", "#7c3aed"))

            def _restore():
                self._results_notify_id = None
                if self._current != "Results":
                    btn.config(fg=self._t["text"])
            self._results_notify_id = self.root.after(2000, _restore)

    # ── Debug / Preview window ──────────────────────────────

    def _show_debug_window(self):
        """Open a Toplevel window with diagnostic info about the last conversion."""
        result = self._last_batch_result
        if result is None:
            messagebox.showinfo("Debug Info", "No conversion results available yet.")
            return

        t = self._t
        win = tk.Toplevel(self.root)
        win.title("Debug Info — Conversion Diagnostics")
        win.geometry("680x500")
        win.config(bg=t["bg"])
        self._set_titlebar_dark(self._dark, win)

        # Scrollable text widget
        text_frame = tk.Frame(win, bg=t["bg"])
        text_frame.pack(fill="both", expand=True)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        text = tk.Text(
            text_frame, font=_FONT_SMALL, wrap="word",
            bg=t["bg"], fg=t["text"],
            bd=0, highlightthickness=0,
            padx=12, pady=10,
        )
        sb = GlassScrollbar(text_frame, orient="vertical", command=text.yview)
        _sb_thumb = t["scrollbar_thumb"]
        _sb_hover = t["scrollbar_hover"]
        sb.set_colors(thumb=_sb_thumb, thumb_hover=_sb_hover, parent_bg=t["bg"])
        text.config(yscrollcommand=sb.set)
        text.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        self._bind_scroll(text)

        def _on_debug_close():
            if self._scroll_target is text:
                self._scroll_target = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_debug_close)

        lines = []
        lines.append("═══  CONVERSION DEBUG INFO  ═══\n")
        lines.append(f"Status: {result.status_text}")
        lines.append(f"Total files: {result.total}")
        lines.append(f"Completed: {result.completed}")
        lines.append(f"Failed: {result.failed}")
        lines.append(f"Cancelled: {result.cancelled}")
        lines.append(f"Output root: {result.output_root}")
        lines.append("")

        # Batch confidence details
        bc = result.batch_confidence
        lines.append("── BATCH CONFIDENCE ──")
        lines.append(f"  Overall:           {bc.overall or 'N/A'}")
        lines.append(f"  Text extraction:   {bc.text_extraction or 'N/A'}")
        lines.append(f"  Table structure:   {bc.table_structure or 'N/A'}")
        lines.append(f"  Image extraction:  {bc.image_extraction or 'N/A'}")
        lines.append(f"  Image placement:   {bc.image_placement or 'N/A'}")
        lines.append(f"  Document order:    {bc.document_order or 'N/A'}")
        lines.append(f"  OCR confidence:    {bc.ocr_confidence or 'N/A'}")
        lines.append("")

        # Per-file confidence
        if result.all_confidence:
            lines.append("── PER-FILE CONFIDENCE ──")
            for conf in result.all_confidence:
                fname = os.path.basename(conf.source_file) if conf.source_file else "Unknown"
                lines.append(f"\n  {fname}:")
                lines.append(f"    Overall:         {conf.overall or 'N/A'}")
                lines.append(f"    Text extraction: {conf.text_extraction or 'N/A'}")
                lines.append(f"    Table structure: {conf.table_structure or 'N/A'}")
                lines.append(f"    OCR confidence:  {conf.ocr_confidence or 'N/A'}")
                if conf.warnings:
                    lines.append(f"    Warnings ({len(conf.warnings)}):")
                    for w in conf.warnings:
                        lines.append(f"      - {w}")
                if conf.notes:
                    lines.append(f"    Notes ({len(conf.notes)}):")
                    for n in conf.notes:
                        lines.append(f"      - {n}")
            lines.append("")

        # Settings snapshot
        lines.append("── SETTINGS USED ──")
        for key, val in sorted(self._cfg.items()):
            if key != "theme":
                lines.append(f"  {key}: {val}")

        text.insert("1.0", "\n".join(lines))
        text.config(state="disabled")

        # ── Export Log button ────────────────────────────────
        btn_frame = tk.Frame(win, bg=t["bg"])
        btn_frame.pack(fill="x", padx=12, pady=(4, 12))

        def _export_log():
            from datetime import datetime
            default_name = f"conversion_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            path = filedialog.asksaveasfilename(
                parent=win,
                title="Save Debug Log",
                initialfile=default_name,
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            )
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text.get("1.0", tk.END))
                btn_export.set_text("✓ Saved")
                win.after(1500, lambda: btn_export.set_text("Export Log")
                          if win.winfo_exists() else None)
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not save log:\n{e}", parent=win)

        btn_export = PillButton(
            btn_frame, text="Export Log", font=_FONT_SMALL,
            style="secondary", padx=14, pady=6,
            command=_export_log,
        )
        btn_export.pack(side="right")
        btn_export.set_colors(
            fill=t["bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["bg"],
        )
        Tooltip(btn_export,
                "Save the full conversion log to a text file for troubleshooting or archival.",
                lambda: self._t)

    # ── Rules Editor dialog ────────────────────────────────

    def _show_rules_editor(self):
        t = self._t
        win = tk.Toplevel(self.root)
        win.title("Post-Processing Rules")
        win.geometry("780x520")
        win.config(bg=t["bg"])
        self._set_titlebar_dark(self._dark, win)
        win.transient(self.root)
        win.grab_set()

        profiles = list(self._rule_profiles)
        selected_profile_idx = [None]
        selected_rule_idx = [None]

        # ── Top bar ──────────────────────────────────────────
        top = tk.Frame(win, bg=t["bg"])
        top.pack(fill="x", padx=16, pady=(12, 8))

        tk.Label(top, text="Profiles", font=_FONT_TITLE, bg=t["bg"], fg=t["text"]).pack(
            side="left")

        def add_profile():
            name = simpledialog.askstring("New Profile", "Profile name:", parent=win)
            if not name or not name.strip():
                return
            name = name.strip()
            if any(p.name == name for p in profiles):
                messagebox.showwarning("Duplicate", f"Profile '{name}' already exists.", parent=win)
                return
            profiles.append(_rules_mod.RuleProfile(name=name))
            refresh_profile_list()
            profile_listbox.selection_set(len(profiles) - 1)
            on_profile_select(None)

        def delete_profile():
            idx = selected_profile_idx[0]
            if idx is None:
                return
            profiles.pop(idx)
            selected_profile_idx[0] = None
            selected_rule_idx[0] = None
            refresh_profile_list()
            refresh_rule_list()

        btn_add_profile = PillButton(top, text="+ New", font=_FONT_SMALL, style="secondary",
                                     padx=10, pady=4, command=add_profile)
        btn_add_profile.pack(side="right", padx=(4, 0))
        btn_add_profile.set_colors(
            fill=t["bg"], fg=t["accent"], outline=t["border"],
            hover_fill=t["bg"], hover_fg=t["accent"], hover_outline=t["accent"],
            parent_bg=t["bg"])

        btn_del_profile = PillButton(top, text="Delete", font=_FONT_SMALL, style="secondary",
                                     padx=10, pady=4, command=delete_profile)
        btn_del_profile.pack(side="right", padx=(4, 0))
        btn_del_profile.set_colors(
            fill=t["bg"], fg=t["accent"], outline=t["border"],
            hover_fill=t["bg"], hover_fg=t["accent"], hover_outline=t["accent"],
            parent_bg=t["bg"])

        # ── Main paned area ──────────────────────────────────
        body = tk.Frame(win, bg=t["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)

        # Left: profile list
        left = tk.Frame(body, bg=t["bg"], width=180)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_rowconfigure(0, weight=1)
        left.grid_columnconfigure(0, weight=1)
        left.grid_propagate(False)

        profile_listbox = tk.Listbox(
            left, bd=0, highlightthickness=1, font=_FONT_SMALL,
            bg=t["bg"], fg=t["text"], selectbackground=t["accent"],
            selectforeground=t["text_on_accent"],
            highlightbackground=t["border"],
        )
        profile_listbox.grid(row=0, column=0, sticky="nsew")
        self._bind_scroll(profile_listbox)

        # Right: rules panel
        right = tk.Frame(body, bg=t["bg"])
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Rules toolbar
        rules_toolbar = tk.Frame(right, bg=t["bg"])
        rules_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        tk.Label(rules_toolbar, text="Rules", font=_FONT_TITLE, bg=t["bg"], fg=t["text"]).pack(
            side="left")

        def add_rule():
            idx = selected_profile_idx[0]
            if idx is None:
                messagebox.showinfo("Rules", "Select a profile first.", parent=win)
                return
            profiles[idx].rules.append(
                _rules_mod.Rule(name=f"Rule {len(profiles[idx].rules) + 1}"))
            refresh_rule_list()
            rule_listbox.selection_set(len(profiles[idx].rules) - 1)
            on_rule_select(None)

        def delete_rule():
            p_idx = selected_profile_idx[0]
            r_idx = selected_rule_idx[0]
            if p_idx is None or r_idx is None:
                return
            profiles[p_idx].rules.pop(r_idx)
            selected_rule_idx[0] = None
            refresh_rule_list()
            clear_rule_editor()

        btn_add_rule = PillButton(rules_toolbar, text="+ Add Rule", font=_FONT_SMALL,
                                  style="secondary", padx=10, pady=4, command=add_rule)
        btn_add_rule.pack(side="right", padx=(4, 0))
        btn_add_rule.set_colors(
            fill=t["bg"], fg=t["accent"], outline=t["border"],
            hover_fill=t["bg"], hover_fg=t["accent"], hover_outline=t["accent"],
            parent_bg=t["bg"])

        btn_del_rule = PillButton(rules_toolbar, text="Delete Rule", font=_FONT_SMALL,
                                  style="secondary", padx=10, pady=4, command=delete_rule)
        btn_del_rule.pack(side="right", padx=(4, 0))
        btn_del_rule.set_colors(
            fill=t["bg"], fg=t["accent"], outline=t["border"],
            hover_fill=t["bg"], hover_fg=t["accent"], hover_outline=t["accent"],
            parent_bg=t["bg"])

        # Rule listbox
        rule_listbox = tk.Listbox(
            right, bd=0, highlightthickness=1, font=_FONT_SMALL,
            bg=t["bg"], fg=t["text"], selectbackground=t["accent"],
            selectforeground=t["text_on_accent"],
            highlightbackground=t["border"], height=6,
        )
        rule_listbox.grid(row=1, column=0, sticky="nsew")
        self._bind_scroll(rule_listbox)

        # Rule editor fields
        editor = tk.Frame(right, bg=t["bg"])
        editor.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        editor.grid_columnconfigure(1, weight=1)

        _entry_bg = t.get("sidebar_bg", t["bg"])

        tk.Label(editor, text="Name:", font=_FONT_SMALL, bg=t["bg"], fg=t["text"]).grid(
            row=0, column=0, sticky="w", pady=2)
        rule_name_var = tk.StringVar()
        rule_name_entry = tk.Entry(editor, textvariable=rule_name_var, font=_FONT_SMALL,
                                   bg=_entry_bg, fg=t["text"], insertbackground=t["text"],
                                   relief="flat", highlightthickness=1,
                                   highlightbackground=t["border"])
        rule_name_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0), pady=2)

        tk.Label(editor, text="Find:", font=_FONT_SMALL, bg=t["bg"], fg=t["text"]).grid(
            row=1, column=0, sticky="w", pady=2)
        rule_pattern_var = tk.StringVar()
        rule_pattern_entry = tk.Entry(editor, textvariable=rule_pattern_var, font=_FONT_SMALL,
                                      bg=_entry_bg, fg=t["text"], insertbackground=t["text"],
                                      relief="flat", highlightthickness=1,
                                      highlightbackground=t["border"])
        rule_pattern_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=2)

        tk.Label(editor, text="Replace:", font=_FONT_SMALL, bg=t["bg"], fg=t["text"]).grid(
            row=2, column=0, sticky="w", pady=2)
        rule_replace_var = tk.StringVar()
        rule_replace_entry = tk.Entry(editor, textvariable=rule_replace_var, font=_FONT_SMALL,
                                      bg=_entry_bg, fg=t["text"], insertbackground=t["text"],
                                      relief="flat", highlightthickness=1,
                                      highlightbackground=t["border"])
        rule_replace_entry.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=2)

        rule_opts_row = tk.Frame(editor, bg=t["bg"])
        rule_opts_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        rule_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(rule_opts_row, text="Enabled", variable=rule_enabled_var,
                       bg=t["bg"], fg=t["text"], selectcolor=t["bg"],
                       activebackground=t["bg"], activeforeground=t["text"],
                       font=_FONT_SMALL).pack(side="left", padx=(0, 16))

        rule_regex_var = tk.BooleanVar(value=True)
        tk.Checkbutton(rule_opts_row, text="Use Regex", variable=rule_regex_var,
                       bg=t["bg"], fg=t["text"], selectcolor=t["bg"],
                       activebackground=t["bg"], activeforeground=t["text"],
                       font=_FONT_SMALL).pack(side="left")

        def save_current_rule(*_):
            p_idx = selected_profile_idx[0]
            r_idx = selected_rule_idx[0]
            if p_idx is None or r_idx is None:
                return
            rule = profiles[p_idx].rules[r_idx]
            rule.name = rule_name_var.get()
            rule.pattern = rule_pattern_var.get()
            rule.replacement = rule_replace_var.get()
            rule.enabled = rule_enabled_var.get()
            rule.use_regex = rule_regex_var.get()
            refresh_rule_list()

        _rule_traces = []
        _rule_traces.append(("write", rule_name_var, rule_name_var.trace_add("write", save_current_rule)))
        _rule_traces.append(("write", rule_pattern_var, rule_pattern_var.trace_add("write", save_current_rule)))
        _rule_traces.append(("write", rule_replace_var, rule_replace_var.trace_add("write", save_current_rule)))
        _rule_traces.append(("write", rule_enabled_var, rule_enabled_var.trace_add("write", save_current_rule)))
        _rule_traces.append(("write", rule_regex_var, rule_regex_var.trace_add("write", save_current_rule)))

        def clear_rule_editor():
            rule_name_var.set("")
            rule_pattern_var.set("")
            rule_replace_var.set("")
            rule_enabled_var.set(True)
            rule_regex_var.set(True)

        # ── List refresh helpers ─────────────────────────────
        def refresh_profile_list():
            profile_listbox.delete(0, "end")
            for p in profiles:
                profile_listbox.insert("end", f"{p.name} ({len(p.rules)} rules)")

        def refresh_rule_list():
            rule_listbox.delete(0, "end")
            p_idx = selected_profile_idx[0]
            if p_idx is None or p_idx >= len(profiles):
                return
            for rule in profiles[p_idx].rules:
                prefix = "✓" if rule.enabled else "✗"
                rule_listbox.insert("end", f" {prefix}  {rule.name}")

        def on_profile_select(event):
            sel = profile_listbox.curselection()
            if not sel:
                return
            selected_profile_idx[0] = sel[0]
            selected_rule_idx[0] = None
            refresh_rule_list()
            clear_rule_editor()

        def on_rule_select(event):
            sel = rule_listbox.curselection()
            p_idx = selected_profile_idx[0]
            if not sel or p_idx is None:
                return
            r_idx = sel[0]
            selected_rule_idx[0] = r_idx
            rule = profiles[p_idx].rules[r_idx]
            rule_name_var.set(rule.name)
            rule_pattern_var.set(rule.pattern)
            rule_replace_var.set(rule.replacement)
            rule_enabled_var.set(rule.enabled)
            rule_regex_var.set(rule.use_regex)

        profile_listbox.bind("<<ListboxSelect>>", on_profile_select)
        rule_listbox.bind("<<ListboxSelect>>", on_rule_select)

        # ── Bottom buttons ───────────────────────────────────
        bottom = tk.Frame(win, bg=t["bg"])
        bottom.pack(fill="x", padx=16, pady=(0, 12))

        def preview_rules():
            p_idx = selected_profile_idx[0]
            if p_idx is None:
                messagebox.showinfo("Preview", "Select a profile first.", parent=win)
                return
            profile = profiles[p_idx]
            sample = (
                "# Sample Document\n\n"
                "CONFIDENTIAL — Internal Use Only\n\n"
                "Page 1 of 5\n\n"
                "This is sample text for testing rules.\n\n"
                "Date: 01/15/2025\n\n"
                "CONFIDENTIAL — Internal Use Only\n"
            )
            _after, changes = profile.preview(sample)
            msg = "Rule preview (against sample text):\n\n"
            for c in changes:
                msg += f"  • {c}\n"
            if not changes:
                msg += "  No rules in this profile."
            msg += f"\n--- Before ---\n{sample[:200]}\n\n--- After ---\n{_after[:200]}"
            messagebox.showinfo("Rule Preview", msg, parent=win)

        def _cleanup_rule_traces():
            for mode, var, tid in _rule_traces:
                try:
                    var.trace_remove(mode, tid)
                except Exception:
                    pass

        def save_and_close():
            self._rule_profiles = profiles
            _rules_mod.save_profiles(profiles)
            profile_names = ["None"] + [p.name for p in profiles]
            self._rules_profile_dd.set_values(profile_names)
            _cleanup_rule_traces()
            if self._scroll_target in (profile_listbox, rule_listbox):
                self._scroll_target = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", save_and_close)

        btn_preview = PillButton(bottom, text="Preview Rules", font=_FONT_SMALL,
                                 style="secondary", padx=14, pady=6, command=preview_rules)
        btn_preview.pack(side="left")
        btn_preview.set_colors(
            fill=t["bg"], fg=t["accent"], outline=t["border"],
            hover_fill=t["bg"], hover_fg=t["accent"], hover_outline=t["accent"],
            parent_bg=t["bg"])

        btn_save = PillButton(bottom, text="Save & Close", font=_FONT_BTN,
                              style="primary", padx=20, pady=8, command=save_and_close)
        btn_save.pack(side="right")
        btn_save.set_colors(
            fill=t["accent"], fg=t["text_on_accent"],
            hover_fill=t["accent_hover"], hover_fg=t["text_on_accent"],
            parent_bg=t["bg"])

        refresh_profile_list()

    # ── Preview window ─────────────────────────────────────

    def _show_preview_window(self):
        """Open a side-by-side preview: source info on the left, converted markdown on the right."""
        result = self._last_batch_result
        if result is None or not result.output_root:
            messagebox.showinfo("Preview", "No conversion results available yet.")
            return

        t = self._t
        win = tk.Toplevel(self.root)
        win.title("Preview — Source vs. Converted Output")
        win.geometry(f"{int(1100 * self._dpi)}x{int(650 * self._dpi)}")
        win.minsize(int(800 * self._dpi), int(400 * self._dpi))
        win.config(bg=t["bg"])
        self._set_titlebar_dark(self._dark, win)

        # ── File selector at top ─────────────────────────────
        top_bar = tk.Frame(win, bg=t["content_bg"])
        top_bar.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(top_bar, text="File:", font=_FONT_SMALL,
                 bg=t["content_bg"], fg=t["text"]).pack(side="left", padx=(0, 8))

        # Collect output files
        output_files = []
        if os.path.isdir(result.output_root):
            for root_dir, dirs, files in os.walk(result.output_root):
                for fname in files:
                    if fname.endswith((".md", ".json", ".html", ".txt", ".jsonl")):
                        output_files.append(os.path.join(root_dir, fname))
        output_files.sort()

        if not output_files:
            messagebox.showinfo("Preview", "No output files found in the output folder.")
            win.destroy()
            return

        file_display_names = [os.path.relpath(f, result.output_root) for f in output_files]
        file_var = tk.StringVar(value=file_display_names[0])

        # ── Copy buttons (pack BEFORE expanding selector) ────
        current_content = [""]  # mutable container for raw markdown

        def _copy_to_clipboard():
            win.clipboard_clear()
            win.clipboard_append(current_content[0])
            btn_copy.set_text("✓ Copied")
            win.after(1500, lambda: btn_copy.set_text("Copy Markdown")
                      if win.winfo_exists() else None)

        def _copy_formatted():
            """Copy as rich HTML so pasting into Word/Docs preserves formatting."""
            md_text = current_content[0]
            try:
                import markdown as _md_lib
                html = _md_lib.markdown(
                    md_text, extensions=["tables", "fenced_code"])
            except ImportError:
                # Minimal fallback — wrap in <pre> if markdown lib missing
                html = f"<pre>{md_text}</pre>"
            if sys.platform == "win32":
                _copy_html_win32(html)
            else:
                # macOS / Linux: plain HTML on clipboard via tkinter
                win.clipboard_clear()
                win.clipboard_append(html)
            btn_copy_fmt.set_text("✓ Copied")
            win.after(1500, lambda: btn_copy_fmt.set_text("Copy Rich")
                      if win.winfo_exists() else None)

        def _copy_html_win32(html: str):
            """Put HTML on the Windows clipboard using CF_HTML format."""
            try:
                import ctypes
                from ctypes import wintypes
                CF_HTML = ctypes.windll.user32.RegisterClipboardFormatW("HTML Format")
                # Build CF_HTML envelope
                header = (
                    "Version:0.9\r\n"
                    "StartHTML:{:08d}\r\n"
                    "EndHTML:{:08d}\r\n"
                    "StartFragment:{:08d}\r\n"
                    "EndFragment:{:08d}\r\n"
                )
                prefix = "<!--StartFragment-->"
                suffix = "<!--EndFragment-->"
                dummy_header = header.format(0, 0, 0, 0)
                start_html = len(dummy_header.encode("utf-8"))
                start_frag = start_html + len(prefix.encode("utf-8"))
                end_frag = start_frag + len(html.encode("utf-8"))
                end_html = end_frag + len(suffix.encode("utf-8"))
                blob = header.format(start_html, end_html, start_frag, end_frag)
                blob += prefix + html + suffix
                data = blob.encode("utf-8") + b"\x00"

                ctypes.windll.user32.OpenClipboard(0)
                ctypes.windll.user32.EmptyClipboard()
                # Also set plain text
                win.clipboard_clear()
                win.clipboard_append(current_content[0])
                # Set HTML format
                h_mem = ctypes.windll.kernel32.GlobalAlloc(0x0042, len(data))
                p = ctypes.windll.kernel32.GlobalLock(h_mem)
                ctypes.memmove(p, data, len(data))
                ctypes.windll.kernel32.GlobalUnlock(h_mem)
                ctypes.windll.user32.SetClipboardData(CF_HTML, h_mem)
                ctypes.windll.user32.CloseClipboard()
            except Exception:
                # Fallback: just copy plain markdown
                win.clipboard_clear()
                win.clipboard_append(current_content[0])

        # Spell check state
        spell_active = [False]
        _spell_checker = [None]  # lazy-loaded SpellChecker instance

        def _toggle_spell_check():
            spell_active[0] = not spell_active[0]
            if spell_active[0]:
                btn_spell.set_text("✓ Spell")
                _run_spell_check()
            else:
                btn_spell.set_text("Spell")
                preview_text.config(state="normal")
                preview_text.tag_remove("misspelled", "1.0", tk.END)
                preview_text.config(state="disabled")

        def _run_spell_check():
            """Flag misspelled words with red underline."""
            if not spell_active[0]:
                return
            try:
                if _spell_checker[0] is None:
                    from spellchecker import SpellChecker
                    _spell_checker[0] = SpellChecker()
                spell = _spell_checker[0]
            except ImportError:
                btn_spell.set_text("N/A")
                return

            preview_text.config(state="normal")
            preview_text.tag_remove("misspelled", "1.0", tk.END)

            content = preview_text.get("1.0", tk.END)
            lines = content.split("\n")
            _word_re = re.compile(r"[a-zA-Z']{3,}")
            spell_ranges: list[str] = []

            for ln_num, line in enumerate(lines, 1):
                for m in _word_re.finditer(line):
                    word = m.group()
                    if word.lower() not in spell.word_frequency:
                        if spell.unknown([word]):
                            spell_ranges.extend([
                                f"{ln_num}.{m.start()}",
                                f"{ln_num}.{m.end()}"])
            if spell_ranges:
                preview_text.tag_add("misspelled", *spell_ranges)
            preview_text.config(state="disabled")

        # Confidence heatmap state
        heatmap_active = [False]

        def _toggle_heatmap():
            heatmap_active[0] = not heatmap_active[0]
            if heatmap_active[0]:
                btn_heatmap.set_text("✓ Heatmap")
                _apply_heatmap()
            else:
                btn_heatmap.set_text("Heatmap")
                preview_text.config(state="normal")
                preview_text.tag_remove("conf_high", "1.0", tk.END)
                preview_text.tag_remove("conf_medium", "1.0", tk.END)
                preview_text.tag_remove("conf_low", "1.0", tk.END)
                preview_text.config(state="disabled")

        def _apply_heatmap():
            """Color-code the preview based on confidence scores."""
            if not heatmap_active[0]:
                return
            rel_path = file_var.get()
            try:
                idx = file_display_names.index(rel_path)
            except ValueError:
                return
            full_path_h = output_files[idx]
            stem = os.path.splitext(os.path.basename(full_path_h))[0]

            # Find the matching confidence result
            conf_obj = None
            if result.all_confidence:
                for c in result.all_confidence:
                    cs = os.path.splitext(os.path.basename(
                        c.source_file))[0] if c.source_file else ""
                    if cs == stem:
                        conf_obj = c
                        break

            if not conf_obj:
                return

            # Determine the overall tag to apply
            overall = (conf_obj.overall or "").lower()
            if overall in ("high",):
                conf_tag = "conf_high"
            elif overall in ("medium", "moderate"):
                conf_tag = "conf_medium"
            else:
                conf_tag = "conf_low"

            # Apply to the entire document as base tint
            preview_text.config(state="normal")
            preview_text.tag_remove("conf_high", "1.0", tk.END)
            preview_text.tag_remove("conf_medium", "1.0", tk.END)
            preview_text.tag_remove("conf_low", "1.0", tk.END)

            total_lines = int(preview_text.index("end-1c").split(".")[0])

            # Apply per-dimension coloring to sections
            # Tables get table_structure confidence
            # Images get image_extraction confidence
            # Regular text gets text_extraction confidence
            content = preview_text.get("1.0", tk.END)
            lines = content.split("\n")

            for ln_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if not stripped:
                    continue
                # Determine which dimension applies
                if stripped.startswith("|"):
                    dim = (conf_obj.table_structure or "").lower()
                elif stripped.startswith("![") or stripped.startswith("🖼"):
                    dim = (conf_obj.image_extraction or "").lower()
                else:
                    dim = (conf_obj.text_extraction or "").lower()

                if dim in ("n/a", ""):
                    dim = overall
                if dim in ("high",):
                    tag = "conf_high"
                elif dim in ("medium", "moderate"):
                    tag = "conf_medium"
                elif dim in ("low", "failed"):
                    tag = "conf_low"
                else:
                    tag = conf_tag
                preview_text.tag_add(tag, f"{ln_num}.0", f"{ln_num}.end+1c")

            preview_text.config(state="disabled")

        # ── Toolbar separator: visual dividers between button groups ──
        def _toolbar_sep():
            sep = tk.Frame(top_bar, width=1, bg=t["border"])
            sep.pack(side="right", fill="y", padx=6, pady=4)
            return sep

        # ── Analysis tools (right side, packed right-to-left) ──
        btn_heatmap = PillButton(
            top_bar, text="Heatmap", font=_FONT_SMALL,
            style="secondary", padx=12, pady=5,
            command=_toggle_heatmap,
        )
        btn_heatmap.pack(side="right", padx=(4, 0))
        btn_heatmap.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )
        Tooltip(btn_heatmap,
                "Color-code the preview by conversion confidence. Green = high confidence, "
                "yellow = medium, red = low. Tables and images are scored separately from text.",
                lambda: self._t)

        btn_spell = PillButton(
            top_bar, text="Spell", font=_FONT_SMALL,
            style="secondary", padx=12, pady=5,
            command=_toggle_spell_check,
        )
        btn_spell.pack(side="right", padx=(4, 0))
        btn_spell.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )
        Tooltip(btn_spell,
                "Toggle offline spell check. Misspelled words are underlined in red. "
                "Useful for catching OCR errors in scanned documents.",
                lambda: self._t)

        _toolbar_sep()  # ── divider between analysis and clipboard tools ──

        # ── Clipboard tools ──
        btn_copy_fmt = PillButton(
            top_bar, text="Copy Rich", font=_FONT_SMALL,
            style="secondary", padx=12, pady=5,
            command=_copy_formatted,
        )
        btn_copy_fmt.pack(side="right", padx=(4, 0))
        btn_copy_fmt.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )
        Tooltip(btn_copy_fmt,
                "Copy as formatted HTML. Paste into Word, Google Docs, or email "
                "to preserve headings, tables, and code block formatting.",
                lambda: self._t)

        btn_copy = PillButton(
            top_bar, text="Copy Markdown", font=_FONT_SMALL,
            style="secondary", padx=12, pady=5,
            command=_copy_to_clipboard,
        )
        btn_copy.pack(side="right", padx=(4, 0))
        btn_copy.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )
        Tooltip(btn_copy,
                "Copy the raw Markdown source to your clipboard.",
                lambda: self._t)

        _toolbar_sep()  # ── divider between clipboard tools and file selector ──

        # File selector (packed after right-side buttons so it expands into remaining space)
        file_selector = GlassDropdown(
            top_bar, variable=file_var, options=file_display_names,
            font=_FONT_SMALL)
        file_selector.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Theme the dropdown (GlassDropdown uses 'border', not 'outline')
        file_selector.set_colors(
            fill=t["content_bg"],
            fg=t["text"],
            border=t["border"],
            hover_fill=t["content_bg"],
            parent_bg=t["content_bg"],
        )

        # ── Paned window: left = source info, right = preview ─
        paned = tk.PanedWindow(
            win, orient="horizontal", bg=t["border"],
            sashwidth=4, sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # ── Left panel: source info + source pages ────────────
        left_frame = tk.Frame(paned, bg=t["bg"])
        paned.add(left_frame, width=int(380 * self._dpi), minsize=int(200 * self._dpi))

        # Tab switcher: Info | Pages
        left_tab_bar = tk.Frame(left_frame, bg=t["bg"])
        left_tab_bar.pack(fill="x", padx=12, pady=(12, 4))
        left_tab_var = tk.StringVar(value="info")

        source_page_images: list = []  # prevent GC of page PhotoImages

        def _set_left_tab(tab: str):
            left_tab_var.set(tab)
            _lbl_info_tab.config(
                fg=t["accent"] if tab == "info" else t["text_secondary"])
            _lbl_pages_tab.config(
                fg=t["accent"] if tab == "pages" else t["text_secondary"])
            if tab == "info":
                source_pages_frame.pack_forget()
                source_text.pack(fill="both", expand=True)
            else:
                source_text.pack_forget()
                source_pages_frame.pack(fill="both", expand=True)

        _lbl_info_tab = tk.Label(
            left_tab_bar, text="SOURCE INFO", font=_FONT_SECTION,
            bg=t["bg"], fg=t["accent"], cursor="hand2",
        )
        _lbl_info_tab.pack(side="left")
        _lbl_info_tab.bind("<Button-1>", lambda _: _set_left_tab("info"))
        Tooltip(_lbl_info_tab,
                "File metadata, confidence scores, and conversion notes for the selected document.",
                lambda: self._t)

        tk.Label(left_tab_bar, text="  │  ", font=_FONT_SECTION,
                 bg=t["bg"], fg=t["border"]).pack(side="left")

        _lbl_pages_tab = tk.Label(
            left_tab_bar, text="SOURCE PAGES", font=_FONT_SECTION,
            bg=t["bg"], fg=t["text_secondary"], cursor="hand2",
        )
        _lbl_pages_tab.pack(side="left")
        _lbl_pages_tab.bind("<Button-1>", lambda _: _set_left_tab("pages"))
        Tooltip(_lbl_pages_tab,
                "Rendered page thumbnails from the original source document. "
                "Supported for PDF and image files.",
                lambda: self._t)

        tk.Frame(left_frame, height=1, bg=t["border"]).pack(fill="x", padx=12, pady=(0, 8))

        # Info view (shown by default)
        source_text = tk.Text(
            left_frame, font=_FONT_SMALL, wrap="word",
            bg=t["bg"], fg=t["text"],
            bd=0, highlightthickness=0,
            padx=12, pady=8, state="disabled",
        )
        source_text.pack(fill="both", expand=True)
        self._bind_scroll(source_text)

        # Pages view (scrollable canvas for rendered source pages)
        source_pages_frame = tk.Frame(left_frame, bg=t["bg"])
        # Not packed initially — toggled by tab click

        pages_canvas = tk.Canvas(source_pages_frame, bg=t["bg"],
                                 highlightthickness=0)
        pages_sb = GlassScrollbar(source_pages_frame, orient="vertical",
                                  command=pages_canvas.yview)
        pages_sb.set_colors(thumb=t["scrollbar_thumb"],
                            thumb_hover=t["scrollbar_hover"],
                            parent_bg=t["bg"])
        pages_inner = tk.Frame(pages_canvas, bg=t["bg"])
        pages_canvas.create_window((0, 0), window=pages_inner, anchor="nw")
        pages_inner.bind("<Configure>", lambda e: pages_canvas.configure(
            scrollregion=pages_canvas.bbox("all")))
        pages_canvas.configure(yscrollcommand=pages_sb.set)
        pages_canvas.pack(side="left", fill="both", expand=True)
        pages_sb.pack(side="right", fill="y")

        # Mousewheel scroll for pages canvas
        pages_canvas.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', pages_canvas))
        pages_canvas.bind(
            "<Leave>", lambda _e: setattr(self, '_scroll_target', None)
            if self._scroll_target is pages_canvas else None)
        pages_inner.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', pages_canvas))

        def _render_source_pages(source_path: str):
            """Render source document pages into the Pages tab."""
            # Clear previous
            for w in pages_inner.winfo_children():
                w.destroy()
            source_page_images.clear()

            ext = os.path.splitext(source_path)[1].lower()

            if ext == ".pdf":
                _render_pdf_pages(source_path)
            elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff",
                         ".tif", ".webp", ".gif"):
                _render_image_page(source_path)
            else:
                tk.Label(
                    pages_inner,
                    text=f"Page preview not available for {ext} files.\n\n"
                         "Supported: PDF, PNG, JPG, BMP, TIFF, WebP, GIF",
                    font=_FONT_SMALL, fg=t["text_secondary"], bg=t["bg"],
                    wraplength=int(300 * self._dpi), justify="center",
                ).pack(pady=40)

        def _render_pdf_pages(pdf_path: str):
            """Render PDF pages as images using PyMuPDF."""
            try:
                import fitz
                doc = fitz.open(pdf_path)
            except Exception:
                tk.Label(pages_inner, text="Could not open PDF",
                         font=_FONT_SMALL, fg=t["text_secondary"],
                         bg=t["bg"]).pack(pady=40)
                return

            panel_w = int(340 * self._dpi)
            zoom = panel_w / 612.0  # 612 = standard US Letter width in pts
            mat = fitz.Matrix(zoom, zoom)

            for page_num in range(min(doc.page_count, 50)):  # cap at 50 pages
                try:
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=mat)
                    from PIL import Image as _PILImage, ImageTk as _PILImageTk
                    img = _PILImage.frombytes("RGB",
                                              [pix.width, pix.height],
                                              pix.samples)
                    photo = _PILImageTk.PhotoImage(img)
                    source_page_images.append(photo)

                    # Page number label
                    tk.Label(
                        pages_inner,
                        text=f"— Page {page_num + 1} —",
                        font=(_FONT_FAMILY, 9), fg=t["text_secondary"],
                        bg=t["bg"],
                    ).pack(pady=(8, 2))

                    lbl = tk.Label(pages_inner, image=photo, bg=t["bg"])
                    lbl.pack(padx=8, pady=(0, 4))
                except Exception:
                    continue
            doc.close()

        def _render_image_page(img_path: str):
            """Render a single image source file."""
            try:
                from PIL import Image as _PILImage, ImageTk as _PILImageTk
                img = _PILImage.open(img_path)
                panel_w = int(340 * self._dpi)
                if img.width > panel_w:
                    ratio = panel_w / img.width
                    img = img.resize(
                        (panel_w, int(img.height * ratio)),
                        _PILImage.LANCZOS)
                photo = _PILImageTk.PhotoImage(img)
                source_page_images.append(photo)
                lbl = tk.Label(pages_inner, image=photo, bg=t["bg"])
                lbl.pack(padx=8, pady=8)
            except Exception:
                tk.Label(pages_inner, text="Could not load image",
                         font=_FONT_SMALL, fg=t["text_secondary"],
                         bg=t["bg"]).pack(pady=40)

        # ── Right panel: markdown preview ────────────────────
        right_frame = tk.Frame(paned, bg=t["bg"])
        paned.add(right_frame, minsize=int(300 * self._dpi))

        _output_hdr_row = tk.Frame(right_frame, bg=t["bg"])
        _output_hdr_row.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(_output_hdr_row, text="CONVERTED OUTPUT", font=_FONT_SECTION,
                 bg=t["bg"], fg=t["text_secondary"], anchor="w"
                 ).pack(side="left")
        _shortcut_lbl = tk.Label(
            _output_hdr_row, text="Ctrl+F to search", font=(_FONT_FAMILY, 8),
            bg=t["bg"], fg=t["border"],
        )
        _shortcut_lbl.pack(side="right")
        tk.Frame(right_frame, height=1, bg=t["border"]).pack(fill="x", padx=12, pady=(0, 8))

        # ── Search & Replace bar (hidden by default) ─────────
        search_bar = tk.Frame(right_frame, bg=t["content_bg"])
        # Not packed initially — toggled by Ctrl+F

        # Row 1: find entry + navigation
        search_row1 = tk.Frame(search_bar, bg=t["content_bg"])
        search_row1.pack(fill="x")

        search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_row1, textvariable=search_var, font=_FONT_SMALL,
            bg=t["bg"], fg=t["text"], insertbackground=t["text"],
            bd=0, highlightthickness=1, highlightcolor=t["accent"],
            highlightbackground=t["border"],
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=4)

        search_count_lbl = tk.Label(
            search_row1, text="", font=_FONT_SMALL,
            bg=t["content_bg"], fg=t["text_secondary"],
        )
        search_count_lbl.pack(side="left", padx=(0, 4))

        # Regex toggle
        regex_on = tk.BooleanVar(value=False)
        regex_btn = tk.Label(
            search_row1, text=".*", font=(_FONT_MONO, 10, "bold"),
            bg=t["content_bg"], fg=t["text_secondary"],
            cursor="hand2", padx=4,
        )
        regex_btn.pack(side="left", padx=2, pady=4)
        Tooltip(regex_btn,
                "Toggle regular expression mode. When active, your search "
                "pattern is treated as a regex (e.g. \\d+ matches numbers).",
                lambda: self._t)

        def _toggle_regex(_e=None):
            regex_on.set(not regex_on.get())
            regex_btn.config(
                fg=t["accent"] if regex_on.get() else t["text_secondary"])
            _do_search()
        regex_btn.bind("<Button-1>", _toggle_regex)

        btn_prev_match = PillButton(
            search_row1, text="▲", font=_FONT_SMALL,
            style="secondary", padx=6, pady=3, command=lambda: _prev_match(),
        )
        btn_prev_match.pack(side="left", padx=1, pady=4)
        btn_prev_match.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )

        btn_next_match = PillButton(
            search_row1, text="▼", font=_FONT_SMALL,
            style="secondary", padx=6, pady=3, command=lambda: _next_match(),
        )
        btn_next_match.pack(side="left", padx=1, pady=4)
        btn_next_match.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )

        btn_close_search = PillButton(
            search_row1, text="✕", font=_FONT_SMALL,
            style="secondary", padx=6, pady=3, command=lambda: _close_search(),
        )
        btn_close_search.pack(side="right", padx=(2, 8), pady=4)
        btn_close_search.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )

        # Row 2: replace entry + buttons
        replace_row = tk.Frame(search_bar, bg=t["content_bg"])
        replace_row.pack(fill="x")

        replace_var = tk.StringVar()
        replace_entry = tk.Entry(
            replace_row, textvariable=replace_var, font=_FONT_SMALL,
            bg=t["bg"], fg=t["text"], insertbackground=t["text"],
            bd=0, highlightthickness=1, highlightcolor=t["accent"],
            highlightbackground=t["border"],
        )
        replace_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=(0, 4))

        btn_replace = PillButton(
            replace_row, text="Replace", font=_FONT_SMALL,
            style="secondary", padx=8, pady=3,
            command=lambda: _replace_current(),
        )
        btn_replace.pack(side="left", padx=2, pady=(0, 4))
        btn_replace.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )
        Tooltip(btn_replace,
                "Replace the current match and advance to the next one.",
                lambda: self._t)

        btn_replace_all = PillButton(
            replace_row, text="All", font=_FONT_SMALL,
            style="secondary", padx=8, pady=3,
            command=lambda: _replace_all(),
        )
        btn_replace_all.pack(side="left", padx=(2, 8), pady=(0, 4))
        btn_replace_all.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )
        Tooltip(btn_replace_all,
                "Replace every match in the document at once.",
                lambda: self._t)

        search_matches = []      # list of (start_pos, end_pos) tuples
        search_current_idx = [0]  # mutable index
        search_visible = [False]
        search_debounce_id = [None]  # pending after() id for debounce
        deferred_after_ids = []     # fire-and-forget after() IDs to cancel on close

        preview_frame = tk.Frame(right_frame, bg=t["bg"])
        preview_frame.pack(fill="both", expand=True)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        preview_text = tk.Text(
            preview_frame, font=(_FONT_MONO, 11), wrap="none",
            bg=t["bg"], fg=t["text"],
            bd=0, highlightthickness=0,
            padx=12, pady=8, state="disabled",
            maxundo=0, undo=False,
        )
        preview_sb = GlassScrollbar(
            preview_frame, orient="vertical", command=preview_text.yview)
        _sb_thumb = t["scrollbar_thumb"]
        _sb_hover = t["scrollbar_hover"]
        preview_sb.set_colors(thumb=_sb_thumb, thumb_hover=_sb_hover, parent_bg=t["bg"])
        preview_text.config(yscrollcommand=preview_sb.set)

        # Horizontal scroll via Shift+MouseWheel (no visible scrollbar)
        def _hscroll(e):
            preview_text.xview_scroll(self._scroll_units(e), "units")
            return "break"
        preview_text.bind("<Shift-MouseWheel>", _hscroll)
        # Linux uses Shift-Button-4 / Shift-Button-5 for horizontal scroll
        preview_text.bind("<Shift-Button-4>",
                          lambda e: (preview_text.xview_scroll(-3, "units"), "break")[-1])
        preview_text.bind("<Shift-Button-5>",
                          lambda e: (preview_text.xview_scroll(3, "units"), "break")[-1])
        preview_text.grid(row=0, column=0, sticky="nsew")
        preview_sb.grid(row=0, column=1, sticky="ns")
        self._bind_scroll(preview_text)

        # ── Text tags for syntax highlighting ────────────────
        preview_text.tag_configure("heading", font=(_FONT_FAMILY, 14, "bold"), foreground=t["accent"])
        preview_text.tag_configure("heading2", font=(_FONT_FAMILY, 12, "bold"), foreground=t["accent"])
        preview_text.tag_configure("heading3", font=(_FONT_FAMILY, 11, "bold"), foreground=t["accent"])
        preview_text.tag_configure("bold", font=(_FONT_MONO, 11, "bold"))
        preview_text.tag_configure("frontmatter", foreground=t["text_secondary"], font=(_FONT_MONO, 10))
        preview_text.tag_configure("table", foreground="#8be9fd" if self._dark else "#0969da")
        preview_text.tag_configure("page_marker", foreground=t["text_secondary"], font=(_FONT_MONO, 10, "italic"))
        # New tags
        _code_bg = "#2a2a3d" if self._dark else "#eef0f4"
        preview_text.tag_configure("code_block", font=(_FONT_MONO, 10),
                                   background=_code_bg,
                                   foreground="#a9dc76" if self._dark else "#22863a",
                                   lmargin1=12, lmargin2=12, rmargin=12)
        preview_text.tag_configure("inline_code", font=(_FONT_MONO, 10),
                                   background=_code_bg)
        preview_text.tag_configure("blockquote", font=(_FONT_FAMILY, 11, "italic"),
                                   foreground=t["text_secondary"],
                                   lmargin1=24, lmargin2=24)
        preview_text.tag_configure("link", foreground=t["accent"], underline=True)
        preview_text.tag_configure("hr", foreground=t["border"],
                                   justify="center", font=(_FONT_MONO, 10))
        preview_text.tag_configure("list_bullet", foreground=t["accent"])
        preview_text.tag_configure("image_ref",
                                   foreground=t.get("accent_secondary", t["accent"]))
        # Confidence heatmap tags
        preview_text.tag_configure("conf_high",
                                   lmargin1=6,
                                   borderwidth=0,
                                   background="#0a2e0a" if self._dark else "#e6f9e6")
        preview_text.tag_configure("conf_medium",
                                   lmargin1=6,
                                   borderwidth=0,
                                   background="#2e2a0a" if self._dark else "#fff8e1")
        preview_text.tag_configure("conf_low",
                                   lmargin1=6,
                                   borderwidth=0,
                                   background="#2e0a0a" if self._dark else "#fde8e8")
        # Spell check tag
        preview_text.tag_configure("misspelled",
                                   underline=True,
                                   foreground="#ff6b6b" if self._dark else "#d63031",
                                   underlinefg="#ff6b6b" if self._dark else "#d63031")
        # Search tags (higher priority — raised above other tags)
        preview_text.tag_configure("search_match",
                                   background="#ffd700" if self._dark else "#ffeaa7",
                                   foreground="#000000")
        preview_text.tag_configure("search_active",
                                   background=t["accent"],
                                   foreground=t["text_on_accent"])
        preview_text.tag_raise("search_match")
        preview_text.tag_raise("search_active")
        preview_text.tag_raise("misspelled")

        # Image reference list (prevent GC of PhotoImages)
        preview_images: list = []
        image_load_id = [None]  # Pending after-ID for deferred _load_images

        # ── Inline formatting regexes ────────────────────────
        _RE_INLINE_CODE = re.compile(r'`([^`]+)`')
        _RE_BOLD = re.compile(r'\*\*([^*]+)\*\*')
        _RE_LINK = re.compile(r'\[([^\]]+)\]\([^)]+\)')

        # ── Image thumbnail helper ───────────────────────────
        _RE_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        _IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}
        _RE_LIST = re.compile(r'^(\s*)([-*]|\d+\.)\s')

        def _load_thumbnail(file_dir: str, img_rel: str):
            """Load an image, return (thumbnail PhotoImage, abs_path) or (None, None)."""
            if img_rel.startswith("data:"):
                return None, None
            abs_path = os.path.normpath(os.path.join(file_dir, img_rel))
            ext = os.path.splitext(abs_path)[1].lower()
            if ext not in _IMG_EXTS or not os.path.isfile(abs_path):
                return None, None
            try:
                from PIL import Image as _PILImage, ImageTk as _PILImageTk
                img = _PILImage.open(abs_path)
                max_w = 400
                if img.width > max_w:
                    ratio = max_w / img.width
                    img = img.resize(
                        (max_w, int(img.height * ratio)), _PILImage.LANCZOS)
                photo = _PILImageTk.PhotoImage(img)
                preview_images.append(photo)  # prevent GC
                return photo, abs_path
            except Exception:
                return None, None

        def _show_image_zoom(img_path: str):
            """Open a full-size image in a themed overlay window."""
            try:
                from PIL import Image as _PILImage, ImageTk as _PILImageTk
                img = _PILImage.open(img_path)
            except Exception:
                return

            zoom_win = tk.Toplevel(win)
            zoom_win.title(os.path.basename(img_path))
            zoom_win.config(bg=t["bg"])
            zoom_win.transient(win)
            self._set_titlebar_dark(self._dark, zoom_win)

            # Fit image to screen (max 90% of screen dimensions)
            screen_w = zoom_win.winfo_screenwidth()
            screen_h = zoom_win.winfo_screenheight()
            max_w = int(screen_w * 0.9)
            max_h = int(screen_h * 0.85)
            display_img = img.copy()
            if display_img.width > max_w or display_img.height > max_h:
                display_img.thumbnail((max_w, max_h), _PILImage.LANCZOS)

            win_w = display_img.width + 24
            win_h = display_img.height + 60
            rx = self.root.winfo_x() + (self.root.winfo_width() - win_w) // 2
            ry = self.root.winfo_y() + (self.root.winfo_height() - win_h) // 2
            zoom_win.geometry(f"{win_w}x{win_h}+{max(0, rx)}+{max(0, ry)}")

            # Image label
            photo = _PILImageTk.PhotoImage(display_img)
            img_label = tk.Label(zoom_win, image=photo, bg=t["bg"])
            img_label.image = photo  # prevent GC
            img_label.pack(fill="both", expand=True, padx=12, pady=(8, 4))

            # Info bar
            info_text = (f"{os.path.basename(img_path)}  •  "
                         f"{img.width}×{img.height} px  •  "
                         f"{os.path.getsize(img_path) / 1024:.0f} KB")
            tk.Label(
                zoom_win, text=info_text, font=(_FONT_FAMILY, 9),
                fg=t["text_secondary"], bg=t["bg"],
            ).pack(pady=(0, 8))

            zoom_win.bind("<Escape>", lambda _: zoom_win.destroy())
            zoom_win.focus_set()

        # ── load_file — two-pass bulk parser ─────────────────
        # Pass 1: classify lines (pure Python, no widget calls)
        # Pass 2: single bulk insert + batch tag application
        # Images deferred to after_idle for instant window render

        def load_file(rel_path):
            # Cancel any pending deferred image load from previous file
            if image_load_id[0] is not None:
                try:
                    win.after_cancel(image_load_id[0])
                except Exception:
                    pass
                image_load_id[0] = None

            try:
                idx = file_display_names.index(rel_path)
            except ValueError:
                return
            full_path = output_files[idx]

            # ── Left panel: source info ──────────────────────
            source_info_lines = []
            stem = os.path.splitext(os.path.basename(full_path))[0]
            matched_source = None
            for src in self._selected_files:
                if os.path.splitext(os.path.basename(src))[0] == stem:
                    matched_source = src
                    break

            if matched_source and os.path.exists(matched_source):
                size = os.path.getsize(matched_source)
                size_str = f"{size / 1024:.1f} KB" if size < 1048576 else f"{size / 1048576:.1f} MB"
                ext = os.path.splitext(matched_source)[1].upper()
                source_info_lines.append(f"File: {os.path.basename(matched_source)}")
                source_info_lines.append(f"Type: {ext}")
                source_info_lines.append(f"Size: {size_str}")
                source_info_lines.append(f"Path: {matched_source}")
            else:
                source_info_lines.append(f"Source: {stem}")

            source_info_lines.append("")

            if result.all_confidence:
                for conf in result.all_confidence:
                    conf_stem = os.path.splitext(os.path.basename(
                        conf.source_file))[0] if conf.source_file else ""
                    if conf_stem == stem:
                        source_info_lines.append("── Confidence ──")
                        source_info_lines.append(f"  Overall:         {conf.overall or 'N/A'}")
                        source_info_lines.append(f"  Text extraction: {conf.text_extraction or 'N/A'}")
                        source_info_lines.append(f"  Table structure: {conf.table_structure or 'N/A'}")
                        source_info_lines.append(f"  Image extraction:{conf.image_extraction or 'N/A'}")
                        source_info_lines.append(f"  Document order:  {conf.document_order or 'N/A'}")
                        if conf.ocr_confidence:
                            source_info_lines.append(f"  OCR confidence:  {conf.ocr_confidence}")
                        if conf.notes:
                            source_info_lines.append("")
                            source_info_lines.append("── Notes ──")
                            for n in conf.notes:
                                source_info_lines.append(f"  • {n}")
                        if conf.warnings:
                            source_info_lines.append("")
                            source_info_lines.append("── Warnings ──")
                            for w in conf.warnings:
                                source_info_lines.append(f"  ⚠ {w}")
                        break

            source_text.config(state="normal")
            source_text.delete("1.0", tk.END)
            source_text.insert("1.0", "\n".join(source_info_lines))
            source_text.config(state="disabled")

            # Render source pages in background (deferred to avoid blocking)
            if matched_source:
                _id = win.after(100, lambda p=matched_source: _render_source_pages(p))
                deferred_after_ids.append(_id)

            # ── Right panel: converted markdown ──────────────
            try:
                with open(full_path, "r", encoding="utf-8") as fh:
                    content = fh.read()
            except Exception as e:
                content = f"Error reading file: {e}"

            current_content[0] = content
            file_dir = os.path.dirname(full_path)

            # ── Pass 1: classify every line (no widget calls) ─
            lines = content.split("\n")
            # Each entry: (tag_or_None, display_text)
            classified: list[tuple] = []
            img_entries: list[tuple] = []  # (line_index, img_rel_path)

            in_frontmatter = False
            in_code_block = False
            seen_content = False  # "no non-blank content seen yet"

            for line in lines:
                stripped = line.strip()

                if stripped == "---" and not seen_content:
                    in_frontmatter = True
                    classified.append(("frontmatter", line))
                    continue
                if stripped:
                    seen_content = True

                if in_frontmatter:
                    classified.append(("frontmatter", line))
                    if stripped == "---":
                        in_frontmatter = False
                    continue

                if stripped.startswith("```"):
                    in_code_block = not in_code_block
                    classified.append(("code_block", line))
                    continue
                if in_code_block:
                    classified.append(("code_block", line))
                    continue

                if (len(stripped) >= 3
                        and stripped[0] in "-*_"
                        and stripped == stripped[0] * len(stripped)):
                    classified.append(("hr", "─" * 50))
                    continue

                if line.startswith("# "):
                    classified.append(("heading", line))
                elif line.startswith("## "):
                    classified.append(("heading2", line))
                elif line.startswith(("### ", "#### ", "##### ", "###### ")):
                    classified.append(("heading3", line))
                elif stripped.startswith("|"):
                    classified.append(("table", line))
                elif stripped.startswith("*Page ") or '<a id="page-' in line:
                    classified.append(("page_marker", line))
                elif stripped.startswith("> ") or stripped == ">":
                    classified.append(("blockquote", line))
                else:
                    img_m = _RE_IMAGE.match(stripped)
                    if img_m:
                        classified.append(("image_ref", line))
                        img_entries.append((len(classified) - 1, img_m.group(2)))
                    else:
                        classified.append((None, line))

            # ── Pass 2: single bulk insert ────────────────────
            preview_text.config(state="normal")
            preview_text.delete("1.0", tk.END)
            preview_images.clear()

            full_text = "\n".join(disp for _, disp in classified)
            if full_text:
                preview_text.insert("1.0", full_text + "\n")

            # ── Pass 3: merge contiguous same-tag lines into runs ─
            # e.g. 50 frontmatter lines → 1 interval instead of 50
            tag_runs: dict[str, list[str]] = {}
            prev_tag = None
            run_start = 0
            run_end = 0

            for i, (tag, _) in enumerate(classified):
                ln = i + 1
                if tag is not None and tag == prev_tag:
                    run_end = ln              # extend current run
                else:
                    if prev_tag is not None:   # close previous run
                        tag_runs.setdefault(prev_tag, []).extend(
                            [f"{run_start}.0", f"{run_end}.end+1c"])
                    if tag is not None:        # start new run
                        run_start = ln
                        run_end = ln
                    prev_tag = tag

            if prev_tag is not None:           # close final run
                tag_runs.setdefault(prev_tag, []).extend(
                    [f"{run_start}.0", f"{run_end}.end+1c"])

            for tag, ranges in tag_runs.items():
                preview_text.tag_add(tag, *ranges)

            # ── Pass 4: batch inline formatting (one Tcl call per format)
            inline_ranges: dict[str, list[str]] = {}
            for i, (tag, text) in enumerate(classified):
                if tag is not None:
                    continue
                ln = i + 1
                list_m = _RE_LIST.match(text)
                if list_m:
                    inline_ranges.setdefault("list_bullet", []).extend(
                        [f"{ln}.0", f"{ln}.{list_m.end()}"])
                if "`" in text:
                    for m in _RE_INLINE_CODE.finditer(text):
                        inline_ranges.setdefault("inline_code", []).extend(
                            [f"{ln}.{m.start()}", f"{ln}.{m.end()}"])
                if "**" in text:
                    for m in _RE_BOLD.finditer(text):
                        inline_ranges.setdefault("bold", []).extend(
                            [f"{ln}.{m.start()}", f"{ln}.{m.end()}"])
                if "](" in text:
                    for m in _RE_LINK.finditer(text):
                        inline_ranges.setdefault("link", []).extend(
                            [f"{ln}.{m.start()}", f"{ln}.{m.end()}"])
            for tag, ranges in inline_ranges.items():
                preview_text.tag_add(tag, *ranges)

            preview_text.config(state="disabled")
            _clear_search_highlights()

            # ── Deferred: image thumbnails (non-blocking) ─────
            if img_entries:
                _current_file = full_path  # capture for identity check

                def _load_images():
                    image_load_id[0] = None
                    # Guard against destroyed window or stale file switch
                    try:
                        if not win.winfo_exists():
                            return
                    except Exception:
                        return
                    preview_text.config(state="normal")
                    offset = 0
                    for idx, img_rel in img_entries:
                        photo, abs_path = _load_thumbnail(file_dir, img_rel)
                        if photo:
                            ins_ln = idx + 1 + offset + 1
                            preview_text.insert(f"{ins_ln}.0", " \n")
                            preview_text.image_create(
                                f"{ins_ln}.0", image=photo)
                            # Bind click-to-zoom on the image line
                            tag_name = f"_img_{idx}"
                            preview_text.tag_add(
                                tag_name, f"{ins_ln}.0", f"{ins_ln}.end")
                            _p = abs_path  # capture for closure
                            preview_text.tag_bind(
                                tag_name, "<Button-1>",
                                lambda _e, p=_p: _show_image_zoom(p))
                            preview_text.tag_configure(
                                tag_name, foreground="", background="")
                            offset += 1
                    preview_text.config(state="disabled")
                    # Image insertion shifts line numbers — refresh search
                    # results so match positions stay correct.
                    if search_visible[0] and search_var.get():
                        _do_search()
                image_load_id[0] = win.after(50, _load_images)

            # Re-run overlays if active
            if spell_active[0]:
                deferred_after_ids.append(win.after(100, _run_spell_check))
            if heatmap_active[0]:
                deferred_after_ids.append(win.after(100, _apply_heatmap))

        # ── Search & Replace functions ───────────────────────
        def _toggle_search(_event=None):
            if search_visible[0]:
                _close_search()
            else:
                search_bar.pack(fill="x", before=preview_frame)
                search_visible[0] = True
                search_entry.focus_set()
                search_entry.select_range(0, tk.END)
            return "break"

        def _close_search(_event=None):
            search_bar.pack_forget()
            search_visible[0] = False
            _clear_search_highlights()
            preview_text.focus_set()
            return "break"

        def _clear_search_highlights():
            preview_text.config(state="normal")
            preview_text.tag_remove("search_match", "1.0", tk.END)
            preview_text.tag_remove("search_active", "1.0", tk.END)
            preview_text.config(state="disabled")
            search_matches.clear()
            search_current_idx[0] = 0
            search_count_lbl.config(text="")

        def _do_search(_event=None):
            _clear_search_highlights()
            query = search_var.get()
            if not query:
                return

            use_regex = regex_on.get()
            preview_text.config(state="normal")
            match_ranges: list[str] = []

            if use_regex:
                # Regex search across the full text content
                try:
                    pattern = re.compile(query, re.IGNORECASE | re.MULTILINE)
                except re.error:
                    search_count_lbl.config(text="bad regex")
                    preview_text.config(state="disabled")
                    return
                full = preview_text.get("1.0", tk.END)
                for m in pattern.finditer(full):
                    if not m.group():
                        continue
                    # Convert string offset to tk line.col index
                    s_off = m.start()
                    e_off = m.end()
                    s_line = full.count("\n", 0, s_off) + 1
                    s_col = s_off - full.rfind("\n", 0, s_off) - 1
                    e_line = full.count("\n", 0, e_off) + 1
                    e_col = e_off - full.rfind("\n", 0, e_off) - 1
                    start_idx = f"{s_line}.{s_col}"
                    end_idx = f"{e_line}.{e_col}"
                    search_matches.append((start_idx, end_idx))
                    match_ranges.extend([start_idx, end_idx])
            else:
                # Plain text search
                start = "1.0"
                count_var = tk.IntVar()
                while True:
                    pos = preview_text.search(
                        query, start, stopindex=tk.END,
                        nocase=True, count=count_var)
                    if not pos:
                        break
                    matched_len = count_var.get() or len(query)
                    end = f"{pos}+{matched_len}c"
                    search_matches.append((pos, end))
                    match_ranges.extend([pos, end])
                    start = end

            if match_ranges:
                preview_text.tag_add("search_match", *match_ranges)
            preview_text.config(state="disabled")

            if search_matches:
                search_current_idx[0] = 0
                _highlight_active()
                search_count_lbl.config(text=f"1/{len(search_matches)}")
            else:
                search_count_lbl.config(text="0 results")

        def _highlight_active():
            preview_text.config(state="normal")
            preview_text.tag_remove("search_active", "1.0", tk.END)
            if search_matches:
                s, e = search_matches[search_current_idx[0]]
                preview_text.tag_add("search_active", s, e)
                preview_text.see(s)
            preview_text.config(state="disabled")

        def _next_match():
            if not search_matches:
                return
            search_current_idx[0] = (search_current_idx[0] + 1) % len(search_matches)
            _highlight_active()
            search_count_lbl.config(
                text=f"{search_current_idx[0] + 1}/{len(search_matches)}")

        def _prev_match():
            if not search_matches:
                return
            search_current_idx[0] = (search_current_idx[0] - 1) % len(search_matches)
            _highlight_active()
            search_count_lbl.config(
                text=f"{search_current_idx[0] + 1}/{len(search_matches)}")

        def _replace_current():
            """Replace the currently active match and advance."""
            if not search_matches:
                return
            s, e = search_matches[search_current_idx[0]]
            replacement = replace_var.get()
            preview_text.config(state="normal")
            preview_text.delete(s, e)
            preview_text.insert(s, replacement)
            preview_text.config(state="disabled")
            # Update the raw content tracker
            current_content[0] = preview_text.get("1.0", tk.END).rstrip("\n")
            _do_search()  # re-scan after replacement

        def _replace_all():
            """Replace all matches at once."""
            if not search_matches:
                return
            replacement = replace_var.get()
            preview_text.config(state="normal")
            # Replace in reverse order so positions stay valid
            for s, e in reversed(search_matches):
                preview_text.delete(s, e)
                preview_text.insert(s, replacement)
            preview_text.config(state="disabled")
            current_content[0] = preview_text.get("1.0", tk.END).rstrip("\n")
            _do_search()

        # Debounced live search — fires 300ms after last keystroke
        def _on_search_key(_event=None):
            if search_debounce_id[0] is not None:
                win.after_cancel(search_debounce_id[0])
            search_debounce_id[0] = win.after(300, _do_search)

        # Search bindings
        search_entry.bind("<Return>", lambda _: _next_match())
        replace_entry.bind("<Return>", lambda _: _replace_current())
        search_entry.bind("<Escape>", _close_search)
        replace_entry.bind("<Escape>", _close_search)
        _search_trace = search_var.trace_add("write", _on_search_key)
        win.bind("<Control-f>", _toggle_search)
        win.bind("<Control-h>", _toggle_search)  # Ctrl+H also opens search

        # ── Status bar at bottom ─────────────────────────────
        status_bar = tk.Frame(win, bg=t["content_bg"])
        status_bar.pack(fill="x", side="bottom", padx=12, pady=(0, 6))
        _status_hint = tk.Label(
            status_bar,
            text="Ctrl+F  Search  │  Click images to zoom  │  Shift+Scroll  Horizontal scroll",
            font=(_FONT_FAMILY, 8), fg=t["text_secondary"], bg=t["content_bg"],
            anchor="w",
        )
        _status_hint.pack(side="left", padx=8, pady=2)

        # Load first file
        load_file(file_display_names[0])

        # Bind file selector changes
        _file_trace = file_var.trace_add("write", lambda *_: load_file(file_var.get()))

        # Cleanup pending after() IDs and traces on window close
        def _on_preview_close():
            if search_debounce_id[0] is not None:
                try: win.after_cancel(search_debounce_id[0])
                except Exception: pass
            if image_load_id[0] is not None:
                try: win.after_cancel(image_load_id[0])
                except Exception: pass
            for _aid in deferred_after_ids:
                try: win.after_cancel(_aid)
                except Exception: pass
            deferred_after_ids.clear()
            try: search_var.trace_remove("write", _search_trace)
            except Exception: pass
            try: file_var.trace_remove("write", _file_trace)
            except Exception: pass
            # Clear scroll target if it pointed to a widget inside this window
            try:
                st = self._scroll_target
                if st is not None and st.winfo_toplevel() is win:
                    self._scroll_target = None
            except Exception:
                pass
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_preview_close)

    # ── File picker logic ────────────────────────────────────

    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Select files to convert",
            filetypes=_FILETYPES,
        )
        if not paths:
            return
        added = 0
        for p in paths:
            p = os.path.normpath(p)
            if p not in self._selected_files:
                self._selected_files.append(p)
                added += 1
        if added:
            self._update_file_list()

    def _pick_folder_input(self):
        folder = filedialog.askdirectory(title="Select a folder to convert")
        if not folder:
            return
        folder = os.path.normpath(folder)
        found = []
        for dirpath, _dirs, filenames in os.walk(folder):
            for entry in sorted(filenames):
                if os.path.splitext(entry)[1].lower() in _SUPPORTED_EXTS:
                    found.append(os.path.join(dirpath, entry))
        if not found:
            messagebox.showinfo(
                "No Supported Files",
                f"No supported files were found in:\n{folder}\n\n"
                "Supported types: " + ", ".join(
                    sorted(e.lstrip(".").upper() for e in _SUPPORTED_EXTS)),
            )
            return
        self._show_folder_preview(folder, found)

    def _show_folder_preview(self, folder: str, found: list[str]):
        t = self._t
        dlg = tk.Toplevel(self.root)
        dlg.title("Confirm Files to Add")
        dlg.geometry("520x400")
        dlg.resizable(True, True)
        dlg.minsize(400, 300)
        self._set_titlebar_dark(self._dark, dlg)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.config(bg=t["content_bg"])

        already = set(self._selected_files)
        new_files = []
        dup_count = 0
        for f in found:
            if f in already:
                dup_count += 1
            else:
                new_files.append(f)

        # ── Header (top) ─────────────────────────────────────
        tk.Label(dlg, text=f"Found {len(found)} supported file(s) in:",
                 font=_FONT_SMALL, bg=t["content_bg"], fg=t["text"],
                 anchor="w").pack(fill="x", padx=16, pady=(16, 2))
        tk.Label(dlg, text=folder,
                 font=_FONT_SMALL, bg=t["content_bg"], fg=t["text_secondary"],
                 anchor="w", wraplength=480, justify="left").pack(fill="x", padx=16, pady=(0, 6))

        # ── Footer items packed BEFORE listbox so they always show ──
        btn_row = tk.Frame(dlg, bg=t["content_bg"])
        btn_row.pack(side="bottom", fill="x", padx=16, pady=(0, 16))

        status = f"{len(new_files)} file(s) will be added"
        if dup_count:
            status += f"  ·  {dup_count} already in list (skipped)"
        tk.Label(dlg, text=status, font=_FONT_SMALL,
                 bg=t["content_bg"], fg=t["text_secondary"],
                 anchor="w").pack(side="bottom", fill="x", padx=16, pady=(0, 4))

        # ── File list (fills remaining space) ────────────────
        list_frame = tk.Frame(dlg, bg=t["bg"], highlightthickness=1,
                              highlightbackground=t["border"])
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        lb = tk.Listbox(list_frame, bd=0, relief="flat", font=_FONT_SMALL,
                        bg=t["bg"], fg=t["text"], highlightthickness=0,
                        selectmode=tk.EXTENDED, activestyle="none")
        sb = GlassScrollbar(list_frame, orient="vertical", command=lb.yview)
        _sb_thumb = t["scrollbar_thumb"]
        _sb_hover = t["scrollbar_hover"]
        sb.set_colors(thumb=_sb_thumb, thumb_hover=_sb_hover, parent_bg=t["bg"])
        lb.config(yscrollcommand=sb.set)
        lb.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        sb.grid(row=0, column=1, sticky="ns", pady=4)
        self._bind_scroll(lb)

        for f in found:
            if f in already:
                lb.insert(tk.END, f"  {os.path.basename(f)}  · already added")
            else:
                lb.insert(tk.END, f"  {os.path.basename(f)}")

        # ── Button row (already packed at bottom) ────────────
        def _close_dlg():
            if self._scroll_target is lb:
                self._scroll_target = None
            dlg.destroy()

        def confirm():
            for f in new_files:
                self._selected_files.append(f)
            self._update_file_list()
            _close_dlg()

        dlg.protocol("WM_DELETE_WINDOW", _close_dlg)
        btn_cancel = PillButton(btn_row, text="Cancel", command=_close_dlg,
                                font=_FONT_SMALL, style="secondary", padx=14, pady=6)
        btn_cancel.set_colors(
            fill=t["content_bg"], fg=t["accent"], outline=t["border"],
            hover_fill=t["content_bg"], hover_fg=t["accent"],
            hover_outline=t["accent"], parent_bg=t["content_bg"],
        )
        btn_cancel.pack(side="right", padx=(8, 0))
        btn_add = PillButton(btn_row, text="Add Files", command=confirm,
                             font=_FONT_SMALL, style="primary", padx=14, pady=6)
        btn_add.set_colors(
            fill=t["accent"], fg=t["text_on_accent"],
            hover_fill=t["accent_hover"], hover_fg=t["text_on_accent"],
            parent_bg=t["content_bg"],
        )
        btn_add.pack(side="right")

    def _clear_files(self):
        self._selected_files.clear()
        self._file_aliases.clear()
        self._file_page_ranges.clear()
        self._update_file_list()

    def _pick_output_folder(self):
        initial = self._output_path or None
        folder = filedialog.askdirectory(title="Select output folder",
                                         initialdir=initial)
        if not folder:
            return
        self._output_path = os.path.normpath(folder)
        self._lbl_output_path.config(text=self._output_path)
        # Remember for next session
        self._cfg["last_output_folder"] = self._output_path
        _cfg_mod.save(self._cfg)
        self._check_start_ready()

    def _update_file_list(self):
        self._file_listbox.delete(0, tk.END)
        for path in self._selected_files:
            alias = self._file_aliases.get(path)
            if alias:
                self._file_listbox.insert(tk.END, f"  {alias}  ✎")
            else:
                self._file_listbox.insert(tk.END, f"  {os.path.basename(path)}")

        count = len(self._selected_files)
        if count == 0:
            self._lbl_file_count.config(text="0 files selected")
            # Show empty state, hide listbox
            self._file_listbox.grid_remove()
            self._file_scrollbar.grid_remove()
            self._lbl_empty.grid()
        else:
            label = f"1 file selected" if count == 1 else f"{count} files selected"
            self._lbl_file_count.config(text=label)
            # Show listbox, hide empty state
            self._lbl_empty.grid_remove()
            self._file_listbox.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
            self._file_scrollbar.grid(row=0, column=1, sticky="ns", pady=4)

        self._check_start_ready()

    def _check_start_ready(self):
        ready = bool(self._selected_files) and bool(self._output_path)
        self._btn_start.set_state("normal" if ready else "disabled")

    def _on_open_output_folder(self):
        path = self._last_output_root
        if not path or not os.path.isdir(path):
            messagebox.showinfo(
                "No Output Available",
                "No conversion output is available yet.\n\n"
                "Complete a conversion to open the output folder.",
            )
            return
        import subprocess
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path], close_fds=True,
                             start_new_session=True)
        else:
            subprocess.Popen(["xdg-open", path], close_fds=True,
                             start_new_session=True)

    # ── Keyboard shortcut handlers ────────────────────────

    def _shortcut_escape(self, event):
        """Escape → cancel conversion (only on Conversion screen, root window)."""
        try:
            if str(event.widget.winfo_toplevel()) != str(self.root):
                return
        except Exception:
            return
        if self._current == "Conversion":
            self._on_cancel_conversion()
            return "break"

    def _shortcut_ctrl_enter(self, event):
        """Ctrl+Enter → start conversion (only on Home screen, root window)."""
        try:
            if str(event.widget.winfo_toplevel()) != str(self.root):
                return
        except Exception:
            return
        if self._current == "Home" and self._btn_start._state == "normal":
            self._on_start()
            return "break"

    def _on_cancel_conversion(self):
        if self._active_job and self._active_job.is_running():
            self._active_job.cancel()
            self._log_write("Cancellation requested — stopping…")
        else:
            messagebox.showinfo(
                "No Active Conversion",
                "No conversion is currently running.",
            )

    def _log_write(self, text: str):
        self._conv_log.config(state="normal")
        self._conv_log.insert(tk.END, text + "\n")
        # Cap log size to prevent unbounded memory growth
        line_count = int(self._conv_log.index("end-1c").split(".")[0])
        if line_count > self._MAX_LOG_LINES:
            self._conv_log.delete("1.0", f"{line_count - self._MAX_LOG_LINES}.0")
        self._conv_log.config(state="disabled")
        self._conv_log.see(tk.END)

    def _reset_conversion_screen(self):
        n = len(self._selected_files)
        self._conv_overall_bar.set_indeterminate(False)
        self._conv_file_bar.set_indeterminate(False)
        self._conv_overall_bar.set_progress(0.0)
        self._conv_file_bar.set_progress(0.0)
        label = "1 file" if n == 1 else f"{n} files"
        self._conv_overall_count_lbl.config(text=f"0 of {label}")
        self._conv_file_name_lbl.config(text="Preparing…")
        self._conv_stage_lbl.config(text="")
        self._conv_elapsed_lbl.config(text="")
        self._conv_log.config(state="normal")
        self._conv_log.delete("1.0", tk.END)
        self._conv_log.config(state="disabled")
        self._log_write(f"Queued {label} for conversion:\n")
        for i, path in enumerate(self._selected_files, 1):
            alias = self._file_aliases.get(path)
            name = alias if alias else os.path.basename(path)
            self._log_write(f"  {i}.  {name}")
        self._log_write("")

    def _on_start(self):
        if self._active_job and self._active_job.is_running():
            return
        if not self._output_path or not os.path.isdir(self._output_path):
            messagebox.showwarning(
                "Output Folder",
                "The output folder does not exist or was not set.\n\n"
                "Please select a valid output folder before starting.",
            )
            return
        # ── License / free-tier gate ──────────────────────────
        if _license_mod.is_trial_expired():
            self._show_license_prompt()
            return
        remaining = _license_mod.get_remaining_conversions()
        file_count = len(self._selected_files)
        if remaining != -1 and file_count > remaining:
            messagebox.showinfo(
                "Free Tier Limit",
                f"You have {remaining} free conversion{'s' if remaining != 1 else ''} "
                f"remaining, but {file_count} file{'s' if file_count != 1 else ''} "
                f"queued.\n\nPlease reduce the file count or enter a license key "
                f"to unlock unlimited conversions.",
            )
            return
        self._btn_start.set_state("disabled")
        self._reset_conversion_screen()
        self._show("Conversion")
        self._last_output_root = self._output_path

        self._active_job = _converter_mod.ConversionJob(
            files=list(self._selected_files),
            aliases=dict(self._file_aliases),
            output_root=self._output_path,
            cfg=dict(self._cfg),
            root=self.root,
            on_log=self._log_write,
            on_file_progress=self._set_file_progress,
            on_overall_progress=self._set_overall_progress,
            on_file_start=self._on_file_start,
            on_stage=self._on_stage_update,
            on_done=self._on_conversion_done,
            page_ranges=dict(self._file_page_ranges),
        )
        self._start_elapsed_timer()
        self._active_job.start()

    def _set_file_progress(self, fraction: float) -> None:
        if fraction < 0:
            self._conv_file_bar.set_indeterminate(True)
        else:
            self._conv_file_bar.set_progress(fraction)

    def _set_overall_progress(self, fraction: float) -> None:
        if fraction < 0:
            self._conv_overall_bar.set_indeterminate(True)
        else:
            self._conv_overall_bar.set_progress(fraction)

    def _on_file_start(self, filename: str, idx: int, total: int) -> None:
        self._conv_file_name_lbl.config(text=filename)
        self._conv_overall_count_lbl.config(text=f"{idx} of {total} file{'s' if total != 1 else ''}")

    def _on_stage_update(self, stage: str) -> None:
        self._conv_stage_lbl.config(text=stage)

    def _on_conversion_done(self, result: "_converter_mod.BatchResult") -> None:
        self._stop_elapsed_timer()
        # Final bar states — only show 100% when not cancelled
        if result.cancelled:
            frac = result.completed / max(result.total, 1)
            self._conv_overall_bar.set_progress(frac)
        else:
            self._conv_overall_bar.set_progress(1.0)
            self._conv_file_bar.set_progress(1.0)
        total = result.total
        self._conv_overall_count_lbl.config(text=f"{result.completed} of {total} file{'s' if total != 1 else ''}")
        self._conv_file_name_lbl.config(text="Conversion complete" if not result.cancelled else "Cancelled")
        self._conv_stage_lbl.config(text="")
        # Re-enable start button
        self._check_start_ready()
        self._log_write("")
        self._log_write(result.status_text)

        # Update license status after conversions
        self._update_license_status()

        # Populate Results screen
        try:
            self._populate_results(result)
        except Exception as e:
            self._log_write(f"Error populating results: {e}")

        if self._current == "Conversion":
            self._show("Results")
        else:
            self._results_notify()

    def _populate_results(self, result: "_converter_mod.BatchResult") -> None:
        self._last_batch_result = result
        t = self._t
        bc = result.batch_confidence

        # Status banner
        self._results_status_lbl.config(text=result.status_text)
        if result.failed > 0:
            self._results_status_frame.config(highlightbackground="#ef4444")
        else:
            self._results_status_frame.config(highlightbackground=t["border"])

        # Output path
        self._results_out_path_lbl.config(text=f"Output location: {result.output_root}")
        self._last_output_root = result.output_root

        # Confidence labels — order matches _CONF_AREAS
        scores = [
            bc.overall,
            bc.text_extraction,
            bc.table_structure,
            bc.image_extraction,
            bc.image_placement,
            bc.document_order,
        ]
        for lbl, score in zip(self._results_conf_level_lbls, scores):
            lbl.config(text=score)

        # Validation panel
        val_results = _validation_mod.validate_batch(result.output_root)
        if val_results:
            vr = _validation_mod.aggregate_validation(val_results)
            self._results_val_count_lbls["heading_count"].config(text=str(vr.heading_count))
            self._results_val_count_lbls["table_count"].config(text=str(vr.table_count))
            self._results_val_count_lbls["image_count"].config(text=str(vr.image_count))
            self._results_val_count_lbls["page_count"].config(text=str(vr.page_count))
            self._results_val_count_lbls["word_count"].config(text=f"{vr.word_count:,}")
            if vr.readability_label:
                self._results_val_count_lbls["readability"].config(
                    text=f"Grade {vr.readability_grade} — {vr.readability_label}")
            else:
                self._results_val_count_lbls["readability"].config(text="—")

            issues = []
            for issue in vr.heading_issues:
                issues.append(f"⚠ Heading: {issue}")
            for issue in vr.broken_links:
                issues.append(f"⚠ Link: {issue}")
            for issue in vr.missing_alt_texts:
                issues.append(f"⚠ Alt text: {issue}")

            self._results_val_issues_text.config(state="normal")
            self._results_val_issues_text.delete("1.0", tk.END)
            if issues:
                self._results_val_issues_text.insert("1.0", "\n".join(issues))
                self._results_val_issues_text.config(
                    fg=t.get("accent_secondary", t["text_secondary"]))
            else:
                self._results_val_issues_text.insert("1.0", "✓ All checks passed")
                self._results_val_issues_text.config(
                    fg=t.get("accent", t["text"]))
            self._results_val_issues_text.config(state="disabled")
        else:
            for key in self._results_val_count_lbls:
                self._results_val_count_lbls[key].config(text="—")
            self._results_val_issues_text.config(state="normal")
            self._results_val_issues_text.delete("1.0", tk.END)
            self._results_val_issues_text.insert("1.0", "No output files to validate.")
            self._results_val_issues_text.config(fg=t["text_secondary"], state="disabled")

        # Warnings panel
        all_warnings = []
        for cr in result.all_confidence:
            for w in cr.warnings:
                all_warnings.append(f"• {w}")
        self._results_warn_text.config(state="normal")
        self._results_warn_text.delete("1.0", tk.END)
        if all_warnings:
            self._results_warn_text.insert(tk.END, "\n".join(all_warnings))
        else:
            self._results_warn_text.insert(tk.END, "No warnings.")
        self._results_warn_text.config(state="disabled")

        # Per-file list with content badges
        self._populate_file_list(result)

    # ── Per-file badge list ──────────────────────────────────

    _BADGE_COLORS = {
        "High":   "#22c55e",
        "Medium": "#eab308",
        "Low":    "#ef4444",
        "Failed": "#ef4444",
    }

    def _populate_file_list(self, result: "_converter_mod.BatchResult") -> None:
        """Fill the FILES section on the Results screen with per-file badges."""
        inner = self._results_files_inner
        if inner is None:
            return

        # Clear previous content
        for w in inner.winfo_children():
            w.destroy()

        t = self._t
        confs = result.all_confidence
        if not confs:
            lbl = tk.Label(
                inner, text="No file details available.",
                font=_FONT_SMALL, anchor="w", padx=10, pady=8,
                bg=t["bg"], fg=t["text_secondary"],
            )
            lbl.pack(anchor="w")
            return

        _badge_font = (_FONT_FAMILY, 8, "bold")

        # Map dimension fields to badge labels
        _dims = [
            ("text_extraction", "Text"),
            ("table_structure", "Tables"),
            ("image_extraction", "Images"),
            ("ocr_confidence", "OCR"),
        ]

        for conf in confs:
            row_frame = tk.Frame(inner, bg=t["bg"])
            row_frame.pack(fill="x", padx=8, pady=2)

            fname = os.path.basename(conf.source_file) if conf.source_file else "Unknown"
            name_lbl = tk.Label(
                row_frame, text=fname, font=_FONT_SMALL,
                anchor="w", bg=t["bg"], fg=t["text"],
            )
            name_lbl.pack(side="left", padx=(4, 8))

            for attr, badge_text in _dims:
                level = getattr(conf, attr, "N/A") or "N/A"
                if level == "N/A":
                    continue
                color = self._BADGE_COLORS.get(level, t["text_secondary"])
                badge = tk.Label(
                    row_frame, text=f" {badge_text} ",
                    font=_badge_font, fg=color, bg=t["bg"],
                    highlightthickness=1, highlightbackground=color,
                    padx=3, pady=0,
                )
                badge.pack(side="left", padx=(0, 4))

            # Overall confidence on the right
            overall = conf.overall or "N/A"
            overall_color = self._BADGE_COLORS.get(overall, t["text_secondary"])
            overall_lbl = tk.Label(
                row_frame, text=overall, font=(_FONT_FAMILY, 9),
                anchor="e", bg=t["bg"], fg=overall_color,
            )
            overall_lbl.pack(side="right", padx=(8, 4))

    def _on_listbox_select(self, _event=None):
        sel = self._file_listbox.curselection()
        self._btn_rename.set_state("normal" if len(sel) == 1 else "disabled")

    def _rename_selected_file(self):
        sel = self._file_listbox.curselection()
        if len(sel) != 1:
            return
        path = self._selected_files[sel[0]]
        current = self._file_aliases.get(path, os.path.splitext(os.path.basename(path))[0])
        new_name = simpledialog.askstring(
            "Rename Output File",
            "Enter a name for the output Markdown file\n(no extension needed):",
            initialvalue=current,
            parent=self.root,
        )
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        original = os.path.splitext(os.path.basename(path))[0]
        if new_name == original:
            self._file_aliases.pop(path, None)
        else:
            self._file_aliases[path] = new_name
        self._update_file_list()

    def _on_listbox_right_click(self, event):
        idx = self._file_listbox.nearest(event.y)
        if idx < 0 or idx >= len(self._selected_files):
            return
        if idx not in self._file_listbox.curselection():
            self._file_listbox.selection_clear(0, tk.END)
            self._file_listbox.selection_set(idx)
        sel = self._file_listbox.curselection()
        t = self._t
        menu = tk.Menu(self.root, tearoff=0,
                       bg=t["content_bg"], fg=t["text"],
                       activebackground=t["accent"],
                       activeforeground=t["text_on_accent"],
                       relief="flat", bd=0)
        if len(sel) == 1:
            menu.add_command(label="Rename Output File…", command=self._rename_selected_file)
            # Show "Select Pages…" for PDF files
            sel_path = self._selected_files[sel[0]]
            if sel_path.lower().endswith(".pdf"):
                pages_label = "Select Pages…"
                if sel_path in self._file_page_ranges:
                    n = len(self._file_page_ranges[sel_path])
                    pages_label = f"Select Pages… ({n} selected)"
                menu.add_command(label=pages_label,
                                 command=lambda: self._show_page_selector(sel_path))
            menu.add_separator()
        remove_label = "Remove File" if len(sel) == 1 else f"Remove {len(sel)} Files"
        menu.add_command(label=remove_label, command=self._remove_selected_files)
        menu.tk_popup(event.x_root, event.y_root)

    def _remove_selected_files(self):
        indices = sorted(self._file_listbox.curselection(), reverse=True)
        for idx in indices:
            path = self._selected_files.pop(idx)
            self._file_aliases.pop(path, None)
            self._file_page_ranges.pop(path, None)
        self._update_file_list()

    def _show_page_selector(self, pdf_path: str):
        """Show a visual page selector with thumbnails for a PDF file."""
        t = self._t
        try:
            import fitz
            doc = fitz.open(pdf_path)
        except Exception:
            messagebox.showerror("Error", "Could not open PDF for page preview.")
            return

        total = doc.page_count
        existing = set(self._file_page_ranges.get(pdf_path, []))

        win = tk.Toplevel(self.root)
        win.title(f"Select Pages — {os.path.basename(pdf_path)}")
        win_w = int(680 * self._dpi)
        win_h = int(520 * self._dpi)
        rx = self.root.winfo_x() + (self.root.winfo_width() - win_w) // 2
        ry = self.root.winfo_y() + (self.root.winfo_height() - win_h) // 2
        win.geometry(f"{win_w}x{win_h}+{max(0, rx)}+{max(0, ry)}")
        win.config(bg=t["bg"])
        win.transient(self.root)
        win.grab_set()
        self._set_titlebar_dark(self._dark, win)

        # Header
        tk.Label(
            win, text=f"{os.path.basename(pdf_path)}  •  {total} pages",
            font=(_FONT_FAMILY, 12, "bold"),
            fg=t["text"], bg=t["bg"],
        ).pack(padx=16, pady=(16, 4), anchor="w")
        tk.Label(
            win, text="Click pages to select or deselect. Shift+click for range.",
            font=(_FONT_FAMILY, 9),
            fg=t["text_secondary"], bg=t["bg"],
        ).pack(padx=16, pady=(0, 8), anchor="w")

        # Quick actions bar
        actions_bar = tk.Frame(win, bg=t["bg"])
        actions_bar.pack(fill="x", padx=16, pady=(0, 8))

        page_selected = {}  # page_num (1-indexed) → BooleanVar
        page_frames = {}    # page_num → frame widget (for highlight)
        thumb_images = []   # prevent GC

        count_lbl = tk.Label(
            actions_bar, text="", font=_FONT_SMALL,
            fg=t["text_secondary"], bg=t["bg"],
        )
        count_lbl.pack(side="right")

        def _update_count():
            sel = [p for p, v in page_selected.items() if v.get()]
            if len(sel) == total or len(sel) == 0:
                count_lbl.config(text=f"All {total} pages")
            else:
                count_lbl.config(text=f"{len(sel)} of {total} pages selected")

        def _select_all():
            for v in page_selected.values():
                v.set(True)
            _refresh_highlights()

        def _select_none():
            for v in page_selected.values():
                v.set(False)
            _refresh_highlights()

        btn_all = PillButton(actions_bar, text="Select All", font=_FONT_SMALL,
                             style="secondary", padx=10, pady=4, command=_select_all)
        btn_all.pack(side="left", padx=(0, 4))
        btn_all.set_colors(fill=t["bg"], fg=t["text"],
                           hover_fill=t["accent"], parent_bg=t["bg"])
        Tooltip(btn_all, "Select all pages for conversion.", lambda: self._t)

        btn_none = PillButton(actions_bar, text="Clear", font=_FONT_SMALL,
                              style="secondary", padx=10, pady=4, command=_select_none)
        btn_none.pack(side="left", padx=(0, 4))
        btn_none.set_colors(fill=t["bg"], fg=t["text"],
                            hover_fill=t["accent"], parent_bg=t["bg"])
        Tooltip(btn_none, "Deselect all pages.", lambda: self._t)

        # Scrollable grid of page thumbnails
        grid_outer = tk.Frame(win, bg=t["bg"])
        grid_outer.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        canvas = tk.Canvas(grid_outer, bg=t["bg"], highlightthickness=0)
        sb = GlassScrollbar(grid_outer, orient="vertical", command=canvas.yview)
        sb.set_colors(thumb=t["scrollbar_thumb"], thumb_hover=t["scrollbar_hover"],
                      parent_bg=t["bg"])
        grid_frame = tk.Frame(canvas, bg=t["bg"])
        canvas.create_window((0, 0), window=grid_frame, anchor="nw")
        grid_frame.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Mousewheel scroll
        canvas.bind("<Enter>", lambda _: setattr(self, '_scroll_target', canvas))
        canvas.bind("<Leave>", lambda _: setattr(self, '_scroll_target', None)
                    if self._scroll_target is canvas else None)
        grid_frame.bind("<Enter>", lambda _: setattr(self, '_scroll_target', canvas))

        last_clicked = [None]  # for Shift+click range selection

        def _on_page_click(page_num, event=None):
            shift = event and (event.state & 0x1)  # Shift held
            if shift and last_clicked[0] is not None:
                # Range selection
                lo = min(last_clicked[0], page_num)
                hi = max(last_clicked[0], page_num)
                for p in range(lo, hi + 1):
                    page_selected[p].set(True)
            else:
                page_selected[page_num].set(not page_selected[page_num].get())
            last_clicked[0] = page_num
            _refresh_highlights()

        def _refresh_highlights():
            for pn, frm in page_frames.items():
                if page_selected[pn].get():
                    frm.config(highlightbackground=t["accent"], highlightthickness=2)
                else:
                    frm.config(highlightbackground=t["border"], highlightthickness=1)
            _update_count()

        # Render thumbnails in a grid (4 columns)
        cols = 4
        thumb_w = int(120 * self._dpi)
        zoom = thumb_w / 612.0  # 612pt = US Letter width
        mat = fitz.Matrix(zoom, zoom)

        for i in range(total):
            page_num = i + 1
            row, col = divmod(i, cols)
            var = tk.BooleanVar(value=(page_num in existing) if existing else True)
            page_selected[page_num] = var

            cell = tk.Frame(grid_frame, bg=t["bg"],
                            highlightthickness=1, highlightbackground=t["border"])
            cell.grid(row=row, column=col, padx=4, pady=4)
            page_frames[page_num] = cell

            try:
                page = doc[i]
                pix = page.get_pixmap(matrix=mat)
                from PIL import Image as _PILImage, ImageTk as _PILImageTk
                img = _PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
                photo = _PILImageTk.PhotoImage(img)
                thumb_images.append(photo)
                lbl = tk.Label(cell, image=photo, bg=t["bg"], cursor="hand2")
            except Exception:
                lbl = tk.Label(cell, text=f"Page {page_num}", font=_FONT_SMALL,
                               fg=t["text_secondary"], bg=t["bg"],
                               width=14, height=8, cursor="hand2")
            lbl.pack(padx=2, pady=2)
            _pn = page_num
            lbl.bind("<Button-1>", lambda e, p=_pn: _on_page_click(p, e))

            tk.Label(cell, text=str(page_num), font=(_FONT_FAMILY, 8),
                     fg=t["text_secondary"], bg=t["bg"]).pack()

        doc.close()
        _refresh_highlights()

        # Bottom buttons
        btn_bar = tk.Frame(win, bg=t["bg"])
        btn_bar.pack(fill="x", padx=16, pady=(0, 16))

        def _close_page_dlg():
            if self._scroll_target is canvas:
                self._scroll_target = None
            win.destroy()

        def _apply():
            selected = sorted(p for p, v in page_selected.items() if v.get())
            if len(selected) == total or not selected:
                self._file_page_ranges.pop(pdf_path, None)
            else:
                self._file_page_ranges[pdf_path] = selected
            self._update_file_list()
            _close_page_dlg()

        win.protocol("WM_DELETE_WINDOW", _close_page_dlg)
        btn_apply = PillButton(btn_bar, text="Apply", font=(_FONT_FAMILY, 10, "bold"),
                               style="primary", padx=24, pady=8, command=_apply)
        btn_apply.pack(side="right", padx=(4, 0))
        btn_apply.set_colors(fill=t["accent"], fg=t["text_on_accent"],
                             hover_fill=t["accent_hover"], parent_bg=t["bg"])

        btn_cancel = PillButton(btn_bar, text="Cancel", font=_FONT_SMALL,
                                style="secondary", padx=16, pady=6,
                                command=_close_page_dlg)
        btn_cancel.pack(side="right", padx=(0, 4))
        btn_cancel.set_colors(fill=t["bg"], fg=t["text"],
                              hover_fill=t["accent"], parent_bg=t["bg"])

    # ── Drag and drop handlers ──────────────────────────────

    def _on_drop_enter(self, event=None):
        t = self._t
        self._file_list_frame.config(highlightbackground=t["accent"], highlightthickness=2)

    def _on_drop_leave(self, event=None):
        t = self._t
        self._file_list_frame.config(highlightbackground=t["border"], highlightthickness=1)

    def _on_drop(self, event):
        self._on_drop_leave()
        raw = event.data
        # tkdnd delivers paths as a Tcl list; braces wrap paths with spaces
        paths = self._parse_drop_paths(raw)
        added = 0
        skipped_exts = set()
        for p in paths:
            p = os.path.normpath(p)
            if os.path.isdir(p):
                for dirpath, _dirs, filenames in os.walk(p):
                    for entry in sorted(filenames):
                        full = os.path.join(dirpath, entry)
                        if os.path.splitext(entry)[1].lower() in _SUPPORTED_EXTS:
                            if full not in self._selected_files:
                                self._selected_files.append(full)
                                added += 1
            elif os.path.isfile(p):
                ext = os.path.splitext(p)[1].lower()
                if ext in _SUPPORTED_EXTS:
                    if p not in self._selected_files:
                        self._selected_files.append(p)
                        added += 1
                else:
                    skipped_exts.add(ext)
        if added:
            self._update_file_list()
        if skipped_exts:
            messagebox.showinfo(
                "Unsupported Files Skipped",
                f"Skipped files with unsupported extensions:\n{', '.join(sorted(skipped_exts))}\n\n"
                f"Added {added} supported file(s).",
            )

    @staticmethod
    def _parse_drop_paths(data: str) -> list[str]:
        """Parse Tcl list of dropped file paths (handles braces and spaces)."""
        paths = []
        i = 0
        while i < len(data):
            if data[i] == '{':
                try:
                    end = data.index('}', i)
                except ValueError:
                    end = len(data)
                paths.append(data[i + 1:end])
                i = end + 2
            elif data[i] == ' ':
                i += 1
            else:
                end = data.find(' ', i)
                if end == -1:
                    end = len(data)
                paths.append(data[i:end])
                i = end + 1
        return paths

    # ── Navigation ──────────────────────────────────────────

    def _show(self, name: str):
        for frame in self._frames.values():
            frame.grid_remove()
        self._frames[name].grid()
        self._current = name
        self._refresh_nav()

    def _refresh_nav(self):
        t = self._t
        for name, btn in self._nav_btns.items():
            active = name == self._current
            btn.config(
                bg=t["nav_active_bg"] if active else t["sidebar_bg"],
                fg=t["accent"]        if active else t["text"],
                font=_FONT_NAV_ACT    if active else _FONT_NAV,
                activebackground=t["nav_active_bg"] if active else t["nav_hover_bg"],
                activeforeground=t["accent"]        if active else t["text"],
            )

    # ── License management ───────────────────────────────────

    def _update_license_status(self):
        """Update the sidebar About / license button."""
        info = _license_mod.get_license_info()
        t = self._t
        self._about_btn_frame.config(bg=t["sidebar_bg"])
        if info["licensed"]:
            self._license_status_lbl.config(
                text="ℹ  About  •  ✓ Licensed",
                fg="#22c55e", bg=t["sidebar_bg"])
        elif info["status"] == "Trial expired":
            self._license_status_lbl.config(
                text="ℹ  About  •  Trial expired",
                fg="#ef4444", bg=t["sidebar_bg"])
        else:
            remaining = info["remaining"]
            self._license_status_lbl.config(
                text=f"ℹ  About  •  {remaining} free left",
                fg=t["text_secondary"], bg=t["sidebar_bg"])

    def _show_license_prompt(self):
        """Show the license activation dialog when trial is expired."""
        t = self._t
        win = tk.Toplevel(self.root)
        win.title("License Required")
        win.geometry(f"{int(480 * self._dpi)}x{int(340 * self._dpi)}")
        win.config(bg=t["bg"])
        win.transient(self.root)
        win.grab_set()

        info = _license_mod.get_license_info()

        # Header
        tk.Label(
            win, text="Free Trial Expired",
            font=(_FONT_FAMILY, 16, "bold"), fg=t["accent"], bg=t["bg"],
        ).pack(pady=(24, 8))

        tk.Label(
            win,
            text=f"You've used {info['conversion_count']} of {info['limit']} "
                 f"free conversions.\n\n"
                 f"Enter a license key to unlock unlimited conversions,\n"
                 f"or visit darksquare.dev to purchase a license.",
            font=(_FONT_FAMILY, 11), fg=t["text"], bg=t["bg"],
            justify="center",
        ).pack(pady=(0, 16))

        # Key entry
        key_frame = tk.Frame(win, bg=t["bg"])
        key_frame.pack(fill="x", padx=32, pady=(0, 8))
        tk.Label(
            key_frame, text="License Key:", font=_FONT_SMALL,
            fg=t["text_secondary"], bg=t["bg"],
        ).pack(anchor="w")
        key_var = tk.StringVar()
        key_entry = tk.Entry(
            key_frame, textvariable=key_var,
            font=(_FONT_MONO, 11), bg=t["content_bg"], fg=t["text"],
            insertbackground=t["text"], relief="flat", bd=0,
        )
        key_entry.pack(fill="x", ipady=6, pady=(4, 0))

        status_lbl = tk.Label(
            win, text="", font=_FONT_SMALL,
            fg=t["text_secondary"], bg=t["bg"],
        )
        status_lbl.pack()

        def activate():
            key = key_var.get().strip()
            if not key:
                status_lbl.config(text="Please enter a license key.", fg="#ef4444")
                return
            success, msg = _license_mod.activate_license(key)
            if success:
                status_lbl.config(text=msg, fg="#22c55e")
                def _safe_close():
                    try:
                        win.destroy()
                    except Exception:
                        pass
                win.after(1500, _safe_close)
            else:
                status_lbl.config(text=msg, fg="#ef4444")

        btn_frame = tk.Frame(win, bg=t["bg"])
        btn_frame.pack(fill="x", padx=32, pady=(12, 16))

        btn_activate = PillButton(
            btn_frame, text="Activate License", font=_FONT_BTN,
            style="primary", padx=20, pady=8, command=activate,
        )
        btn_activate.pack(side="right")
        btn_activate.set_colors(
            fill=t["accent"], fg=t["text_on_accent"],
            hover_fill=t["accent_hover"], hover_fg=t["text_on_accent"],
            parent_bg=t["bg"],
        )

        btn_close = PillButton(
            btn_frame, text="Close", font=_FONT_SMALL,
            style="secondary", padx=14, pady=6, command=win.destroy,
        )
        btn_close.pack(side="left")
        btn_close.set_colors(
            fill=t["bg"], fg=t["text_secondary"], outline=t["border"],
            hover_fill=t["bg"], hover_fg=t["accent"], hover_outline=t["accent"],
            parent_bg=t["bg"],
        )

    # ── About / Help ─────────────────────────────────────────

    def _show_about_window(self):
        """Show the About / Help window with app info and quick-start guide."""
        t = self._t
        win = tk.Toplevel(self.root)
        win.title("About — Doc to Markdown")
        win.geometry(f"{int(560 * self._dpi)}x{int(560 * self._dpi)}")
        win.config(bg=t["bg"])
        win.transient(self.root)
        self._set_titlebar_dark(self._dark, win)

        info = _license_mod.get_license_info()

        # Scrollable content
        canvas = tk.Canvas(win, bg=t["bg"], highlightthickness=0)
        sb = GlassScrollbar(win, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=t["bg"])
        canvas.create_window((0, 0), window=frame, anchor="nw")
        frame.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.configure(yscrollcommand=sb.set)

        _sb_thumb = t["scrollbar_thumb"]
        _sb_hover = t["scrollbar_hover"]
        sb.set_colors(thumb=_sb_thumb, thumb_hover=_sb_hover, parent_bg=t["bg"])

        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Enable mousewheel scrolling
        canvas.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', canvas))
        canvas.bind(
            "<Leave>", lambda _e: setattr(self, '_scroll_target', None)
            if self._scroll_target is canvas else None)
        frame.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', canvas))

        pad = 28

        # ── Title ──
        tk.Label(
            frame, text="Doc to Markdown", font=(_FONT_FAMILY, 20, "bold"),
            fg=t["accent"], bg=t["bg"],
        ).pack(anchor="w", padx=pad, pady=(24, 0))
        tk.Label(
            frame, text="by Darksquare", font=(_FONT_FAMILY, 12),
            fg=t["text_secondary"], bg=t["bg"],
        ).pack(anchor="w", padx=pad)
        tk.Label(
            frame, text="Version 1.2.0", font=(_FONT_FAMILY, 11),
            fg=t["text_secondary"], bg=t["bg"],
        ).pack(anchor="w", padx=pad, pady=(2, 12))

        # ── License status panel ──
        lic_frame = tk.Frame(frame, bg=t["content_bg"], padx=16, pady=12,
                             highlightbackground=t["border"], highlightthickness=1)
        lic_frame.pack(fill="x", padx=pad, pady=(0, 4))
        status_color = "#22c55e" if info["licensed"] else (
            "#ef4444" if info["status"] == "Trial expired" else t["accent"])
        tk.Label(
            lic_frame, text=f"License: {info['status']}",
            font=(_FONT_FAMILY, 11, "bold"), fg=status_color, bg=t["content_bg"],
        ).pack(anchor="w")
        if not info["licensed"]:
            remaining = info["remaining"]
            tk.Label(
                lic_frame,
                text=f"Conversions used: {info['conversion_count']} / {info['limit']}  "
                     f"({remaining} remaining)",
                font=_FONT_SMALL, fg=t["text_secondary"], bg=t["content_bg"],
            ).pack(anchor="w", pady=(4, 0))
        else:
            tk.Label(
                lic_frame, text="Unlimited conversions",
                font=_FONT_SMALL, fg=t["text_secondary"], bg=t["content_bg"],
            ).pack(anchor="w", pady=(4, 0))

        # ── License key entry ──
        key_frame = tk.Frame(frame, bg=t["bg"])
        key_frame.pack(fill="x", padx=pad, pady=(4, 16))

        tk.Label(
            key_frame, text="License Key:", font=(_FONT_FAMILY, 10),
            fg=t["text_secondary"], bg=t["bg"],
        ).pack(anchor="w", pady=(0, 4))

        key_row = tk.Frame(key_frame, bg=t["bg"])
        key_row.pack(fill="x")

        key_entry = tk.Entry(
            key_row, font=(_FONT_MONO, 11),
            bg=t["content_bg"], fg=t["text"],
            insertbackground=t["text"],
            relief="flat", highlightthickness=1,
            highlightbackground=t["border"],
            highlightcolor=t["accent"],
        )
        key_entry.pack(side="left", fill="x", expand=True, ipady=5)

        if info["licensed"]:
            # Show the current key (masked) and a deactivate button
            masked = info["license_key"][:7] + "••••-••••-" + info["license_key"][-4:]
            key_entry.insert(0, masked)
            key_entry.config(state="disabled", disabledbackground=t["content_bg"],
                             disabledforeground=t["text_secondary"])

            def _deactivate():
                _license_mod.deactivate_license()
                self._update_license_status()
                win.destroy()
                self._show_about_window()

            deact_btn = PillButton(
                key_row, text="Deactivate", font=_FONT_SMALL,
                style="secondary", padx=12, pady=5, command=_deactivate,
            )
            deact_btn.pack(side="left", padx=(8, 0))
            deact_btn.set_colors(
                fill=t["bg"], fg="#ef4444", outline="#ef4444",
                hover_fill="#ef4444", hover_fg="#ffffff", hover_outline="#ef4444",
                parent_bg=t["bg"],
            )
        else:
            key_entry.insert(0, "")

            key_msg = tk.Label(
                key_frame, text="", font=(_FONT_FAMILY, 9),
                bg=t["bg"], anchor="w",
            )
            key_msg.pack(anchor="w", pady=(4, 0))

            def _activate():
                key = key_entry.get().strip()
                if not key:
                    key_msg.config(text="Please enter a license key.", fg="#ef4444")
                    return
                ok, msg = _license_mod.activate_license(key)
                if ok:
                    self._update_license_status()
                    win.destroy()
                    self._show_about_window()
                else:
                    key_msg.config(text=msg, fg="#ef4444")

            act_btn = PillButton(
                key_row, text="Activate", font=_FONT_SMALL,
                style="primary", padx=14, pady=5, command=_activate,
            )
            act_btn.pack(side="left", padx=(8, 0))
            act_btn.set_colors(
                fill=t["accent"], fg=t["text_on_accent"], outline=t["accent"],
                hover_fill=t["accent_hover"], hover_fg=t["text_on_accent"],
                hover_outline=t["accent_hover"], parent_bg=t["bg"],
            )

        # ── Quick Start ──
        def _section(title, body):
            tk.Label(
                frame, text=title, font=(_FONT_FAMILY, 13, "bold"),
                fg=t["text"], bg=t["bg"],
            ).pack(anchor="w", padx=pad, pady=(12, 4))
            tk.Label(
                frame, text=body, font=(_FONT_FAMILY, 11),
                fg=t["text_secondary"], bg=t["bg"],
                wraplength=int(480 * self._dpi), justify="left",
            ).pack(anchor="w", padx=pad)

        _section("Getting Started", (
            "1. Click 'Add Files' or drag files onto the Home screen\n"
            "2. Choose an output folder\n"
            "3. Adjust settings if needed (defaults work well)\n"
            "4. Click 'Convert' and wait for results\n"
            "5. Review output in the Preview window"
        ))

        _section("Supported Formats", (
            "PDF, DOCX, DOC, XLSX, XLS, CSV, PPTX, EPUB, HTML, HTM, "
            "RTF, DXF, PNG, JPG, JPEG, BMP, TIFF, TIF, WEBP, GIF"
        ))

        _section("Output Formats", (
            "Markdown (.md), JSON (.json), HTML (.html), "
            "Plain Text (.txt), RAG Chunks (.jsonl), "
            "Searchable PDF (.pdf)"
        ))

        _section("Key Features", (
            "• Multi-engine conversion with automatic fallback chains\n"
            "• OCR for scanned documents (RapidOCR + Tesseract)\n"
            "• GPU acceleration (CUDA, DirectML, CoreML)\n"
            "• Offline translation for non-English documents\n"
            "• Confidence scoring across 6 quality dimensions\n"
            "• Post-processing rules with named profiles\n"
            "• Watch Folder mode for automated batch conversion\n"
            "• Dark and light themes"
        ))

        _section("Local Processing", (
            "All files are processed locally on your machine. No documents "
            "are uploaded to any cloud service, external API, or remote server. "
            "Your data never leaves your computer."
        ))

        _section("Support", (
            "Website: darksquare.dev\n"
            "Email: support@darksquare.dev"
        ))

        # Bottom padding
        tk.Frame(frame, bg=t["bg"], height=24).pack()

        # Clean up scroll target reference when window closes
        def _on_about_close():
            if self._scroll_target is canvas:
                self._scroll_target = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_about_close)

    # ── Theme ────────────────────────────────────────────────

    def _toggle_theme(self):
        self._dark = self._theme_dark_var.get()
        self._t = themes.DARK if self._dark else themes.LIGHT
        self._cfg["theme"] = "dark" if self._dark else "light"
        _cfg_mod.save(self._cfg)
        self._apply_theme()

    def _draw_sun_icon(self):
        c = self._sun_canvas
        c.delete("all")
        s = int(c.cget("width"))
        cx, cy = s / 2, s / 2
        active = not self._dark
        color = "#f59e0b" if active else self._t["text_secondary"]

        inner_r = s * 0.18
        outer_r = s * 0.42
        pts = []
        for i in range(16):
            a = i * math.pi / 8 - math.pi / 2
            r = outer_r if i % 2 == 0 else inner_r
            pts.extend([cx + r * math.cos(a), cy + r * math.sin(a)])
        c.create_polygon(pts, fill=color, outline=color,
                         width=1, smooth=True, splinesteps=16)

    def _draw_moon_icon(self):
        c = self._moon_canvas
        c.delete("all")
        s = int(c.cget("width"))
        cx, cy = s / 2, s / 2
        bg = self._t["sidebar_bg"]
        active = self._dark
        color = "#cbd5e1" if active else self._t["text_secondary"]

        r = s * 0.32
        _draw_circle(c, cx, cy, r, fill=color, steps=64)
        _draw_circle(c, cx - r * 0.35, cy + r * 0.05, r * 1.0, fill=bg, steps=64)

    def _set_titlebar_dark(self, dark: bool, window=None) -> None:
        """
        Apply dark/light title bar on Windows via the DWM API.

        Works on the root window or any Toplevel passed via *window*.
        For Toplevel dialogs the call is deferred so the window is fully
        mapped before we query its HWND.
        """
        target = window or self.root
        if window is not None:
            target.after(50, lambda: self._apply_dwm_dark(dark, target))
        else:
            self._apply_dwm_dark(dark, target)

    def _apply_dwm_dark(self, dark: bool, target) -> None:
        if not self._is_windows:
            return
        try:
            if not target.winfo_exists():
                return
        except Exception:
            return
        try:
            import ctypes
            from ctypes import c_int, byref, sizeof

            target.update_idletasks()

            # wm_frame() returns the hex string of the real top-level
            # frame HWND that DWM controls.  For Toplevel dialogs
            # GetParent() can return the owner instead of the frame,
            # so wm_frame() is the reliable path.
            frame_hex = target.wm_frame()
            hwnd = int(frame_hex, 16) if frame_hex else 0

            if not hwnd:
                client_hwnd = target.winfo_id()
                hwnd = ctypes.windll.user32.GetParent(client_hwnd)
                if not hwnd:
                    hwnd = client_hwnd

            value = c_int(1 if dark else 0)

            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ret = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(value), sizeof(value)
            )

            if ret != 0:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 19, byref(value), sizeof(value)
                )
        except Exception:
            pass

    def _apply_theme(self):
        t = self._t
        self._set_titlebar_dark(self._dark)

        self.root.config(bg=t["bg"])
        self._sidebar.config(bg=t["sidebar_bg"])
        self._border_line.config(bg=t["border"])
        self._content.config(bg=t["content_bg"])
        self._div_top.config(bg=t["border"])
        self._div_bot.config(bg=t["border"])
        self._sidebar_spacer.config(bg=t["sidebar_bg"])
        self._lbl_title.config(bg=t["sidebar_bg"], fg=t["text"])
        self._update_license_status()

        self._theme_row.config(bg=t["sidebar_bg"])
        self._theme_inner.config(bg=t["sidebar_bg"])
        self._sun_canvas.config(bg=t["sidebar_bg"])
        self._moon_canvas.config(bg=t["sidebar_bg"])
        self._theme_toggle.set_colors(
            on_fill=t["accent"],
            off_fill="#2a2a3c" if self._dark else "#c0bdd0",
            thumb_on="#ffffff",
            thumb_off="#7e7e98" if self._dark else "#9898a8",
            parent_bg=t["sidebar_bg"],
        )
        self._draw_sun_icon()
        self._draw_moon_icon()

        # Screen frames and their heading labels
        for frame in self._frames.values():
            frame.config(bg=t["content_bg"])
            self._style_screen_labels(frame, t)

        # ── Home-specific widgets ────────────────────────────
        self._home_toolbar.config(bg=t["content_bg"])

        # ── PillButton batch theming ──────────────────────────
        # Compute a dimmed accent for disabled primary buttons
        _dis_fill = "#352450" if self._dark else "#c4b0e0"

        for btn in self._primary_pills:
            btn.set_colors(
                fill=t["accent"], fg=t["text_on_accent"],
                hover_fill=t["accent_hover"], hover_fg=t["text_on_accent"],
                disabled_fill=_dis_fill,
                disabled_fg=t["text_secondary"],
                parent_bg=t["content_bg"],
            )

        for btn in self._secondary_pills:
            btn.set_colors(
                fill=t["content_bg"], fg=t["accent"],
                outline=t["border"],
                hover_fill=t["content_bg"], hover_fg=t["accent"],
                hover_outline=t["accent"],
                disabled_fg=t["text_secondary"],
                parent_bg=t["content_bg"],
            )

        # ── Home-specific non-button widgets ─────────────────
        self._file_list_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._file_listbox.config(
            bg=t["bg"],
            fg=t["text"],
            selectbackground=t["accent"],
            selectforeground=t["text_on_accent"],
        )
        # GlassScrollbar theming
        _sb_thumb = t["scrollbar_thumb"]
        _sb_hover = t["scrollbar_hover"]
        for sb in self._glass_scrollbars:
            sb.set_colors(thumb=_sb_thumb, thumb_hover=_sb_hover,
                          parent_bg=t["bg"])
        self._lbl_empty.config(bg=t["bg"], fg=t["text_secondary"])
        self._lbl_file_count.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._home_out_row.config(bg=t["content_bg"])
        self._out_path_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._lbl_output_path.config(bg=t["bg"], fg=t["text_secondary"])

        # ── Results-specific widgets ──────────────────────────
        self._results_scroll_outer.config(bg=t["content_bg"])
        self._results_canvas.config(bg=t["content_bg"])
        self._results_content.config(bg=t["content_bg"])
        self._style_screen_labels(self._results_content, t)

        self._results_status_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._results_status_lbl.config(bg=t["bg"], fg=t["text_secondary"])

        self._results_out_row.config(bg=t["content_bg"])
        self._results_out_path_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._results_out_path_lbl.config(bg=t["bg"], fg=t["text_secondary"])

        # Per-file list theming
        self._results_files_section_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._results_files_div.config(bg=t["border"])
        self._results_files_outer.config(bg=t["bg"], highlightbackground=t["border"])
        if self._results_files_canvas:
            self._results_files_canvas.config(bg=t["bg"])
        if self._results_files_inner:
            self._results_files_inner.config(bg=t["bg"])
            for child in self._results_files_inner.winfo_children():
                if child.winfo_class() == "Frame":
                    child.config(bg=t["bg"])
                    for sub in child.winfo_children():
                        if sub.winfo_class() == "Label":
                            # Preserve badge-specific colors — only set bg
                            sub.config(bg=t["bg"])
                elif child.winfo_class() == "Label":
                    child.config(bg=t["bg"], fg=t["text_secondary"])

        self._results_conf_section_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._results_conf_div.config(bg=t["border"])
        self._results_conf_frame.config(bg=t["content_bg"])
        for lbl in self._results_conf_level_lbls:
            lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._results_val_section_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._results_val_div.config(bg=t["border"])
        self._results_val_frame.config(bg=t["content_bg"])
        # Validation count labels are themed by the winfo_children walk below
        # Theme every child label inside the validation counts frame
        for child in self._results_val_frame.winfo_children():
            if child.winfo_class() == "Label":
                child.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._results_val_issues_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._results_val_issues_text.config(bg=t["bg"], insertbackground=t["text"])
        # fg is set dynamically by _populate_results (cyan for issues, accent for pass)

        self._results_warn_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._results_warn_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._results_warn_text.config(
            bg=t["bg"], fg=t["text"], insertbackground=t["text"])

        self._results_btn_row.config(bg=t["content_bg"])

        # ── Watch-specific widgets ────────────────────────────
        self._watch_input_row.config(bg=t["content_bg"])
        self._watch_input_path_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._watch_input_path_lbl.config(bg=t["bg"], fg=t["text_secondary"])

        self._watch_output_row.config(bg=t["content_bg"])
        self._watch_output_path_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._watch_output_path_lbl.config(bg=t["bg"], fg=t["text_secondary"])

        self._watch_format_row.config(bg=t["content_bg"])
        self._watch_format_lbl.config(bg=t["content_bg"], fg=t["text"])
        self._watch_format_note_lbl.config(bg=t["content_bg"], fg=t["accent_secondary"])

        self._watch_ctrl_row.config(bg=t["content_bg"])
        self._watch_status_lbl.config(bg=t["content_bg"])
        if not (self._watcher and self._watcher.is_running):
            self._watch_status_lbl.config(fg=t["text_secondary"])
        self._watch_counts_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._watch_progress_row.config(bg=t["content_bg"])
        self._watch_file_lbl.config(bg=t["content_bg"], fg=t["text"])
        self._watch_stage_lbl.config(bg=t["content_bg"], fg=t["accent_secondary"])
        self._watch_progress_bar.set_colors(
            track=t["bg"], fill=t["accent"], border=t["border"],
            parent_bg=t["content_bg"])

        self._watch_log_section_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._watch_log_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._watch_log.config(bg=t["bg"], fg=t["text"], insertbackground=t["text"])

        self._watch_btn_row.config(bg=t["content_bg"])

        # ── Conversion-specific widgets ───────────────────────
        self._conv_overall_row.config(bg=t["content_bg"])
        self._conv_overall_lbl.config(bg=t["content_bg"], fg=t["text"])
        self._conv_overall_count_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._conv_elapsed_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._conv_overall_bar.set_colors(
            track=t["bg"], fill=t["accent"], border=t["border"],
            parent_bg=t["content_bg"])

        self._conv_file_row.config(bg=t["content_bg"])
        self._conv_file_name_lbl.config(bg=t["content_bg"], fg=t["text"])
        self._conv_stage_lbl.config(bg=t["content_bg"], fg=t["accent_secondary"])

        self._conv_file_bar.set_colors(
            track=t["bg"], fill=t["accent"], border=t["border"],
            parent_bg=t["content_bg"])

        self._conv_log_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._conv_log_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._conv_log.config(
            bg=t["bg"], fg=t["text"],
            insertbackground=t["text"],
        )

        # ── Settings-specific widgets ────────────────────────
        # _settings_content is embedded inside a Canvas window so it is NOT
        # reached by the _style_screen_labels traversal above.  Walk it
        # explicitly first, then apply per-widget color overrides below.
        self._settings_canvas.config(bg=t["content_bg"])
        self._settings_content.config(bg=t["content_bg"])
        self._style_screen_labels(self._settings_content, t)

        for lbl in self._settings_section_hdrs:
            lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        for sep in self._settings_dividers:
            sep.config(bg=t["border"])

        for lbl in self._settings_info_labels:
            lbl.config(bg=t["content_bg"], fg=t["accent_secondary"])

        _off_track = "#2a2a3c" if self._dark else "#c0bdd0"
        _thumb_off = "#7e7e98" if self._dark else "#9898a8"

        for tog in self._settings_toggles:
            tog.set_colors(
                on_fill=t["accent"],
                off_fill=_off_track,
                thumb_on="#ffffff",
                thumb_off=_thumb_off,
                parent_bg=t["content_bg"],
            )

        for dd in self._settings_dropdowns:
            dd.set_colors(
                fill=t["sidebar_bg"],
                fg=t["text"],
                border=t["border"],
                hover_fill=t["nav_hover_bg"],
                popup_bg=t["sidebar_bg"],
                popup_fg=t["text"],
                popup_hover_bg=t["nav_hover_bg"],
                popup_accent=t["accent"],
                chevron=t["text_secondary"],
                parent_bg=t["content_bg"],
            )

        for lbl in self._settings_default_lbls:
            lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        if self._sysinfo_card:
            self._sysinfo_card.config(
                bg=t["content_bg"], highlightbackground=t["border"])
            for lbl in self._sysinfo_labels:
                lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._refresh_nav()

    def _style_screen_labels(self, widget, t):
        cls = widget.winfo_class()
        if cls == "Canvas":
            return  # PillButtons handle their own theming
        if cls == "Label":
            widget.config(bg=t["content_bg"], fg=t["text"])
        elif cls == "Frame":
            widget.config(bg=t["content_bg"])
            for child in widget.winfo_children():
                self._style_screen_labels(child, t)

    @staticmethod
    def _detect_system_dark_mode() -> bool:
        """Detect OS dark mode preference. Returns True for dark, False for light."""
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return value == 0  # 0 = dark, 1 = light
            except Exception:
                return True  # default to dark
        elif sys.platform == "darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True, text=True, timeout=2)
                return "dark" in result.stdout.lower()
            except Exception:
                return True
        else:
            # Linux: check GTK theme name for "dark" keyword
            try:
                import subprocess
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True, text=True, timeout=2)
                if "dark" in result.stdout.lower():
                    return True
                result = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                    capture_output=True, text=True, timeout=2)
                return "dark" in result.stdout.lower()
            except Exception:
                return True

    @staticmethod
    def _scroll_units(event) -> int:
        """Normalize mousewheel delta to scroll units across platforms."""
        if event.delta:
            if sys.platform == "darwin":
                return -event.delta
            return -1 * (event.delta // 120)
        return 0

    def _bind_scroll(self, widget, target=None, parent_target=None):
        """Bind mouse-wheel scroll support on *widget*.

        Parameters
        ----------
        widget : tk widget
            The widget that receives <Enter>/<Leave> events.
        target : tk widget or None
            The scrollable widget whose yview_scroll is called.
            Defaults to *widget* itself.
        parent_target : tk widget or None
            If set, <Leave> restores _scroll_target to this widget
            (useful for nested scrollable areas inside a canvas).
            If None, <Leave> clears _scroll_target to None.
        """
        target = target or widget
        widget.bind("<Enter>", lambda _e, t=target: setattr(self, '_scroll_target', t))
        if parent_target is not None:
            widget.bind(
                "<Leave>",
                lambda _e, t=target, p=parent_target:
                    setattr(self, '_scroll_target', p)
                    if self._scroll_target is t else None)
        else:
            widget.bind(
                "<Leave>",
                lambda _e, t=target:
                    setattr(self, '_scroll_target', None)
                    if self._scroll_target is t else None)

    # ── Startup checks ──────────────────────────────────────

    _APP_VERSION = "1.2.0"
    _UPDATE_URL = "https://darksquare.dev/version.json"

    def _startup_checks(self):
        """Run non-blocking startup checks after the window is visible."""
        import threading
        threading.Thread(target=self._check_updates, daemon=True).start()
        threading.Thread(target=self._check_dependencies, daemon=True).start()

    def _check_updates(self):
        """Check for updates in background thread. Non-blocking, silent on failure."""
        try:
            import urllib.request
            import json as _json
            req = urllib.request.Request(
                self._UPDATE_URL,
                headers={"User-Agent": f"DocToMarkdown/{self._APP_VERSION}"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
            latest = data.get("latest_version", "")
            download_url = data.get("download_url", "https://darksquare.dev")
            if latest and latest != self._APP_VERSION:
                # Schedule UI notification on the main thread
                try:
                    self.root.after(0, lambda: self._show_update_banner(latest, download_url))
                except Exception:
                    pass  # root may have been destroyed during shutdown
        except Exception:
            pass  # silent — no network is fine

    def _show_update_banner(self, latest: str, url: str):
        """Show a non-intrusive update notification at the top of the Home screen."""
        t = self._t
        home = self._frames.get("Home")
        if not home:
            return
        banner = tk.Frame(home, bg=t["accent"], pady=4)
        # Home uses grid layout — place banner at top spanning full width.
        # Row 0 holds the title; use a negative-pad row by reconfiguring.
        banner.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        banner.lift()  # ensure banner renders on top of the title row
        msg = tk.Label(
            banner,
            text=f"  Update available: v{latest}  —  Visit darksquare.dev to download",
            font=(_FONT_FAMILY, 10), fg=t["text_on_accent"], bg=t["accent"],
            anchor="w", cursor="hand2",
        )
        msg.pack(side="left", fill="x", expand=True)
        msg.bind("<Button-1>", lambda _: __import__("webbrowser").open(url))
        dismiss = tk.Label(
            banner, text=" ✕ ", font=(_FONT_FAMILY, 10, "bold"),
            fg=t["text_on_accent"], bg=t["accent"], cursor="hand2",
        )
        dismiss.pack(side="right", padx=(0, 8))
        dismiss.bind("<Button-1>", lambda _: banner.destroy())

    def _check_dependencies(self):
        """Check for optional dependencies and show a one-time notice if any are missing."""
        # When running from a PyInstaller bundle all dependencies are already
        # packaged inside the frozen executable — skip the check entirely.
        if getattr(sys, "frozen", False):
            return

        # Only check once per source install
        if self._cfg.get("_dep_check_done"):
            return

        import importlib.util
        import shutil

        missing = []
        checks = [
            ("RapidOCR", "rapidocr_onnxruntime",
             "Primary OCR engine for scanned documents and images"),
            ("Tesseract", "pytesseract",
             "Fallback OCR engine (requires Tesseract binary)"),
            ("Docling", "docling",
             "AI-powered document layout analysis for complex PDFs"),
        ]
        # Use find_spec instead of __import__ — checks if the module is
        # installed without actually loading heavy ML frameworks (PyTorch,
        # TensorFlow, etc.) which would block for many seconds.
        for name, module, desc in checks:
            if importlib.util.find_spec(module) is None:
                missing.append((name, desc))

        # Special check: Tesseract binary on PATH
        if not any(n == "Tesseract" for n, _ in missing):
            if shutil.which("tesseract") is None:
                missing.append(("Tesseract binary",
                                "pytesseract installed but tesseract not found in PATH"))

        # Schedule the config write on the main thread to avoid a data race
        # with _on_setting_changed() which also reads/writes self._cfg.
        try:
            self.root.after(0, lambda: self._mark_dep_check_done())
        except Exception:
            pass

        if not missing:
            return

        # Schedule the themed dialog on the main thread
        try:
            self.root.after(500, lambda m=missing: self._show_dependency_dialog(m))
        except Exception:
            pass  # root may have been destroyed during shutdown

    def _mark_dep_check_done(self):
        """Write the dep-check-done flag on the main thread (avoids data race)."""
        self._cfg["_dep_check_done"] = True
        _cfg_mod.save(self._cfg)

    def _show_dependency_dialog(self, missing: list):
        """Show a themed dialog listing missing optional components.

        Only shown when running from source (never from the PyInstaller
        installer, which bundles all dependencies).
        """
        t = self._t
        # Calculate height based on number of missing items
        base_h = 260
        per_item = 52
        win_h = base_h + len(missing) * per_item

        win = tk.Toplevel(self.root)
        win.title("Optional Components")
        win_w = int(460 * self._dpi)
        win_h_px = int(win_h * self._dpi)
        # Centre on the main window
        rx = self.root.winfo_x() + (self.root.winfo_width() - win_w) // 2
        ry = self.root.winfo_y() + (self.root.winfo_height() - win_h_px) // 2
        win.geometry(f"{win_w}x{win_h_px}+{max(0, rx)}+{max(0, ry)}")
        win.config(bg=t["bg"])
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        self._set_titlebar_dark(self._dark, win)

        pad = 24

        # ── Icon + title row ──
        header = tk.Frame(win, bg=t["bg"])
        header.pack(fill="x", padx=pad, pady=(pad, 0))
        tk.Label(
            header, text="ℹ", font=(_FONT_FAMILY, 22),
            fg=t["accent"], bg=t["bg"],
        ).pack(side="left", padx=(0, 10))
        tk.Label(
            header, text="Optional Components",
            font=(_FONT_FAMILY, 14, "bold"),
            fg=t["text"], bg=t["bg"],
        ).pack(side="left", anchor="w")

        # ── Description ──
        tk.Label(
            win,
            text="Some optional components were not found. Conversions\n"
                 "will use the best available engine automatically.",
            font=(_FONT_FAMILY, 10),
            fg=t["text_secondary"], bg=t["bg"],
            justify="left", anchor="w",
        ).pack(fill="x", padx=pad, pady=(12, 8))

        # ── Missing items list ──
        list_frame = tk.Frame(win, bg=t["content_bg"],
                              highlightbackground=t["border"],
                              highlightthickness=1)
        list_frame.pack(fill="x", padx=pad, pady=(0, 12))

        for i, (name, desc) in enumerate(missing):
            row = tk.Frame(list_frame, bg=t["content_bg"])
            row.pack(fill="x", padx=12, pady=(8 if i == 0 else 2, 8 if i == len(missing) - 1 else 2))
            tk.Label(
                row, text=f"•  {name}", font=(_FONT_FAMILY, 10, "bold"),
                fg=t["accent"], bg=t["content_bg"], anchor="w",
            ).pack(anchor="w")
            tk.Label(
                row, text=f"    {desc}", font=(_FONT_FAMILY, 9),
                fg=t["text_secondary"], bg=t["content_bg"], anchor="w",
                wraplength=int(390 * self._dpi),
            ).pack(anchor="w")

        # ── Hint ──
        tk.Label(
            win,
            text="Run  python setup.py  to install all components.",
            font=(_FONT_FAMILY, 9),
            fg=t["text_secondary"], bg=t["bg"],
            anchor="w",
        ).pack(fill="x", padx=pad, pady=(0, 16))

        # ── OK button ──
        btn_frame = tk.Frame(win, bg=t["bg"])
        btn_frame.pack(fill="x", padx=pad, pady=(0, pad))
        ok_btn = PillButton(
            btn_frame, text="OK",
            style="primary",
            font=(_FONT_FAMILY, 10, "bold"),
            padx=26, pady=8,
            command=win.destroy,
        )
        ok_btn.set_colors(
            fill=t["accent"], fg=t["text_on_accent"],
            hover_fill=t["accent_hover"], hover_fg=t["text_on_accent"],
            parent_bg=t["bg"],
        )
        ok_btn.pack(anchor="e")

    # ── Cleanup ──────────────────────────────────────────────

    def _on_close(self):
        if self._active_job and self._active_job.is_running():
            if not messagebox.askyesno(
                "Conversion in Progress",
                "A conversion is currently running.\n\n"
                "Are you sure you want to close the application?",
                parent=self.root,
            ):
                return
            self._active_job.cancel()
            thread = getattr(self._active_job, '_thread', None)
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
        if self._watcher and self._watcher.is_running:
            self._watcher.stop()
        # Cancel pending after() callbacks to prevent TclError on destroyed root
        for attr in ("_watch_notify_id", "_elapsed_after_id", "_results_notify_id"):
            pending = getattr(self, attr, None)
            if pending is not None:
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
        self.root.destroy()

    # ── Run ──────────────────────────────────────────────────

    def run(self):
        # Apply title bar theme after the event loop starts.
        # The window must be fully mapped before DWM will accept the attribute.
        self.root.after(100, lambda: self._set_titlebar_dark(self._dark))
        self.root.mainloop()
