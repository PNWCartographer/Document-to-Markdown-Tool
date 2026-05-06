import os
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox, simpledialog
from . import theme as themes
from .tooltip import Tooltip
import config.settings as _cfg_mod
import engine.converter as _converter_mod

SCREENS = ["Home", "Settings", "Conversion", "Results"]

ICONS = {
    "Home":       "⌂",
    "Settings":   "⚙",
    "Conversion": "▶",
    "Results":    "✓",
}

_SUPPORTED_EXTS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv",
                   ".png", ".jpg", ".jpeg", ".tiff", ".bmp"}

_FILETYPES = [
    ("Supported files",  "*.pdf *.docx *.doc *.xlsx *.xls *.csv *.png *.jpg *.jpeg *.tiff *.bmp"),
    ("PDF files",        "*.pdf"),
    ("Word documents",   "*.docx *.doc"),
    ("Excel files",      "*.xlsx *.xls"),
    ("CSV files",        "*.csv"),
    ("Image files",      "*.png *.jpg *.jpeg *.tiff *.bmp"),
    ("All files",        "*.*"),
]

_FONT_TITLE    = ("Segoe UI", 13, "bold")
_FONT_HEADING  = ("Segoe UI", 22, "bold")
_FONT_BODY     = ("Segoe UI", 13)
_FONT_NAV      = ("Segoe UI", 12)
_FONT_NAV_ACT  = ("Segoe UI", 12, "bold")
_FONT_SMALL    = ("Segoe UI", 11)
_FONT_BTN      = ("Segoe UI", 13, "bold")
_FONT_SECTION  = ("Segoe UI", 10, "bold")

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
}


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Document to Markdown Converter")
        self.root.geometry("960x640")
        self.root.minsize(720, 500)

        self._dark = False
        self._t = themes.LIGHT
        self._nav_btns: dict[str, tk.Button] = {}
        self._frames:   dict[str, tk.Frame]  = {}
        self._current   = "Home"

        # Home screen state
        self._selected_files: list[str] = []
        self._file_aliases:   dict[str, str] = {}   # path → custom output name
        self._output_path: str = ""

        # Settings state
        self._cfg = _cfg_mod.load()
        self._setting_vars:        dict = {}
        self._settings_section_hdrs: list[tk.Label]  = []
        self._settings_dividers:     list[tk.Frame]  = []
        self._settings_info_labels:  list[tk.Label]  = []
        self._settings_name_labels:  list[tk.Label]  = []
        self._settings_checkboxes:   list[tk.Widget] = []
        self._settings_dropdowns:    list[tk.Widget] = []

        # Engine state
        self._active_job: "Optional[_converter_mod.ConversionJob]" = None
        self._last_output_root: str = ""

        self._build_layout()
        self._apply_theme()
        self._show("Home")

    # ── Layout ──────────────────────────────────────────────

    def _build_layout(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=0)  # sidebar
        self.root.grid_columnconfigure(1, weight=0)  # 1px border
        self.root.grid_columnconfigure(2, weight=1)  # content

        # Use clam so ttk scrollbar colors are respected on Windows
        self._ttk_style = ttk.Style()
        self._ttk_style.theme_use('clam')
        self._ttk_style.configure('App.Vertical.TScrollbar',
            relief='flat', borderwidth=0)

        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self):
        self._sidebar = tk.Frame(self.root, width=196)
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

        self._btn_theme = tk.Button(
            self._sidebar,
            text="  ☀   Light Mode",
            font=_FONT_SMALL,
            anchor="w",
            bd=0,
            relief="flat",
            padx=8,
            pady=9,
            cursor="hand2",
            command=self._toggle_theme,
        )
        self._btn_theme.grid(row=11, column=0, sticky="ew", padx=8, pady=(0, 10))

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

    def _placeholder(self, parent, text: str, row: int, height: int = 120):
        box = tk.Frame(parent, height=height, highlightthickness=1)
        box.grid(row=row, column=0, sticky="ew", padx=32, pady=6)
        box.grid_propagate(False)
        box.grid_rowconfigure(0, weight=1)
        box.grid_columnconfigure(0, weight=1)
        lbl = tk.Label(box, text=text, font=_FONT_SMALL, anchor="center")
        lbl.grid(row=0, column=0, sticky="nsew")
        return box, lbl

    def _build_home(self):
        f = self._new_screen("Home")
        # rows: 0=title, 1=subtitle, 2=toolbar, 3=file list, 4=count, 5=output, 6=start
        f.grid_rowconfigure(3, weight=1)

        self._heading(f, "Home", "Select files or a folder and choose an output location.")

        # ── Toolbar ─────────────────────────────────────────
        self._home_toolbar = tk.Frame(f)
        self._home_toolbar.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 4))
        self._home_toolbar.grid_columnconfigure(3, weight=1)  # spacer col

        self._btn_add_files = tk.Button(
            self._home_toolbar,
            text="+ Add Files",
            font=_FONT_SMALL,
            bd=0, relief="flat",
            highlightthickness=1,
            padx=12, pady=5,
            cursor="hand2",
            command=self._pick_files,
        )
        self._btn_add_files.grid(row=0, column=0, padx=(0, 6))

        self._btn_add_folder = tk.Button(
            self._home_toolbar,
            text="+ Add Folder",
            font=_FONT_SMALL,
            bd=0, relief="flat",
            highlightthickness=1,
            padx=12, pady=5,
            cursor="hand2",
            command=self._pick_folder_input,
        )
        self._btn_add_folder.grid(row=0, column=1, padx=(0, 6))

        self._btn_rename = tk.Button(
            self._home_toolbar,
            text="Rename…",
            font=_FONT_SMALL,
            bd=0, relief="flat",
            highlightthickness=1,
            padx=12, pady=5,
            cursor="hand2",
            state="disabled",
            command=self._rename_selected_file,
        )
        self._btn_rename.grid(row=0, column=2, padx=(0, 6))

        # spacer at column 3

        self._btn_clear = tk.Button(
            self._home_toolbar,
            text="Clear All",
            font=_FONT_SMALL,
            bd=0, relief="flat",
            highlightthickness=1,
            padx=12, pady=5,
            cursor="hand2",
            command=self._clear_files,
        )
        self._btn_clear.grid(row=0, column=4)

        # ── File list ────────────────────────────────────────
        self._file_list_frame = tk.Frame(f, highlightthickness=1)
        self._file_list_frame.grid(row=3, column=0, sticky="nsew", padx=32, pady=(0, 2))
        self._file_list_frame.grid_rowconfigure(0, weight=1)
        self._file_list_frame.grid_columnconfigure(0, weight=1)
        self._file_list_frame.grid_propagate(True)

        # Empty state label (shown when no files are selected)
        self._lbl_empty = tk.Label(
            self._file_list_frame,
            text="No files selected.\nUse '+ Add Files' or '+ Add Folder' to get started.",
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
        self._file_scrollbar = ttk.Scrollbar(
            self._file_list_frame,
            orient="vertical",
            command=self._file_listbox.yview,
            style='App.Vertical.TScrollbar',
        )
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

        self._btn_browse = tk.Button(
            self._home_out_row,
            text="Browse…",
            font=_FONT_SMALL,
            bd=0, relief="flat",
            highlightthickness=1,
            padx=12, pady=5,
            cursor="hand2",
            command=self._pick_output_folder,
        )
        self._btn_browse.grid(row=0, column=1)

        # ── Start button ─────────────────────────────────────
        self._btn_start = tk.Button(
            f,
            text="Start Conversion",
            font=_FONT_BTN,
            padx=24,
            pady=10,
            bd=0,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self._on_start,
        )
        self._btn_start.grid(row=6, column=0, sticky="w", padx=32, pady=(0, 28))

    def _build_settings(self):
        f = self._new_screen("Settings")
        f.grid_rowconfigure(2, weight=1)

        self._heading(
            f, "Settings",
            "Configure conversion mode, OCR language, image handling, and output options.",
        )

        # ── Build tk.Vars from loaded config ─────────────────
        self._setting_vars = {
            "conversion_mode":       tk.StringVar(value=self._cfg["conversion_mode"]),
            "preserve_images":       tk.BooleanVar(value=self._cfg["preserve_images"]),
            "preserve_page_numbers": tk.BooleanVar(value=self._cfg["preserve_page_numbers"]),
            "rebuild_toc":           tk.BooleanVar(value=self._cfg["rebuild_toc"]),
            "ocr_language":          tk.StringVar(value=self._cfg["ocr_language"]),
            "overwrite_existing":    tk.BooleanVar(value=self._cfg["overwrite_existing"]),
            "output_subfolder":      tk.BooleanVar(value=self._cfg["output_subfolder"]),
            "low_confidence_action": tk.StringVar(value=self._cfg["low_confidence_action"]),
        }
        for var in self._setting_vars.values():
            var.trace_add("write", self._on_setting_changed)

        # ── Content frame ─────────────────────────────────────
        self._settings_content = tk.Frame(f)
        self._settings_content.grid(row=2, column=0, sticky="nsew", padx=32, pady=(0, 24))
        self._settings_content.grid_columnconfigure(1, weight=1)

        row = 0

        # Section: Conversion
        row = self._settings_add_section(self._settings_content, "Conversion", row, first=True)
        row = self._settings_add_dropdown(
            self._settings_content, "conversion_mode", "Conversion Mode",
            ["Standard", "OCR", "Auto-detect"],
            _TIPS["conversion_mode"], row,
        )

        # Section: Content Handling
        row = self._settings_add_section(self._settings_content, "Content Handling", row)
        row = self._settings_add_checkbox(
            self._settings_content, "preserve_images", "Preserve Images",
            _TIPS["preserve_images"], row,
        )
        row = self._settings_add_checkbox(
            self._settings_content, "preserve_page_numbers", "Preserve Page Numbers",
            _TIPS["preserve_page_numbers"], row,
        )
        row = self._settings_add_checkbox(
            self._settings_content, "rebuild_toc", "Rebuild Table of Contents",
            _TIPS["rebuild_toc"], row,
        )

        # Section: OCR
        row = self._settings_add_section(self._settings_content, "OCR", row)
        row = self._settings_add_dropdown(
            self._settings_content, "ocr_language", "OCR Language",
            ["English", "French", "German", "Spanish", "Italian", "Portuguese",
             "Dutch", "Auto-detect"],
            _TIPS["ocr_language"], row,
        )

        # Section: Output
        row = self._settings_add_section(self._settings_content, "Output", row)
        row = self._settings_add_checkbox(
            self._settings_content, "overwrite_existing", "Overwrite Existing Files",
            _TIPS["overwrite_existing"], row,
        )
        row = self._settings_add_checkbox(
            self._settings_content, "output_subfolder", "Output Subfolder Structure",
            _TIPS["output_subfolder"], row,
        )
        row = self._settings_add_dropdown(
            self._settings_content, "low_confidence_action", "Handle Low Confidence Results",
            ["Ask me", "Keep and flag", "Skip"],
            _TIPS["low_confidence_action"], row,
        )

    def _settings_add_section(self, parent, title: str, row: int, first=False) -> int:
        top_pad = 8 if first else 18
        lbl = tk.Label(parent, text=title.upper(), font=_FONT_SECTION, anchor="w")
        lbl.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(top_pad, 2))
        sep = tk.Frame(parent, height=1)
        sep.grid(row=row + 1, column=0, columnspan=3, sticky="ew", pady=(0, 2))
        self._settings_section_hdrs.append(lbl)
        self._settings_dividers.append(sep)
        return row + 2

    def _settings_add_checkbox(self, parent, key, label, tip, row) -> int:
        info = tk.Label(parent, text="ⓘ", font=("Segoe UI", 12), cursor="question_arrow")
        info.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 4))
        Tooltip(info, tip, lambda: self._t)

        lbl = tk.Label(parent, text=label, font=_FONT_SMALL, anchor="w")
        lbl.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=4)

        var = self._setting_vars[key]
        cb = tk.Checkbutton(parent, variable=var, bd=0, highlightthickness=0, cursor="hand2")
        cb.grid(row=row, column=2, sticky="e", pady=4)

        self._settings_info_labels.append(info)
        self._settings_name_labels.append(lbl)
        self._settings_checkboxes.append(cb)
        return row + 1

    def _settings_add_dropdown(self, parent, key, label, options, tip, row) -> int:
        info = tk.Label(parent, text="ⓘ", font=("Segoe UI", 12), cursor="question_arrow")
        info.grid(row=row, column=0, sticky="w", pady=4, padx=(0, 4))
        Tooltip(info, tip, lambda: self._t)

        lbl = tk.Label(parent, text=label, font=_FONT_SMALL, anchor="w")
        lbl.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=4)

        var = self._setting_vars[key]
        menu = tk.OptionMenu(parent, var, *options)
        menu.config(bd=0, relief="flat", highlightthickness=1, pady=3, padx=8, cursor="hand2")
        menu.grid(row=row, column=2, sticky="e", pady=3)

        self._settings_info_labels.append(info)
        self._settings_name_labels.append(lbl)
        self._settings_dropdowns.append(menu)
        return row + 1

    def _on_setting_changed(self, *_):
        for key, var in self._setting_vars.items():
            self._cfg[key] = var.get()
        _cfg_mod.save(self._cfg)

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

        self._conv_overall_bar_outer = tk.Frame(f, height=10, highlightthickness=1)
        self._conv_overall_bar_outer.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 16))
        self._conv_overall_bar_outer.grid_propagate(False)

        self._conv_overall_bar_inner = tk.Frame(self._conv_overall_bar_outer, height=10)
        self._conv_overall_bar_inner.place(x=0, y=0, relheight=1.0, relwidth=0.0)

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
        self._conv_file_bar_outer = tk.Frame(f, height=6, highlightthickness=1)
        self._conv_file_bar_outer.grid(row=5, column=0, sticky="ew", padx=32, pady=(0, 16))
        self._conv_file_bar_outer.grid_propagate(False)

        self._conv_file_bar_inner = tk.Frame(self._conv_file_bar_outer, height=6)
        self._conv_file_bar_inner.place(x=0, y=0, relheight=1.0, relwidth=0.0)

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
        self._conv_log_sb = ttk.Scrollbar(
            self._conv_log_frame, orient="vertical", command=self._conv_log.yview,
            style='App.Vertical.TScrollbar')
        self._conv_log.config(yscrollcommand=self._conv_log_sb.set)
        self._conv_log.grid(row=0, column=0, sticky="nsew")
        self._conv_log_sb.grid(row=0, column=1, sticky="ns")

        # ── Cancel button ────────────────────────────────────
        self._btn_cancel = tk.Button(
            f,
            text="Cancel",
            font=_FONT_BTN,
            padx=24, pady=10,
            bd=0, relief="flat",
            highlightthickness=1,
            cursor="hand2",
            command=self._on_cancel_conversion,
        )
        self._btn_cancel.grid(row=8, column=0, sticky="w", padx=32, pady=(0, 28))

    def _build_results(self):
        f = self._new_screen("Results")
        f.grid_rowconfigure(8, weight=1)

        self._heading(
            f, "Results",
            "View the output location, confidence report summary, warnings, and open the output folder.",
        )

        # ── Status banner ────────────────────────────────────
        self._results_status_frame = tk.Frame(f, highlightthickness=1)
        self._results_status_frame.grid(row=2, column=0, sticky="ew", padx=32, pady=(0, 16))
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
        self._results_out_row = tk.Frame(f)
        self._results_out_row.grid(row=3, column=0, sticky="ew", padx=32, pady=(0, 16))
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

        self._btn_open_folder = tk.Button(
            self._results_out_row,
            text="Open Folder",
            font=_FONT_SMALL,
            bd=0, relief="flat",
            highlightthickness=1,
            padx=12, pady=5,
            cursor="hand2",
            command=self._on_open_output_folder,
        )
        self._btn_open_folder.grid(row=0, column=1)

        # ── Confidence summary ───────────────────────────────
        self._results_conf_section_lbl = tk.Label(
            f, text="CONFIDENCE SUMMARY", font=_FONT_SECTION, anchor="w")
        self._results_conf_section_lbl.grid(
            row=4, column=0, sticky="ew", padx=32, pady=(0, 2))

        self._results_conf_div = tk.Frame(f, height=1)
        self._results_conf_div.grid(row=5, column=0, sticky="ew", padx=32, pady=(0, 6))

        self._results_conf_frame = tk.Frame(f)
        self._results_conf_frame.grid(row=6, column=0, sticky="ew", padx=32, pady=(0, 16))
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

        # ── Warnings ─────────────────────────────────────────
        self._results_warn_lbl = tk.Label(f, text="Warnings", font=_FONT_SMALL, anchor="w")
        self._results_warn_lbl.grid(row=7, column=0, sticky="w", padx=32, pady=(0, 4))

        self._results_warn_frame = tk.Frame(f, highlightthickness=1)
        self._results_warn_frame.grid(row=8, column=0, sticky="nsew", padx=32, pady=(0, 8))
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
        self._results_warn_sb = ttk.Scrollbar(
            self._results_warn_frame, orient="vertical",
            command=self._results_warn_text.yview,
            style='App.Vertical.TScrollbar',
        )
        self._results_warn_text.config(yscrollcommand=self._results_warn_sb.set)
        self._results_warn_text.grid(row=0, column=0, sticky="nsew")
        self._results_warn_sb.grid(row=0, column=1, sticky="ns")

        # ── Button row ───────────────────────────────────────
        self._results_btn_row = tk.Frame(f)
        self._results_btn_row.grid(row=9, column=0, sticky="ew", padx=32, pady=(0, 28))

        self._btn_open_output = tk.Button(
            self._results_btn_row,
            text="Open Output Folder",
            font=_FONT_BTN,
            padx=24, pady=10,
            bd=0, relief="flat",
            cursor="hand2",
            command=self._on_open_output_folder,
        )
        self._btn_open_output.grid(row=0, column=0)

        self._btn_new_conv = tk.Button(
            self._results_btn_row,
            text="Start New Conversion",
            font=_FONT_BTN,
            padx=24, pady=10,
            bd=0, relief="flat",
            highlightthickness=1,
            cursor="hand2",
            command=lambda: self._show("Home"),
        )
        self._btn_new_conv.grid(row=0, column=1, padx=(12, 0))

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
        for entry in sorted(os.listdir(folder)):
            full = os.path.join(folder, entry)
            if os.path.isfile(full) and os.path.splitext(entry)[1].lower() in _SUPPORTED_EXTS:
                found.append(full)
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
        sb = tk.Scrollbar(list_frame, orient="vertical", command=lb.yview)
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

        tk.Button(btn_row, text="Cancel", command=dlg.destroy,
                  bg=t["sidebar_bg"], fg=t["text"],
                  activebackground=t["nav_hover_bg"], activeforeground=t["text"],
                  highlightthickness=1, highlightbackground=t["border"],
                  bd=0, relief="flat", padx=16, pady=7,
                  font=_FONT_SMALL, cursor="hand2").pack(side="right", padx=(8, 0))
        tk.Button(btn_row, text="Add Files", command=confirm,
                  bg=t["accent"], fg=t["text_on_accent"],
                  activebackground=t["accent_hover"], activeforeground=t["text_on_accent"],
                  bd=0, relief="flat", padx=16, pady=7,
                  font=_FONT_SMALL, cursor="hand2").pack(side="right")

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
        self._btn_start.config(state="normal" if ready else "disabled")

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
        subprocess.Popen(f'explorer "{path}"')

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
        self._conv_overall_bar_inner.place(relwidth=0.0)
        self._conv_file_bar_inner.place(relwidth=0.0)
        label = "1 file" if n == 1 else f"{n} files"
        self._conv_overall_count_lbl.config(text=f"0 of {n} file{'s' if n != 1 else ''}")
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
        self._reset_conversion_screen()
        self._show("Conversion")
        self._last_output_root = self._output_path

        self._active_job = _converter_mod.ConversionJob(
            files=self._selected_files,
            aliases=self._file_aliases,
            output_root=self._output_path,
            cfg=self._cfg,
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
        self._conv_file_bar_inner.place(relwidth=max(0.0, min(1.0, fraction)))

    def _set_overall_progress(self, fraction: float) -> None:
        self._conv_overall_bar_inner.place(relwidth=max(0.0, min(1.0, fraction)))

    def _on_file_start(self, filename: str, idx: int, total: int) -> None:
        self._conv_file_name_lbl.config(text=filename)
        self._conv_overall_count_lbl.config(text=f"{idx} of {total} file{'s' if total != 1 else ''}")

    def _on_stage_update(self, stage: str) -> None:
        self._conv_stage_lbl.config(text=stage)

    def _on_conversion_done(self, result: "_converter_mod.BatchResult") -> None:
        # Final bar states
        self._conv_overall_bar_inner.place(relwidth=1.0)
        self._conv_file_bar_inner.place(relwidth=1.0)
        total = result.total
        self._conv_overall_count_lbl.config(text=f"{result.completed} of {total} file{'s' if total != 1 else ''}")
        self._conv_file_name_lbl.config(text="Conversion complete" if not result.cancelled else "Cancelled")
        self._conv_stage_lbl.config(text="")
        self._log_write("")
        self._log_write(result.status_text)

        # Populate Results screen
        self._populate_results(result)
        self._show("Results")

    def _populate_results(self, result: "_converter_mod.BatchResult") -> None:
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
        self._btn_rename.config(state="normal" if len(sel) == 1 else "disabled")

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
        self._dark = not self._dark
        self._t = themes.DARK if self._dark else themes.LIGHT
        self._apply_theme()

    def _apply_theme(self):
        t = self._t

        self.root.config(bg=t["bg"])
        self._sidebar.config(bg=t["sidebar_bg"])
        self._border_line.config(bg=t["border"])
        self._content.config(bg=t["content_bg"])
        self._div_top.config(bg=t["border"])
        self._div_bot.config(bg=t["border"])
        self._sidebar_spacer.config(bg=t["sidebar_bg"])
        self._lbl_title.config(bg=t["sidebar_bg"], fg=t["text"])

        self._btn_theme.config(
            bg=t["sidebar_bg"],
            fg=t["text_secondary"],
            activebackground=t["nav_hover_bg"],
            activeforeground=t["text_secondary"],
            text="  ☽   Dark Mode" if self._dark else "  ☀   Light Mode",
        )

        # Screen frames and their heading labels
        for frame in self._frames.values():
            frame.config(bg=t["content_bg"])
            self._style_screen_labels(frame, t)

        # ── Home-specific widgets ────────────────────────────
        self._home_toolbar.config(bg=t["content_bg"])

        for btn in (self._btn_add_files, self._btn_add_folder, self._btn_clear, self._btn_browse):
            btn.config(
                bg=t["sidebar_bg"],
                fg=t["accent"],
                highlightbackground=t["border"],
                activebackground=t["nav_hover_bg"],
                activeforeground=t["accent"],
            )
        self._btn_rename.config(
            bg=t["sidebar_bg"],
            fg=t["accent"],
            disabledforeground=t["text_secondary"],
            highlightbackground=t["border"],
            activebackground=t["nav_hover_bg"],
            activeforeground=t["accent"],
        )

        self._file_list_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._file_listbox.config(
            bg=t["bg"],
            fg=t["text"],
            selectbackground=t["accent"],
            selectforeground=t["text_on_accent"],
        )
        self._ttk_style.configure('App.Vertical.TScrollbar',
            background=t["border"],
            troughcolor=t["bg"],
            arrowcolor=t["text_secondary"],
            bordercolor=t["bg"],
            darkcolor=t["border"],
            lightcolor=t["border"],
        )
        self._ttk_style.map('App.Vertical.TScrollbar',
            background=[('active', t["text_secondary"]), ('pressed', t["text"])],
        )
        self._lbl_empty.config(bg=t["bg"], fg=t["text_secondary"])
        self._lbl_file_count.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._home_out_row.config(bg=t["content_bg"])
        self._out_path_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._lbl_output_path.config(bg=t["bg"], fg=t["text_secondary"])

        # ── Results-specific widgets ──────────────────────────
        self._results_status_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._results_status_lbl.config(bg=t["bg"], fg=t["text_secondary"])

        self._results_out_row.config(bg=t["content_bg"])
        self._results_out_path_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._results_out_path_lbl.config(bg=t["bg"], fg=t["text_secondary"])
        self._btn_open_folder.config(
            bg=t["sidebar_bg"],
            fg=t["accent"],
            highlightbackground=t["border"],
            activebackground=t["nav_hover_bg"],
            activeforeground=t["accent"],
        )

        self._results_conf_section_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._results_conf_div.config(bg=t["border"])
        self._results_conf_frame.config(bg=t["content_bg"])
        for lbl in self._results_conf_level_lbls:
            lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._results_warn_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._results_warn_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._results_warn_text.config(
            bg=t["bg"], fg=t["text"], insertbackground=t["text"])

        self._results_btn_row.config(bg=t["content_bg"])
        self._btn_open_output.config(
            bg=t["accent"],
            fg=t["text_on_accent"],
            activebackground=t["accent_hover"],
            activeforeground=t["text_on_accent"],
            disabledforeground=t["text_on_accent"],
        )
        self._btn_new_conv.config(
            bg=t["sidebar_bg"],
            fg=t["accent"],
            highlightbackground=t["border"],
            activebackground=t["nav_hover_bg"],
            activeforeground=t["accent"],
        )

        # ── Conversion-specific widgets ───────────────────────
        self._conv_overall_row.config(bg=t["content_bg"])
        self._conv_overall_lbl.config(bg=t["content_bg"], fg=t["text"])
        self._conv_overall_count_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._conv_overall_bar_outer.config(bg=t["bg"], highlightbackground=t["border"])
        self._conv_overall_bar_inner.config(bg=t["accent"])

        self._conv_file_row.config(bg=t["content_bg"])
        self._conv_file_name_lbl.config(bg=t["content_bg"], fg=t["text"])
        self._conv_stage_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        self._conv_file_bar_outer.config(bg=t["bg"], highlightbackground=t["border"])
        self._conv_file_bar_inner.config(bg=t["accent"])

        self._conv_log_lbl.config(bg=t["content_bg"], fg=t["text_secondary"])
        self._conv_log_frame.config(bg=t["bg"], highlightbackground=t["border"])
        self._conv_log.config(
            bg=t["bg"], fg=t["text"],
            insertbackground=t["text"],
        )

        self._btn_cancel.config(
            bg=t["sidebar_bg"],
            fg=t["accent"],
            highlightbackground=t["border"],
            activebackground=t["nav_hover_bg"],
            activeforeground=t["accent"],
        )

        # Start button
        self._btn_start.config(
            bg=t["accent"],
            fg=t["text_on_accent"],
            activebackground=t["accent_hover"],
            activeforeground=t["text_on_accent"],
            disabledforeground=t["text_on_accent"],
        )

        # ── Settings-specific widgets ────────────────────────
        # _style_screen_labels already walked the settings content frame and set
        # all Labels to content_bg/text and all Frames to content_bg. Override
        # the widgets that need non-default colors.
        self._settings_content.config(bg=t["content_bg"])

        for lbl in self._settings_section_hdrs:
            lbl.config(bg=t["content_bg"], fg=t["text_secondary"])

        for sep in self._settings_dividers:
            sep.config(bg=t["border"])

        for lbl in self._settings_info_labels:
            lbl.config(bg=t["content_bg"], fg=t["accent"])

        for cb in self._settings_checkboxes:
            cb.config(
                bg=t["content_bg"],
                fg=t["text"],
                activebackground=t["content_bg"],
                activeforeground=t["text"],
                selectcolor=t["bg"],
            )

        for menu in self._settings_dropdowns:
            menu.config(
                bg=t["sidebar_bg"],
                fg=t["text"],
                activebackground=t["nav_hover_bg"],
                activeforeground=t["text"],
                highlightbackground=t["border"],
            )
            menu["menu"].config(
                bg=t["sidebar_bg"],
                fg=t["text"],
                activebackground=t["accent"],
                activeforeground=t["text_on_accent"],
            )

        self._refresh_nav()

    def _style_screen_labels(self, widget, t):
        cls = widget.winfo_class()
        if cls == "Label":
            widget.config(bg=t["content_bg"], fg=t["text"])
        elif cls == "Frame":
            widget.config(bg=t["content_bg"])
            for child in widget.winfo_children():
                self._style_screen_labels(child, t)

    # ── Run ──────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
