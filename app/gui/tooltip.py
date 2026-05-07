import tkinter as tk

_DELAY_MS = 500
_FONT_TIP  = ("Segoe UI", 11)


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
            self._widget.after_cancel(self._job)
            self._job = None
        if self._win:
            self._win.destroy()
            self._win = None

    def _show(self):
        self._job = None
        t = self._get_theme()

        self._win = tk.Toplevel(self._widget)
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry("+0+0")          # off-screen until we measure
        self._win.config(bg=t["border"])

        tk.Label(
            self._win,
            text=self._text,
            justify="left",
            wraplength=380,
            padx=10,
            pady=8,
            bg=t["sidebar_bg"],
            fg=t["text"],
            font=_FONT_TIP,
        ).pack(padx=1, pady=1)

        # Measure actual tooltip size before placing it
        self._win.update_idletasks()
        tw = self._win.winfo_width()
        th = self._win.winfo_height()

        # Preferred position: just below and aligned with the widget
        wx = self._widget.winfo_rootx()
        wy = self._widget.winfo_rooty()
        wh = self._widget.winfo_height()

        # Root window bounds
        root = self._widget.winfo_toplevel()
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        rw = root.winfo_width()
        rh = root.winfo_height()

        x = wx + 4
        y = wy + wh + 6

        # Clamp so tooltip stays inside the root window horizontally
        if x + tw > rx + rw:
            x = rx + rw - tw - 4

        # If it would go below the window, flip it above the widget instead
        if y + th > ry + rh:
            y = wy - th - 4

        # Never go left of the window left edge
        x = max(x, rx + 4)

        self._win.wm_geometry(f"+{x}+{y}")
