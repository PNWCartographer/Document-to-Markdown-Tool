import sys
import os

# Hide the console window on Windows when launched via python.exe
# instead of pythonw.exe.  Has no effect on Linux / macOS.
try:
    from ctypes import windll
    windll.user32.ShowWindow(windll.kernel32.GetConsoleWindow(), 0)
except Exception:
    pass

# Enable Per-Monitor DPI awareness on Windows before any tkinter calls.
# Level 2 (Per Monitor DPI Aware) gives the sharpest rendering on every
# display, including multi-monitor setups with different DPI values.
# Must run before tk.Tk() is created.
try:
    windll.shcore.SetProcessDpiAwareness(2)   # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    pass

sys.path.insert(0, os.path.dirname(__file__))

from gui.app import App

if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except Exception:
        import traceback
        msg = traceback.format_exc()
        # Try to show error even if tkinter is not available
        try:
            import tkinter as _tk
            from tkinter import messagebox as _mb
            _root = _tk.Tk()
            _root.withdraw()
            _mb.showerror("Startup Error", f"Failed to start:\n\n{msg}")
            _root.destroy()
        except Exception:
            pass
        # Also try writing to a log file
        try:
            import os, datetime
            log_dir = os.path.join(
                os.environ.get("APPDATA", os.path.expanduser("~")),
                "DocToMarkdown",
            )
            os.makedirs(log_dir, exist_ok=True)
            with open(os.path.join(log_dir, "crash.log"), "a", encoding="utf-8") as fh:
                fh.write(f"\n{'='*60}\n")
                fh.write(f"Crash at {datetime.datetime.now()}\n")
                fh.write(msg)
        except Exception:
            pass
