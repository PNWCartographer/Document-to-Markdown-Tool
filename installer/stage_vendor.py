"""
Stage vendored binaries into installer/vendor/ for bundling by PyInstaller.

Currently stages Tesseract OCR (Apache 2.0) only. Ghostscript is NOT staged
or shipped — it is AGPL-licensed, so users install it themselves and the app
guides them to the official download page when they first use Searchable PDF.

Run automatically by build_installer.bat before PyInstaller, or manually:
    python installer/stage_vendor.py

Copies the Tesseract binary, its runtime DLLs, and the requested language
data from an installed Tesseract into installer/vendor/tesseract/, trimming
documentation and unused files to keep the bundle small.
"""

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(HERE, "vendor")
TESS_DEST = os.path.join(VENDOR, "tesseract")

# Languages to bundle (traineddata basenames). Keep small by default;
# add more here if you want extra OCR languages in the shipped build.
LANGUAGES = ["eng", "osd"]

_TESS_SEARCH = [
    r"C:\Program Files\Tesseract-OCR",
    r"C:\Program Files (x86)\Tesseract-OCR",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "Tesseract-OCR"),
]


def find_tesseract_dir():
    """Locate an installed Tesseract directory, or None."""
    exe = shutil.which("tesseract")
    if exe and os.path.isfile(exe):
        return os.path.dirname(exe)
    for d in _TESS_SEARCH:
        if os.path.isfile(os.path.join(d, "tesseract.exe")):
            return d
    return None


def stage_tesseract():
    """Copy a trimmed Tesseract into installer/vendor/tesseract/."""
    src = find_tesseract_dir()
    if not src:
        print("  ERROR: Tesseract not found. Install it first (python setup.py).")
        return False

    print(f"  Source: {src}")
    if os.path.isdir(TESS_DEST):
        shutil.rmtree(TESS_DEST, ignore_errors=True)
    os.makedirs(TESS_DEST, exist_ok=True)

    # 1. tesseract.exe
    exe_src = os.path.join(src, "tesseract.exe")
    if not os.path.isfile(exe_src):
        print("  ERROR: tesseract.exe missing in source directory.")
        return False
    shutil.copy2(exe_src, os.path.join(TESS_DEST, "tesseract.exe"))

    # 2. runtime DLLs in the install root
    dll_count = 0
    for name in os.listdir(src):
        if name.lower().endswith(".dll"):
            shutil.copy2(os.path.join(src, name), os.path.join(TESS_DEST, name))
            dll_count += 1

    # 3. tessdata: only the requested languages + tiny config dirs
    src_td = os.path.join(src, "tessdata")
    dst_td = os.path.join(TESS_DEST, "tessdata")
    os.makedirs(dst_td, exist_ok=True)
    lang_count = 0
    for lang in LANGUAGES:
        f = os.path.join(src_td, f"{lang}.traineddata")
        if os.path.isfile(f):
            shutil.copy2(f, os.path.join(dst_td, f"{lang}.traineddata"))
            lang_count += 1
        else:
            print(f"  WARNING: language '{lang}' not found in tessdata — skipped")
    for sub in ("configs", "tessconfigs"):
        s = os.path.join(src_td, sub)
        if os.path.isdir(s):
            shutil.copytree(s, os.path.join(dst_td, sub), dirs_exist_ok=True)

    # 4. license/attribution alongside the binary (Apache 2.0)
    for lic_name in ("LICENSE", "LICENSE.txt", "COPYING"):
        lic = os.path.join(src, lic_name)
        if os.path.isfile(lic):
            shutil.copy2(lic, os.path.join(TESS_DEST, "TESSERACT_LICENSE.txt"))
            break

    size = sum(
        os.path.getsize(os.path.join(r, f))
        for r, _dirs, fs in os.walk(TESS_DEST) for f in fs
    )
    print(f"  Staged: tesseract.exe + {dll_count} DLLs + {lang_count} language(s)")
    print(f"  Size:   {size / 1024 / 1024:.1f} MB  ->  {TESS_DEST}")
    return True


def main():
    print("Staging vendored binaries (Tesseract only; Ghostscript is not shipped)...")
    os.makedirs(VENDOR, exist_ok=True)
    if not stage_tesseract():
        sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
