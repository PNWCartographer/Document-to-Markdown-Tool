# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Markwell by Darksquare.

Usage:
    pyinstaller installer/markwell.spec

Produces a one-folder distribution at:
    dist/Markwell/Markwell.exe

That folder is consumed by the InnoSetup script (markwell.iss)
to produce the final installer.
"""

import os
import sys
import importlib
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
)

# ── Paths ───────────────────────────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
APP_DIR = os.path.join(PROJECT_ROOT, "app")
ICON_FILE = os.path.join(PROJECT_ROOT, "assets", "app_icon.ico")

# ── Hidden imports ──────────────────────────────────────────────
# Modules that PyInstaller cannot detect via static analysis.
hidden_imports = [
    # ── App subpackages ──
    *collect_submodules("gui"),
    *collect_submodules("engine"),
    *collect_submodules("config"),

    # ── Core conversion libraries ──
    "fitz",
    "pymupdf4llm",
    "mammoth",
    "docx",
    "openpyxl",
    "xlrd",
    "pandas",
    "pdfplumber",

    # ── Optional heavy engines (graceful if missing) ──
    "docling",
    "docling.document_converter",
    "docling.datamodel",
    "rapidocr_onnxruntime",
    "onnxruntime",

    # ── OCR & image ──
    "pytesseract",
    "PIL",
    "PIL.Image",
    "cv2",

    # ── Searchable PDF ──
    "ocrmypdf",
    "pikepdf",
    "img2pdf",
    "pdfminer",
    "pdfminer.high_level",
    "pluggy",
    "reportlab",

    # ── Table extraction ──
    "camelot",

    # ── Format-specific ──
    "pptx",
    "ebooklib",
    "ebooklib.epub",
    "bs4",
    "markdownify",
    "striprtf",
    "ezdxf",

    # ── Preview tools ──
    "spellchecker",
    "markdown",

    # ── Language tools ──
    "fast_langdetect",
    "argostranslate",
    "argostranslate.translate",
    "argostranslate.package",

    # ── System detection ──
    "psutil",
    "pynvml",

    # ── File watching ──
    "watchdog",
    "watchdog.observers",
    "watchdog.events",

    # ── DnD (optional) ──
    "tkinterdnd2",

    # ── stdlib that PyInstaller sometimes misses ──
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "tkinter.font",
    "json",
    "csv",
    "re",
    "threading",
    "concurrent.futures",
    "dataclasses",
    "email.mime.text",
]

# ── Data files ──────────────────────────────────────────────────
# Collect package data that must ship at runtime (models, configs, etc.)
datas = []

# Bundle project documentation and license files
datas += [
    (os.path.join(PROJECT_ROOT, "README.md"), "."),
    (os.path.join(PROJECT_ROOT, "LICENSE"), "."),
    (os.path.join(PROJECT_ROOT, "THIRD_PARTY_LICENSES"), "."),
    (os.path.join(PROJECT_ROOT, "assets", "app_icon.ico"), "assets"),
]

# Bundled vendor binaries — Tesseract OCR (Apache 2.0), staged into
# installer/vendor/ by installer/stage_vendor.py. Lands in the dist as
# vendor/tesseract/ so app/engine/vendor.py resolves it at runtime.
# Ghostscript is intentionally NOT bundled (AGPL) — users install it themselves.
_vendor_tess = os.path.join(PROJECT_ROOT, "installer", "vendor", "tesseract")
if os.path.isdir(_vendor_tess):
    for _root, _dirs, _files in os.walk(_vendor_tess):
        for _fn in _files:
            _full = os.path.join(_root, _fn)
            _rel = os.path.relpath(os.path.dirname(_full), _vendor_tess)
            if _rel == ".":
                _dest = os.path.join("vendor", "tesseract")
            else:
                _dest = os.path.join("vendor", "tesseract", _rel)
            datas.append((_full, _dest))
    print(f"[spec] Bundling vendored Tesseract from {_vendor_tess}")
else:
    print("[spec] WARNING: installer/vendor/tesseract not found — "
          "run 'python installer/stage_vendor.py' first to bundle Tesseract.")

# Collect data files from libraries that embed runtime assets
_data_packages = [
    "rapidocr_onnxruntime",
    "ezdxf",
    "pdfplumber",
    "ebooklib",
    "argostranslate",
    "fast_langdetect",
    "markdownify",
    "docling",
    "docling_core",
    "ocrmypdf",
    "spellchecker",
]
for pkg in _data_packages:
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass  # package not installed — skip

# ── Dynamic libraries ──────────────────────────────────────────
binaries = []
_bin_packages = ["onnxruntime", "cv2", "ezdxf", "pikepdf"]
for pkg in _bin_packages:
    try:
        binaries += collect_dynamic_libs(pkg)
    except Exception:
        pass

# ── Excludes ────────────────────────────────────────────────────
# Trim packages that are not needed at runtime to reduce bundle size.
excludes = [
    "matplotlib",
    "notebook",
    "jupyter",
    "IPython",
    "pytest",
    "sphinx",
    "pyinstaller",
    # NOTE: do NOT exclude setuptools / pip / wheel — PyInstaller's setuptools
    # hook aliases a vendored 'wheel' module, and excluding it aborts the build
    # with: ValueError: Target module "wheel" already imported as ExcludedModule.
    # scipy is intentionally left bundled because docling/torch may import it
    # at runtime; excluding it risks an ImportError in the frozen app.
]

# ── Analysis ────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(APP_DIR, "main.py")],
    pathex=[APP_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# ── PYZ (bytecode archive) ─────────────────────────────────────
pyz = PYZ(a.pure)

# ── EXE ─────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Markwell",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # windowed app — no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=ICON_FILE,
)

# ── COLLECT (one-folder distribution) ──────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Markwell",
)
