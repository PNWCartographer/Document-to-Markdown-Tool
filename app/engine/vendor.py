"""
Locates optional binaries bundled alongside the application.

When the app is frozen (PyInstaller one-folder build), bundled binaries
live under a ``vendor/`` folder next to the executable. In development
that folder does not exist, so these helpers return ``None`` and the
engines fall back to system-installed copies (PATH / common locations).

Bundling policy:
- **Tesseract** (Apache 2.0) IS bundled with the installer.
- **Ghostscript** (AGPL v3) is NOT bundled. The gs helper exists only to
  detect a copy a user may place in ``vendor/ghostscript`` manually, and
  normally returns ``None``. The app guides users to install Ghostscript
  themselves from the official site.

Cross-platform: path layout is resolved per OS so the same helper works
once macOS/Linux vendor binaries are added in their installer milestones.
"""

import os
import sys
from typing import Optional


def app_root() -> str:
    """Return the directory bundled resources are rooted at."""
    if getattr(sys, "frozen", False):
        # PyInstaller stores bundled data under sys._MEIPASS. In one-folder
        # 6.x this is the _internal/ directory beside the executable; in
        # one-file builds it is the temporary extraction directory. Fall
        # back to the executable's own directory if _MEIPASS is unset.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return meipass
        return os.path.dirname(sys.executable)
    # Development: project root (app/engine/vendor.py -> ../.. -> project).
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def vendor_dir() -> str:
    """Return the path to the bundled vendor directory (may not exist)."""
    return os.path.join(app_root(), "vendor")


def bundled_tesseract() -> Optional[str]:
    """Return the path to the bundled Tesseract binary, or None if absent."""
    name = "tesseract.exe" if sys.platform == "win32" else "tesseract"
    candidate = os.path.join(vendor_dir(), "tesseract", name)
    return candidate if os.path.isfile(candidate) else None


def bundled_tessdata() -> Optional[str]:
    """Return the path to the bundled tessdata directory, or None if absent."""
    candidate = os.path.join(vendor_dir(), "tesseract", "tessdata")
    return candidate if os.path.isdir(candidate) else None


def bundled_ghostscript() -> Optional[str]:
    """
    Return the path to a bundled Ghostscript binary, or None.

    Normally returns None — Ghostscript is not shipped with the installer
    (AGPL). Present only to support a manually vendored copy.
    """
    if sys.platform == "win32":
        names = ("gswin64c.exe", "gswin32c.exe")
    else:
        names = ("gs",)
    base = os.path.join(vendor_dir(), "ghostscript", "bin")
    for name in names:
        candidate = os.path.join(base, name)
        if os.path.isfile(candidate):
            return candidate
    return None
