import sys
import tkinter as tk

_DELAY_MS   = 500
_FONT_FAMILY = ("Segoe UI" if sys.platform == "win32" else
                "Helvetica Neue" if sys.platform == "darwin" else "sans-serif")
_FONT_TIP   = (_FONT_FAMILY, 11)
_SMALL_TIP  = "Resize the window to view this tooltip."


class Tooltip:
    """Hover tooltip with theme support.

    Pass get_theme as a callable that returns the current theme dict so the
    tooltip always matches the active light/dark palette even when the theme
    changes after the tooltip was created.
    """

    def __init__(self, widget: tk.Widget, text: str, get_theme):
        self._widget    = widget
        self._text      = text
        self._get_theme = get_theme
        self._win       = None
        self._job       = None
        widget.bind("<Enter>",       self._schedule, add="+")
        widget.bind("<Leave>",       self._cancel,   add="+")
        widget.bind("<ButtonPress>", self._cancel,   add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self._job = self._widget.after(_DELAY_MS, self._show)

    def _cancel(self, _event=None):
        if self._job:
            try:
                self._widget.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None

    def _show(self):
        self._job = None
        try:
            if not self._widget.winfo_exists():
                return
        except Exception:
            return
        t = self._get_theme()

        wx = self._widget.winfo_rootx()
        wy = self._widget.winfo_rooty()
        wh = self._widget.winfo_height()

        root = self._widget.winfo_toplevel()
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        rw = root.winfo_width()
        rh = root.winfo_height()

        def _build(text):
            """(Re)create the tooltip window with given text; return (tw, th)."""
            if self._win:
                self._win.destroy()
            win = tk.Toplevel(self._widget)
            win.wm_overrideredirect(True)
            # +10000+10000 keeps the measurement window off every monitor so
            # it never overlaps the hovered widget (which would fire <Leave>
            # and cancel the tooltip before it can be positioned).
            win.wm_geometry("+10000+10000")
            win.config(bg=t["border"])
            tk.Label(
                win, text=text, justify="left", wraplength=380,
                padx=10, pady=8, bg=t["sidebar_bg"], fg=t["text"],
                font=_FONT_TIP,
            ).pack(padx=1, pady=1)
            win.update_idletasks()
            self._win = win
            return win.winfo_width(), win.winfo_height()

        def _place(tw, th):
            """Return (x, y) only if tooltip fits inside window without
            overlapping the widget.  Returns None when it cannot fit."""
            x = wx + 4
            if x + tw > rx + rw - 4:
                x = rx + rw - tw - 4
            x = max(x, rx + 4)

            # Try below first
            y_b = wy + wh + 6
            if y_b + th <= ry + rh - 4:
                return x, y_b

            # Try above (clamped to window top)
            y_a = max(wy - th - 4, ry + 4)
            if y_a + th <= wy:              # must clear the widget
                return x, y_a

            return None                     # cannot fit without overlap or clipping

        tw, th = _build(self._text)
        result  = _place(tw, th)

        if result is None:
            # Full text won't fit — swap in the short fallback and try again
            tw, th = _build(_SMALL_TIP)
            result  = _place(tw, th)

        if result is None:
            # Even the short tip doesn't fit (extremely small window).
            # Show it below the widget anyway — it will clip at the edge
            # but will not cause the pulsing-overlap problem.
            x = max(min(wx + 4, rx + rw - tw - 4), rx + 4)
            result = (x, wy + wh + 6)

        self._win.wm_geometry(f"+{result[0]}+{result[1]}")
