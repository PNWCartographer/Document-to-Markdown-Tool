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
    app = App()
    app.run()
