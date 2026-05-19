import math
import os
import re
import sys
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

_SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv",
                   ".pptx", ".epub", ".dxf",
                   ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

_FILETYPES = [
    ("Supported files",  "*.pdf *.docx *.doc *.xlsx *.xls *.csv *.pptx *.epub *.dxf *.png *.jpg *.jpeg *.tiff *.bmp"),
    ("PDF files",        "*.pdf"),
    ("Word documents",   "*.docx *.doc"),
    ("PowerPoint files", "*.pptx"),
    ("EPUB e-books",     "*.epub"),
    ("DXF drawings",     "*.dxf"),
    ("Excel files",      "*.xlsx *.xls"),
    ("CSV files",        "*.csv"),
    ("Image files",      "*.png *.jpg *.jpeg *.tiff *.bmp"),
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
        "search indexing."
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
        "convert batches faster but use more memory and CPU. Start with 1 and "
        "increase if you are converting many files and have available system resources."
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
        "and scanned pages. Auto uses PaddleOCR (higher accuracy, deep "
        "learning) with Tesseract as fallback. Choose PaddleOCR for best "
        "results on engineering drawings, complex layouts, and non-Latin "
        "scripts. Choose Tesseract for faster, lighter processing, or if "
        "PaddleOCR is not installed."
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
            self._dpi = 1.0

        from .widgets import set_dpi_scale
        set_dpi_scale(self._dpi)

        self.root.title("Document to Markdown Converter")
        self.root.geometry(f"{int(960 * self._dpi)}x{int(640 * self._dpi)}")
        self.root.minsize(int(720 * self._dpi), int(500 * self._dpi))

        # Load config first — theme preference is stored here
        self._cfg = _cfg_mod.load()

        self._dark = (self._cfg.get("theme", "light") == "dark")
        self._t = themes.DARK if self._dark else themes.LIGHT
        self._nav_btns: dict[str, tk.Button] = {}
        self._frames:   dict[str, tk.Frame]  = {}
        self._current   = "Home"

        # Home screen state
        self._selected_files: list[str] = []
        self._file_aliases:   dict[str, str] = {}   # path → custom output name
        self._output_path: str = ""

        # Settings state (config already loaded above)
        self._setting_vars:        dict = {}
        self._settings_section_hdrs: list[tk.Label]  = []
        self._settings_dividers:     list[tk.Frame]  = []
        self._settings_info_labels:  list[tk.Label]  = []
        self._settings_name_labels:  list[tk.Label]  = []
        self._settings_toggles:   list[tk.Widget] = []
        self._settings_dropdowns:    list[tk.Widget] = []
        self._settings_default_lbls: list[tk.Label]  = []

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
            import sys as _sys
            _sys.stderr.write(f"Unhandled error:\n{msg}\n")
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

        self._div_bot = tk.Frame(self._sidebar, height=1)
        self._div_bot.grid(row=10, column=0, sticky="ew", padx=12, pady=(0, 4))

        # Theme toggle: [sun] [toggle] [moon]
        self._theme_row = tk.Frame(self._sidebar)
        self._theme_row.grid(row=11, column=0, sticky="ew", padx=8, pady=(0, 14))
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
            text="No output folder selected",
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

        self._settings_scroll_outer.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', canvas))
        self._settings_scroll_outer.bind(
            "<Leave>", lambda _e: setattr(self, '_scroll_target', None)
            if self._scroll_target is canvas else None)

        self._settings_canvas = canvas

        # col 0 = ⓘ icon, col 1 = label (expands), col 2 = control, col 3 = default hint
        self._settings_content.grid_columnconfigure(1, weight=1)

        row = 0

        # Section: Conversion
        row = self._settings_add_section(self._settings_content, "Conversion", row, first=True)
        row = self._settings_add_dropdown(
            self._settings_content, "conversion_mode", "Conversion Mode",
            ["Standard", "OCR", "Auto-detect"],
            _TIPS["conversion_mode"], row,
            default_hint="default: Auto-detect",
        )

        # Section: Content Handling
        row = self._settings_add_section(self._settings_content, "Content Handling", row)
        row = self._settings_add_checkbox(
            self._settings_content, "preserve_images", "Preserve Images",
            _TIPS["preserve_images"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "embed_images", "Embed Images in File (Base64)",
            _TIPS["embed_images"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "preserve_page_numbers", "Preserve Page Numbers",
            _TIPS["preserve_page_numbers"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "rebuild_toc", "Rebuild Table of Contents",
            _TIPS["rebuild_toc"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "remove_headers_footers", "Remove Headers and Footers",
            _TIPS["remove_headers_footers"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "skip_blank_pages", "Skip Blank Pages",
            _TIPS["skip_blank_pages"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "strip_line_numbers", "Strip Line Numbers",
            _TIPS["strip_line_numbers"], row,
            default_hint="default: off",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "detect_code_blocks", "Detect Code Blocks",
            _TIPS["detect_code_blocks"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "detect_footnotes", "Detect Footnotes",
            _TIPS["detect_footnotes"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "detect_equations", "Detect Equations",
            _TIPS["detect_equations"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "dxf_svg_preview", "DXF Drawing Preview",
            _TIPS["dxf_svg_preview"], row,
            default_hint="default: on",
        )

        # Section: Performance
        row = self._settings_add_section(self._settings_content, "Performance", row)
        row = self._settings_add_dropdown(
            self._settings_content, "parallel_workers", "Parallel Workers",
            ["1", "2", "4", "Auto"],
            _TIPS["parallel_workers"], row,
            default_hint="default: 1",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "quality_preset", "Conversion Quality",
            ["Fast", "Balanced", "Quality"],
            _TIPS["quality_preset"], row,
            default_hint="default: Quality",
        )

        # Section: OCR
        row = self._settings_add_section(self._settings_content, "OCR", row)
        row = self._settings_add_dropdown(
            self._settings_content, "ocr_language", "OCR Language",
            ["English", "French", "German", "Spanish", "Italian", "Portuguese",
             "Dutch", "Auto-detect"],
            _TIPS["ocr_language"], row,
            default_hint="default: English",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "ocr_engine", "OCR Engine",
            ["Auto", "PaddleOCR", "Tesseract"],
            _TIPS["ocr_engine"], row,
            default_hint="default: Auto",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "auto_translate", "Auto-Translate OCR Text",
            _TIPS["auto_translate"], row,
            default_hint="default: on",
        )

        # Section: Output
        row = self._settings_add_section(self._settings_content, "Output", row)
        row = self._settings_add_dropdown(
            self._settings_content, "output_format", "Output Format",
            ["Markdown", "JSON", "HTML", "Plain Text", "RAG Chunks"],
            _TIPS["output_format"], row,
            default_hint="default: Markdown",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "markdown_flavor", "Markdown Flavor",
            ["GFM", "Obsidian", "Pandoc"],
            _TIPS["markdown_flavor"], row,
            default_hint="default: GFM",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "yaml_front_matter", "YAML Front Matter",
            _TIPS["yaml_front_matter"], row,
            default_hint="default: on",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "overwrite_existing", "Overwrite Existing Files",
            _TIPS["overwrite_existing"], row,
            default_hint="default: off",
        )
        row = self._settings_add_checkbox(
            self._settings_content, "output_subfolder", "Output Subfolder Structure",
            _TIPS["output_subfolder"], row,
            default_hint="default: off",
        )
        row = self._settings_add_dropdown(
            self._settings_content, "low_confidence_action", "Handle Low Confidence Results",
            ["Ask me", "Keep and flag", "Skip"],
            _TIPS["low_confidence_action"], row,
            default_hint="default: Ask me",
        )

        # Section: Post-Processing Rules
        row = self._settings_add_section(self._settings_content, "Post-Processing Rules", row)

        info = tk.Label(self._settings_content, text="ⓘ", font=("Segoe UI", 12), cursor="question_arrow")
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
        row += 1

        # ── Reset to Defaults button ──────────────────────────
        row = self._settings_add_section(self._settings_content, "Reset", row)
        self._btn_reset_defaults = PillButton(
            self._settings_content,
            text="Reset to Defaults",
            font=_FONT_SMALL,
            style="secondary",
            padx=14, pady=6,
            command=self._on_reset_defaults,
        )
        self._btn_reset_defaults.grid(
            row=row, column=1, columnspan=3, sticky="w", pady=(4, 16))
        self._secondary_pills.append(self._btn_reset_defaults)

    def _settings_add_section(self, parent, title: str, row: int, first=False) -> int:
        top_pad = 8 if first else 18
        lbl = tk.Label(parent, text=title.upper(), font=_FONT_SECTION, anchor="w")
        lbl.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(top_pad, 2))
        sep = tk.Frame(parent, height=1)
        sep.grid(row=row + 1, column=0, columnspan=4, sticky="ew", pady=(0, 2))
        self._settings_section_hdrs.append(lbl)
        self._settings_dividers.append(sep)
        return row + 2

    def _settings_add_checkbox(self, parent, key, label, tip, row, default_hint="") -> int:
        info = tk.Label(parent, text="ⓘ", font=("Segoe UI", 12), cursor="question_arrow")
        info.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 4))
        Tooltip(info, tip, lambda: self._t)

        lbl = tk.Label(parent, text=label, font=_FONT_SMALL, anchor="w")
        lbl.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        var = self._setting_vars[key]
        cb = ToggleSwitch(parent, variable=var)
        cb.grid(row=row, column=2, sticky="e", pady=4, padx=(0, 8))

        hint_lbl = tk.Label(parent, text=default_hint, font=("Segoe UI", 9), anchor="e")
        hint_lbl.grid(row=row, column=3, sticky="e", pady=4, padx=(0, 4))

        self._settings_info_labels.append(info)
        self._settings_name_labels.append(lbl)
        self._settings_toggles.append(cb)
        self._settings_default_lbls.append(hint_lbl)
        return row + 1

    def _settings_add_dropdown(self, parent, key, label, options, tip, row, default_hint="") -> int:
        info = tk.Label(parent, text="ⓘ", font=("Segoe UI", 12), cursor="question_arrow")
        info.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 4))
        Tooltip(info, tip, lambda: self._t)

        lbl = tk.Label(parent, text=label, font=_FONT_SMALL, anchor="w")
        lbl.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=4)

        var = self._setting_vars[key]
        menu = GlassDropdown(parent, variable=var, options=options,
                             font=_FONT_SMALL)
        menu.grid(row=row, column=2, sticky="e", pady=3, padx=(0, 8))

        hint_lbl = tk.Label(parent, text=default_hint, font=("Segoe UI", 9), anchor="e")
        hint_lbl.grid(row=row, column=3, sticky="e", pady=4, padx=(0, 4))

        self._settings_info_labels.append(info)
        self._settings_name_labels.append(lbl)
        self._settings_dropdowns.append(menu)
        self._settings_default_lbls.append(hint_lbl)
        return row + 1

    def _on_setting_changed(self, *_):
        if getattr(self, '_resetting_defaults', False):
            return
        for key, var in self._setting_vars.items():
            self._cfg[key] = var.get()
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
        self._conv_overall_row.grid_columnconfigure(0, weight=1)

        self._conv_overall_lbl = tk.Label(
            self._conv_overall_row, text="Overall Progress", font=_FONT_SMALL, anchor="w")
        self._conv_overall_lbl.grid(row=0, column=0, sticky="w")

        self._conv_overall_count_lbl = tk.Label(
            self._conv_overall_row, text="0 of 0 files", font=_FONT_SMALL, anchor="e")
        self._conv_overall_count_lbl.grid(row=0, column=1, sticky="e")

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

        self._results_scroll_outer.bind(
            "<Enter>", lambda _e: setattr(self, '_scroll_target', r_canvas))
        self._results_scroll_outer.bind(
            "<Leave>", lambda _e: setattr(self, '_scroll_target', None)
            if self._scroll_target is r_canvas else None)

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

        # ── Confidence summary ───────────────────────────────
        self._results_conf_section_lbl = tk.Label(
            rc, text="CONFIDENCE SUMMARY", font=_FONT_SECTION, anchor="w")
        self._results_conf_section_lbl.grid(
            row=2, column=0, sticky="ew", padx=32, pady=(0, 2))

        self._results_conf_div = tk.Frame(rc, height=1)
        self._results_conf_div.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 6))

        self._results_conf_frame = tk.Frame(rc)
        self._results_conf_frame.grid(row=4, column=0, sticky="ew", padx=32, pady=(0, 16))
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
            row=5, column=0, sticky="ew", padx=32, pady=(0, 2))

        self._results_val_div = tk.Frame(rc, height=1)
        self._results_val_div.grid(row=6, column=0, sticky="ew", padx=32, pady=(0, 6))

        self._results_val_frame = tk.Frame(rc)
        self._results_val_frame.grid(row=7, column=0, sticky="ew", padx=32, pady=(0, 16))
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
            row=8, column=0, sticky="nsew", padx=32, pady=(0, 8))
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

        # ── Warnings ─────────────────────────────────────────
        self._results_warn_lbl = tk.Label(rc, text="Warnings", font=_FONT_SMALL, anchor="w")
        self._results_warn_lbl.grid(row=9, column=0, sticky="w", padx=32, pady=(0, 4))

        self._results_warn_frame = tk.Frame(rc, highlightthickness=1)
        self._results_warn_frame.grid(row=10, column=0, sticky="nsew", padx=32, pady=(0, 8))
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

        # ── Button row ───────────────────────────────────────
        self._results_btn_row = tk.Frame(rc)
        self._results_btn_row.grid(row=11, column=0, sticky="ew", padx=32, pady=(0, 28))

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

    # ── Watch Folder screen ─────────────────────────────────

    def _build_watch(self):
        f = self._new_screen("Watch")
        f.grid_rowconfigure(6, weight=1)

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

        # ── Controls row ─────────────────────────────────────
        self._watch_ctrl_row = tk.Frame(f)
        self._watch_ctrl_row.grid(row=4, column=0, sticky="ew", padx=32, pady=(0, 8))
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

        # ── Activity log section label ───────────────────────
        self._watch_log_section_lbl = tk.Label(
            f, text="ACTIVITY LOG", font=_FONT_SECTION, anchor="w")
        self._watch_log_section_lbl.grid(
            row=5, column=0, sticky="ew", padx=32, pady=(0, 2))

        # ── Activity log ─────────────────────────────────────
        self._watch_log_frame = tk.Frame(f, highlightthickness=1)
        self._watch_log_frame.grid(row=6, column=0, sticky="nsew", padx=32, pady=(0, 8))
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

        # ── Bottom button row ────────────────────────────────
        self._watch_btn_row = tk.Frame(f)
        self._watch_btn_row.grid(row=7, column=0, sticky="ew", padx=32, pady=(0, 28))

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
        if not self._watch_output_path:
            messagebox.showwarning("Watch Folder", "Please select an output folder.")
            return

        cfg = dict(self._cfg)

        self._watcher = _watch_mod.FolderWatcher(
            watch_path=self._watch_input_path,
            output_path=self._watch_output_path,
            cfg=cfg,
            root=self.root,
            on_file_queued=self._watch_on_queued,
            on_file_started=self._watch_on_started,
            on_file_done=self._watch_on_done,
            on_error=self._watch_on_error,
        )
        self._watcher.start()

        self._btn_watch_start.set_text("Stop Watching")
        self._watch_status_lbl.config(text="Watching...", fg=self._t.get("accent", "#7c3aed"))
        self._watch_log_append(f"Started watching: {self._watch_input_path}")
        self._watch_log_append(f"Output folder: {self._watch_output_path}")

    def _stop_watch(self):
        if self._watcher:
            self._watcher.stop()
        self._btn_watch_start.set_text("Start Watching")
        self._watch_status_lbl.config(text="Stopped", fg=self._t["text_secondary"])
        self._watch_log_append("Stopped watching.")

    def _watch_on_queued(self, path: str):
        filename = os.path.basename(path)
        self._watch_log_append(f"Detected: {filename}")
        self._update_watch_counts()

    def _watch_on_started(self, path: str):
        filename = os.path.basename(path)
        self._watch_log_append(f"Converting: {filename}...")

    def _watch_on_done(self, path: str, success: bool, message: str):
        prefix = "  ✓" if success else "  ✗"
        self._watch_log_append(f"{prefix} {message}")
        self._update_watch_counts()
        if success:
            self._watch_notify(os.path.basename(path))

    def _watch_on_error(self, message: str):
        self._watch_log_append(f"Error: {message}")

    def _watch_log_append(self, text: str):
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self._watch_log.config(state="normal")
        self._watch_log.insert("end", f"[{timestamp}] {text}\n")
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
            btn.config(fg=self._t.get("accent", "#7c3aed"))
            self.root.after(2000, lambda: btn.config(fg=self._t["text"]))

    # ── Debug / Preview window ──────────────────────────────

    def _show_debug_window(self):
        """Open a Toplevel window with diagnostic info about the last conversion."""
        result = getattr(self, "_last_batch_result", None)
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

        rule_name_var.trace_add("write", save_current_rule)
        rule_pattern_var.trace_add("write", save_current_rule)
        rule_replace_var.trace_add("write", save_current_rule)
        rule_enabled_var.trace_add("write", save_current_rule)
        rule_regex_var.trace_add("write", save_current_rule)

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

        def save_and_close():
            self._rule_profiles = profiles
            _rules_mod.save_profiles(profiles)
            profile_names = ["None"] + [p.name for p in profiles]
            self._rules_profile_dd.set_values(profile_names)
            win.destroy()

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
        result = getattr(self, "_last_batch_result", None)
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

        # ── Copy to clipboard button (pack BEFORE expanding selector) ─
        current_content = [""]  # mutable container for raw markdown

        def _copy_to_clipboard():
            win.clipboard_clear()
            win.clipboard_append(current_content[0])
            btn_copy.set_text("✓ Copied")
            win.after(1500, lambda: btn_copy.set_text("Copy Markdown")
                      if win.winfo_exists() else None)

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

        # ── Left panel: source info ──────────────────────────
        left_frame = tk.Frame(paned, bg=t["bg"])
        paned.add(left_frame, width=int(340 * self._dpi), minsize=int(200 * self._dpi))

        tk.Label(left_frame, text="SOURCE INFO", font=_FONT_SECTION,
                 bg=t["bg"], fg=t["text_secondary"], anchor="w"
                 ).pack(fill="x", padx=12, pady=(12, 4))
        tk.Frame(left_frame, height=1, bg=t["border"]).pack(fill="x", padx=12, pady=(0, 8))

        source_text = tk.Text(
            left_frame, font=_FONT_SMALL, wrap="word",
            bg=t["bg"], fg=t["text"],
            bd=0, highlightthickness=0,
            padx=12, pady=8, state="disabled",
        )
        source_text.pack(fill="both", expand=True)

        # ── Right panel: markdown preview ────────────────────
        right_frame = tk.Frame(paned, bg=t["bg"])
        paned.add(right_frame, minsize=int(300 * self._dpi))

        tk.Label(right_frame, text="CONVERTED OUTPUT", font=_FONT_SECTION,
                 bg=t["bg"], fg=t["text_secondary"], anchor="w"
                 ).pack(fill="x", padx=12, pady=(12, 4))
        tk.Frame(right_frame, height=1, bg=t["border"]).pack(fill="x", padx=12, pady=(0, 8))

        # ── Search bar (hidden by default) ───────────────────
        search_bar = tk.Frame(right_frame, bg=t["content_bg"])
        # Not packed initially — toggled by Ctrl+F

        search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_bar, textvariable=search_var, font=_FONT_SMALL,
            bg=t["bg"], fg=t["text"], insertbackground=t["text"],
            bd=0, highlightthickness=1, highlightcolor=t["accent"],
            highlightbackground=t["border"],
        )
        search_entry.pack(side="left", fill="x", expand=True, padx=(8, 4), pady=4)

        search_count_lbl = tk.Label(
            search_bar, text="", font=_FONT_SMALL,
            bg=t["content_bg"], fg=t["text_secondary"],
        )
        search_count_lbl.pack(side="left", padx=(0, 4))

        btn_prev_match = PillButton(
            search_bar, text="Prev", font=_FONT_SMALL,
            style="secondary", padx=8, pady=3, command=lambda: _prev_match(),
        )
        btn_prev_match.pack(side="left", padx=2, pady=4)
        btn_prev_match.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )

        btn_next_match = PillButton(
            search_bar, text="Next", font=_FONT_SMALL,
            style="secondary", padx=8, pady=3, command=lambda: _next_match(),
        )
        btn_next_match.pack(side="left", padx=2, pady=4)
        btn_next_match.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )

        btn_close_search = PillButton(
            search_bar, text="✕", font=_FONT_SMALL,
            style="secondary", padx=6, pady=3, command=lambda: _close_search(),
        )
        btn_close_search.pack(side="right", padx=(2, 8), pady=4)
        btn_close_search.set_colors(
            fill=t["content_bg"], fg=t["text"],
            hover_fill=t["accent"], parent_bg=t["content_bg"],
        )

        search_matches = []      # list of "line.col" positions
        search_current_idx = [0]  # mutable index
        search_visible = [False]
        search_debounce_id = [None]  # pending after() id for debounce

        preview_frame = tk.Frame(right_frame, bg=t["bg"])
        preview_frame.pack(fill="both", expand=True)
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        preview_text = tk.Text(
            preview_frame, font=("Consolas", 11), wrap="none",
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
        preview_text.grid(row=0, column=0, sticky="nsew")
        preview_sb.grid(row=0, column=1, sticky="ns")

        # ── Text tags for syntax highlighting ────────────────
        preview_text.tag_configure("heading", font=("Segoe UI", 14, "bold"), foreground=t["accent"])
        preview_text.tag_configure("heading2", font=("Segoe UI", 12, "bold"), foreground=t["accent"])
        preview_text.tag_configure("heading3", font=("Segoe UI", 11, "bold"), foreground=t["accent"])
        preview_text.tag_configure("bold", font=("Consolas", 11, "bold"))
        preview_text.tag_configure("frontmatter", foreground=t["text_secondary"], font=("Consolas", 10))
        preview_text.tag_configure("table", foreground="#8be9fd" if self._dark else "#0969da")
        preview_text.tag_configure("page_marker", foreground=t["text_secondary"], font=("Consolas", 10, "italic"))
        # New tags
        _code_bg = "#2a2a3d" if self._dark else "#eef0f4"
        preview_text.tag_configure("code_block", font=("Consolas", 10),
                                   background=_code_bg,
                                   foreground="#a9dc76" if self._dark else "#22863a",
                                   lmargin1=12, lmargin2=12, rmargin=12)
        preview_text.tag_configure("inline_code", font=("Consolas", 10),
                                   background=_code_bg)
        preview_text.tag_configure("blockquote", font=("Segoe UI", 11, "italic"),
                                   foreground=t["text_secondary"],
                                   lmargin1=24, lmargin2=24)
        preview_text.tag_configure("link", foreground=t["accent"], underline=True)
        preview_text.tag_configure("hr", foreground=t["border"],
                                   justify="center", font=("Consolas", 10))
        preview_text.tag_configure("list_bullet", foreground=t["accent"])
        preview_text.tag_configure("image_ref",
                                   foreground=t.get("accent_secondary", t["accent"]))
        # Search tags (higher priority — raised above other tags)
        preview_text.tag_configure("search_match",
                                   background="#ffd700" if self._dark else "#ffeaa7",
                                   foreground="#000000")
        preview_text.tag_configure("search_active",
                                   background=t["accent"],
                                   foreground=t["text_on_accent"])
        preview_text.tag_raise("search_match")
        preview_text.tag_raise("search_active")

        # Image reference list (prevent GC of PhotoImages)
        preview_images: list = []

        # ── Inline formatting regexes ────────────────────────
        _RE_INLINE_CODE = re.compile(r'`([^`]+)`')
        _RE_BOLD = re.compile(r'\*\*([^*]+)\*\*')
        _RE_LINK = re.compile(r'\[([^\]]+)\]\([^)]+\)')

        # ── Image thumbnail helper ───────────────────────────
        _RE_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        _IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff"}
        _RE_LIST = re.compile(r'^(\s*)([-*]|\d+\.)\s')

        def _load_thumbnail(file_dir: str, img_rel: str):
            """Load an image, return PhotoImage or None."""
            if img_rel.startswith("data:"):
                return None
            abs_path = os.path.normpath(os.path.join(file_dir, img_rel))
            ext = os.path.splitext(abs_path)[1].lower()
            if ext not in _IMG_EXTS or not os.path.isfile(abs_path):
                return None
            try:
                from PIL import Image, ImageTk
                img = Image.open(abs_path)
                max_w = 400
                if img.width > max_w:
                    ratio = max_w / img.width
                    img = img.resize(
                        (max_w, int(img.height * ratio)), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                preview_images.append(photo)  # prevent GC
                return photo
            except Exception:
                return None

        # ── load_file — two-pass bulk parser ─────────────────
        # Pass 1: classify lines (pure Python, no widget calls)
        # Pass 2: single bulk insert + batch tag application
        # Images deferred to after_idle for instant window render

        def load_file(rel_path):
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
            first_line = True

            for line in lines:
                stripped = line.strip()

                if stripped == "---" and first_line:
                    in_frontmatter = True
                    classified.append(("frontmatter", line))
                    first_line = False
                    continue
                first_line = False

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
                elif line.startswith(("## ", "### ")):
                    classified.append(("heading2", line))
                elif line.startswith(("#### ", "##### ", "###### ")):
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
                def _load_images():
                    preview_text.config(state="normal")
                    offset = 0
                    for idx, img_rel in img_entries:
                        photo = _load_thumbnail(file_dir, img_rel)
                        if photo:
                            ins_ln = idx + 1 + offset + 1
                            preview_text.insert(f"{ins_ln}.0", " \n")
                            preview_text.image_create(
                                f"{ins_ln}.0", image=photo)
                            offset += 1
                    preview_text.config(state="disabled")
                    # Image insertion shifts line numbers — refresh search
                    # results so match positions stay correct.
                    if search_visible[0] and search_var.get():
                        _do_search()
                win.after(50, _load_images)

        # ── Search functions ─────────────────────────────────
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
            if search_matches:
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

            preview_text.config(state="normal")
            # Collect all matches first, then apply tags in one call
            start = "1.0"
            match_ranges: list[str] = []
            count_var = tk.IntVar()
            while True:
                pos = preview_text.search(
                    query, start, stopindex=tk.END,
                    nocase=True, count=count_var)
                if not pos:
                    break
                matched_len = count_var.get() or len(query)
                end = f"{pos}+{matched_len}c"
                search_matches.append(pos)
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
                pos = search_matches[search_current_idx[0]]
                end = f"{pos}+{len(search_var.get())}c"
                preview_text.tag_add("search_active", pos, end)
                preview_text.see(pos)
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

        # Debounced live search — fires 300ms after last keystroke
        def _on_search_key(_event=None):
            if search_debounce_id[0] is not None:
                win.after_cancel(search_debounce_id[0])
            search_debounce_id[0] = win.after(300, _do_search)

        # Search bindings
        search_entry.bind("<Return>", _do_search)
        search_entry.bind("<Escape>", _close_search)
        _search_trace = search_var.trace_add("write", _on_search_key)
        win.bind("<Control-f>", _toggle_search)

        # Load first file
        load_file(file_display_names[0])

        # Bind file selector changes
        _file_trace = file_var.trace_add("write", lambda *_: load_file(file_var.get()))

        # Cleanup pending after() IDs and traces on window close
        def _on_preview_close():
            if search_debounce_id[0] is not None:
                try: win.after_cancel(search_debounce_id[0])
                except Exception: pass
            try: search_var.trace_remove("write", _search_trace)
            except Exception: pass
            try: file_var.trace_remove("write", _file_trace)
            except Exception: pass
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
                "Supported types: PDF, DOCX, XLSX, CSV, PNG, JPG, TIFF, BMP",
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

        for f in found:
            if f in already:
                lb.insert(tk.END, f"  {os.path.basename(f)}  · already added")
            else:
                lb.insert(tk.END, f"  {os.path.basename(f)}")

        # ── Button row (already packed at bottom) ────────────
        def confirm():
            for f in new_files:
                self._selected_files.append(f)
            self._update_file_list()
            dlg.destroy()

        btn_cancel = PillButton(btn_row, text="Cancel", command=dlg.destroy,
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
        self._update_file_list()

    def _pick_output_folder(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if not folder:
            return
        self._output_path = os.path.normpath(folder)
        self._lbl_output_path.config(text=self._output_path)
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
        import subprocess, sys as _sys
        if _sys.platform == "win32":
            os.startfile(path)
        elif _sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _on_cancel_conversion(self):
        if self._active_job and self._active_job.is_running():
            self._active_job.cancel()
            self._log_write("Cancellation requested — waiting for current file to finish…")
        else:
            messagebox.showinfo(
                "No Active Conversion",
                "No conversion is currently running.",
            )

    def _log_write(self, text: str):
        self._conv_log.config(state="normal")
        self._conv_log.insert(tk.END, text + "\n")
        self._conv_log.config(state="disabled")
        self._conv_log.see(tk.END)

    def _reset_conversion_screen(self):
        n = len(self._selected_files)
        self._conv_overall_bar.set_progress(0.0)
        self._conv_file_bar.set_progress(0.0)
        label = "1 file" if n == 1 else f"{n} files"
        self._conv_overall_count_lbl.config(text=f"0 of {label}")
        self._conv_file_name_lbl.config(text="Preparing…")
        self._conv_stage_lbl.config(text="")
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
        )
        self._active_job.start()

    def _set_file_progress(self, fraction: float) -> None:
        self._conv_file_bar.set_progress(fraction)

    def _set_overall_progress(self, fraction: float) -> None:
        self._conv_overall_bar.set_progress(fraction)

    def _on_file_start(self, filename: str, idx: int, total: int) -> None:
        self._conv_file_name_lbl.config(text=filename)
        self._conv_overall_count_lbl.config(text=f"{idx} of {total} file{'s' if total != 1 else ''}")

    def _on_stage_update(self, stage: str) -> None:
        self._conv_stage_lbl.config(text=stage)

    def _on_conversion_done(self, result: "_converter_mod.BatchResult") -> None:
        # Final bar states
        self._conv_overall_bar.set_progress(1.0)
        self._conv_file_bar.set_progress(1.0)
        total = result.total
        self._conv_overall_count_lbl.config(text=f"{result.completed} of {total} file{'s' if total != 1 else ''}")
        self._conv_file_name_lbl.config(text="Conversion complete" if not result.cancelled else "Cancelled")
        self._conv_stage_lbl.config(text="")
        self._log_write("")
        self._log_write(result.status_text)

        # Populate Results screen
        try:
            self._populate_results(result)
        except Exception as e:
            self._log_write(f"Error populating results: {e}")
        self._show("Results")

    def _populate_results(self, result: "_converter_mod.BatchResult") -> None:
        self._last_batch_result = result
        t = self._t
        bc = result.batch_confidence

        # Status banner
        self._results_status_lbl.config(text=result.status_text)
        if result.failed > 0:
            self._results_status_frame.config(highlightbackground=t.get("warn", t["border"]))
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
            menu.add_separator()
        remove_label = "Remove File" if len(sel) == 1 else f"Remove {len(sel)} Files"
        menu.add_command(label=remove_label, command=self._remove_selected_files)
        menu.tk_popup(event.x_root, event.y_root)

    def _remove_selected_files(self):
        indices = sorted(self._file_listbox.curselection(), reverse=True)
        for idx in indices:
            path = self._selected_files.pop(idx)
            self._file_aliases.pop(path, None)
        self._update_file_list()

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

        self._watch_ctrl_row.config(bg=t["content_bg"])
        self._watch_status_lbl.config(bg=t["content_bg"])
        if not (self._watcher and self._watcher.is_running):
            self._watch_status_lbl.config(fg=t["text_secondary"])
        self._watch_counts_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._watch_log_section_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._watch_log_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._watch_log.config(bg=t["bg"], fg=t["text"], insertbackground=t["text"])

        self._watch_btn_row.config(bg=t["content_bg"])

        # ── Conversion-specific widgets ───────────────────────
        self._conv_overall_row.config(bg=t["content_bg"])
        self._conv_overall_lbl.config(bg=t["content_bg"], fg=t["text"])
        self._conv_overall_count_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

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
    def _scroll_units(event) -> int:
        """Normalize mousewheel delta to scroll units across platforms."""
        import sys as _sys
        if event.delta:
            if _sys.platform == "darwin":
                return -event.delta
            return -1 * (event.delta // 120)
        return 0

    # ── Cleanup ──────────────────────────────────────────────

    def _on_close(self):
        if self._active_job and self._active_job.is_running():
            self._active_job.cancel()
            thread = getattr(self._active_job, '_thread', None)
            if thread and thread.is_alive():
                thread.join(timeout=1.0)
        if self._watcher and self._watcher.is_running:
            self._watcher.stop()
        self.root.destroy()

    # ── Run ──────────────────────────────────────────────────

    def run(self):
        # Apply title bar theme after the event loop starts.
        # The window must be fully mapped before DWM will accept the attribute.
        self.root.after(100, lambda: self._set_titlebar_dark(self._dark))
        self.root.mainloop()
