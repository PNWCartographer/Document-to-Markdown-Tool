"""
Document to Markdown Converter — one-shot setup script.

Run once after cloning / downloading the project:
    python setup.py

What this does:
  1. Checks Python version (3.10+ required)
  2. Installs all pip dependencies from requirements.txt
  3. Downloads and silently installs Tesseract OCR 5.4.0 (Windows, 64-bit)
  4. Verifies the installation and reports any issues

All processing stays local. No telemetry, no cloud uploads.
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import tempfile

MIN_PYTHON = (3, 10)
TESSERACT_VERSION = "5.4.0.20240606"
TESSERACT_URL = (
    f"https://github.com/UB-Mannheim/tesseract/releases/download/"
    f"v{TESSERACT_VERSION}/tesseract-ocr-w64-setup-{TESSERACT_VERSION}.exe"
)
TESSERACT_DEFAULT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def banner(text: str) -> None:
    print(f"\n{'-' * 60}")
    print(f"  {text}")
    print(f"{'-' * 60}")


def check_python() -> None:
    banner("Checking Python version")
    v = sys.version_info[:2]
    if v < MIN_PYTHON:
        print(f"  ERROR: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, found {v[0]}.{v[1]}")
        sys.exit(1)
    print(f"  Python {v[0]}.{v[1]} — OK")

    # Warn about Windows Store Python (known ML DLL issues)
    if "WindowsApps" in sys.executable or "PythonSoftwareFoundation" in sys.executable:
        print()
        print("  NOTE: You are using Windows Store Python.")
        print("  Most features work fine. If you encounter DLL errors with")
        print("  RapidOCR, install Python from https://python.org instead.")


def install_pip_packages() -> None:
    banner("Installing Python dependencies")
    req = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.isfile(req):
        print("  ERROR: requirements.txt not found.")
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req],
        check=False,
    )
    if result.returncode != 0:
        print("\n  WARNING: Some packages failed to install.")
        print("  The tool may still work — check the output above for details.")
    else:
        print("\n  All packages installed successfully.")


def install_tesseract() -> None:
    banner("Installing Tesseract OCR")

    # Already installed?
    if shutil.which("tesseract") or os.path.isfile(TESSERACT_DEFAULT_PATH):
        path = shutil.which("tesseract") or TESSERACT_DEFAULT_PATH
        print(f"  Tesseract already installed at: {path}")
        _print_tesseract_version(path)
        return

    if sys.platform != "win32":
        print("  Non-Windows platform detected.")
        print("  Install Tesseract via your package manager:")
        print("    Ubuntu/Debian : sudo apt install tesseract-ocr")
        print("    macOS         : brew install tesseract")
        return

    print(f"  Downloading Tesseract {TESSERACT_VERSION}...")
    installer = os.path.join(tempfile.gettempdir(), "tesseract-setup.exe")

    try:
        def _progress(blocks, block_size, total):
            done = min(blocks * block_size, total)
            pct = int(done / total * 40) if total > 0 else 0
            bar = "█" * pct + "░" * (40 - pct)
            mb_done = done // 1024 // 1024
            mb_total = total // 1024 // 1024
            print(f"\r  [{bar}] {mb_done}/{mb_total} MB", end="", flush=True)

        urllib.request.urlretrieve(TESSERACT_URL, installer, reporthook=_progress)
        print()
    except Exception as e:
        print(f"\n  ERROR downloading Tesseract: {e}")
        print(f"  Download manually from: {TESSERACT_URL}")
        print(f"  Then re-run this script.")
        return

    print("  Running installer (this may trigger a UAC prompt)...")
    result = subprocess.run([installer, "/S"], check=False)
    if result.returncode == 0 and os.path.isfile(TESSERACT_DEFAULT_PATH):
        print(f"  Tesseract installed at: {TESSERACT_DEFAULT_PATH}")
        _print_tesseract_version(TESSERACT_DEFAULT_PATH)
    else:
        print(f"  Installer exited with code {result.returncode}.")
        print("  If Tesseract is not found, run the installer manually.")


def _print_tesseract_version(binary: str) -> None:
    try:
        out = subprocess.check_output([binary, "--version"], stderr=subprocess.STDOUT, text=True)
        version_line = out.splitlines()[0] if out else "(unknown)"
        print(f"  Version: {version_line}")
    except Exception:
        pass


def verify() -> None:
    banner("Verifying installation")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

    checks = [
        ("docling",        "import docling"),
        ("pymupdf",        "import fitz"),
        ("pymupdf4llm",    "import pymupdf4llm"),
        ("pdfplumber",     "import pdfplumber"),
        ("camelot",        "import camelot"),
        ("python-docx",    "import docx"),
        ("mammoth",        "import mammoth"),
        ("openpyxl",       "import openpyxl"),
        ("xlrd",           "import xlrd"),
        ("pandas",         "import pandas"),
        ("Pillow",         "import PIL"),
        ("opencv-python",  "import cv2"),
        ("rapidocr",       "import rapidocr_onnxruntime"),
        ("pytesseract",    "import pytesseract"),
        ("psutil",         "import psutil"),
        ("ebooklib",       "import ebooklib"),
        ("beautifulsoup4", "import bs4"),
        ("markdownify",    "import markdownify"),
        ("striprtf",       "import striprtf"),
        ("ezdxf",          "import ezdxf"),
        ("watchdog",       "import watchdog"),
        ("ocrmypdf",       "import ocrmypdf"),
        ("python-pptx",    "import pptx"),
        ("fast-langdetect", "import fast_langdetect"),
        ("argostranslate", "import argostranslate"),
        ("nvidia-ml-py",   "import pynvml"),
        ("pyspellchecker", "import spellchecker"),
        ("tkinterdnd2",    "import tkinterdnd2"),
        ("markdown",       "import markdown"),
    ]

    all_ok = True
    for name, stmt in checks:
        try:
            exec(stmt)
            print(f"  {name:<16} OK")
        except Exception as e:
            print(f"  {name:<16} FAILED — {e}")
            all_ok = False

    print()
    print("  OCR engines:")
    try:
        from engine.ocr_engine import rapidocr_available, tesseract_available
        ra = rapidocr_available()
        ta = tesseract_available()
        print(f"    RapidOCR   : {'OK  active' if ra else 'FAIL unavailable'}")
        print(f"    Tesseract  : {'OK  active' if ta else 'FAIL unavailable'}")
        if not ra and not ta:
            print("    WARNING: No OCR engine active — images/scanned PDFs will skip text extraction.")
    except Exception as e:
        print(f"    Could not check OCR engines: {e}")

    print()
    print("  System detection:")
    try:
        from engine.system_info import detect_system, format_summary
        info = detect_system()
        for line in format_summary(info).split("\n"):
            print(f"    {line}")
    except Exception as e:
        print(f"    Could not detect system info: {e}")

    print()
    if all_ok:
        print("  Setup complete. Run the tool with:")
        print("    python app/main.py")
        print("    — or double-click Launch.pyw")
    else:
        print("  Setup finished with warnings. Check failed items above.")


if __name__ == "__main__":
    print("Document to Markdown Converter — Setup")
    check_python()
    install_pip_packages()
    install_tesseract()
    verify()
