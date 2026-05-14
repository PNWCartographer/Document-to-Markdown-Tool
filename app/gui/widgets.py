"""
Custom widgets for the Darksquare-themed GUI.

PillButton    — Rounded pill/capsule-shaped button (Canvas).
ToggleSwitch  — Pill-shaped on/off slider toggle (Canvas).
GlassScrollbar — Thin pill-thumbed scrollbar (Canvas).
GlassDropdown — Liquid-glass themed dropdown selector (Canvas + Toplevel).

All pixel dimensions are scaled at creation time via the module-level
DPI factor.  Call ``set_dpi_scale(factor)`` once before building widgets.
"""

import math
import tkinter as tk
import tkinter.font as tkfont


# ── DPI helpers ─────────────────────────────────────────────

_DPI: float = 1.0


def set_dpi_scale(factor: float) -> None:
    """Set the global DPI scaling factor.  Call once before widget creation."""
    global _DPI
    _DPI = factor


def _s(px) -> int:
    """Scale an integer pixel value by the current DPI factor."""
    return round(px * _DPI)


def _sf(px) -> float:
    """Scale a float pixel value (outline widths, etc.) by the DPI factor."""
    return px * _DPI


# ── PillButton ──────────────────────────────────────────────

class PillButton(tk.Canvas):
    """
    A rounded pill-shaped button drawn on a Canvas.

    Two visual styles:
        "primary"   — filled background (accent color)
        "secondary" — outline only, background matches parent

    Usage::

        btn = PillButton(parent, text="Start", style="primary",
                         font=("Segoe UI", 13, "bold"), padx=26, pady=10,
                         command=on_click)
        btn.grid(row=0, column=0)
        btn.set_colors(fill="#a855f7", fg="#f5f0ff",
                       hover_fill="#b87afc", parent_bg="#121220")
    """

    _STEPS = 32        # polygon steps for outlined pills

    def __init__(self, parent, text="", command=None,
                 font=("Segoe UI", 11), padx=22, pady=8,
                 style="secondary", state="normal", **kw):
        bg = kw.pop("bg", kw.pop("background", parent.cget("bg")))
        super().__init__(parent, highlightthickness=0, bd=0, bg=bg, **kw)

        self._text_str = text
        self._command = command
        self._font_spec = font
        self._padx = _s(padx)
        self._pady = _s(pady)
        self._style = style
        self._state = state
        self._btn_hovered = False
        self._parent_bg = bg
        self._outline_w = _sf(1.5)   # scaled outline stroke width
        self._inset = _s(2)          # scaled edge inset

        # Colour slots — populated via set_colors()
        self._fill = ""
        self._fg = "#ffffff"
        self._outline_c = ""
        self._btn_hover_fill = ""
        self._btn_hover_fg = ""
        self._btn_hover_outline = ""
        self._disabled_fill = ""       # dimmed fill for primary disabled
        self._disabled_fg = "#555555"

        # Measure text and size the canvas
        self._font_obj = tkfont.Font(font=self._font_spec)
        self._btn_w = 0
        self._btn_h = 0
        self._recompute_size()

        # Event bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

        if state == "normal":
            self.config(cursor="hand2")

        self.after_idle(self._draw)

    # ── Public API ──────────────────────────────────────────

    def set_colors(self, *, fill="", fg="#fff", outline="",
                   hover_fill="", hover_fg="", hover_outline="",
                   disabled_fill="", disabled_fg="#555",
                   parent_bg=None):
        """Set all colour slots and redraw."""
        self._fill = fill
        self._fg = fg
        self._outline_c = outline
        self._btn_hover_fill = hover_fill or fill
        self._btn_hover_fg = hover_fg or fg
        self._btn_hover_outline = hover_outline or outline
        self._disabled_fill = disabled_fill
        self._disabled_fg = disabled_fg
        if parent_bg is not None:
            self._parent_bg = parent_bg
            self.config(bg=parent_bg)
        self._draw()

    def set_state(self, state: str):
        """'normal' or 'disabled'."""
        self._state = state
        self.config(cursor="hand2" if state == "normal" else "")
        self._draw()

    def set_text(self, text: str):
        self._text_str = text
        self._recompute_size()
        self._draw()

    # ── Internal ────────────────────────────────────────────

    def _recompute_size(self):
        tw = self._font_obj.measure(self._text_str)
        th = self._font_obj.metrics("linespace")
        self._btn_w = tw + 2 * self._padx
        self._btn_h = th + 2 * self._pady
        self.config(width=self._btn_w, height=self._btn_h)

    def _draw(self):
        self.delete("all")
        w, h = self._btn_w, self._btn_h
        if w < 4 or h < 4:
            return

        ins = self._inset

        # Resolve colours for current state
        if self._state == "disabled":
            if self._style == "primary":
                fill = self._disabled_fill or self._fill
            else:
                fill = self._parent_bg
            fg = self._disabled_fg
            outline = self._outline_c if self._style == "secondary" else ""
        elif self._btn_hovered:
            fill = self._btn_hover_fill if self._style == "primary" else self._parent_bg
            fg = self._btn_hover_fg
            outline = self._btn_hover_outline if self._style == "secondary" else ""
        else:
            fill = self._fill if self._style == "primary" else self._parent_bg
            fg = self._fg
            outline = self._outline_c if self._style == "secondary" else ""

        # Primary buttons: outline matches fill (invisible)
        if self._style == "primary":
            outline = fill

        # Pill shape
        _draw_pill(self, ins, ins, w - ins, h - ins, fill=fill, outline=outline,
                   outline_w=self._outline_w if self._style == "secondary" else 0,
                   steps=self._STEPS)

        # Text
        self.create_text(w / 2, h / 2, text=self._text_str,
                         fill=fg, font=self._font_spec, anchor="center")

    # ── Mouse events ────────────────────────────────────────

    def _on_enter(self, _e):
        if self._state != "disabled":
            self._btn_hovered = True
            self._draw()

    def _on_leave(self, _e):
        self._btn_hovered = False
        self._draw()

    def _on_press(self, _e):
        pass

    def _on_release(self, _e):
        if self._state != "disabled" and self._btn_hovered and self._command:
            self._command()


# ── ToggleSwitch ────────────────────────────────────────────

class ToggleSwitch(tk.Canvas):
    """
    A pill-shaped on/off toggle slider.

    Binds to a tkinter BooleanVar and toggles it on click.
    The thumb slides left (off) or right (on) inside a pill track.

    Usage::

        var = tk.BooleanVar(value=True)
        toggle = ToggleSwitch(parent, variable=var)
        toggle.grid(row=0, column=0)
        toggle.set_colors(on_fill="#a855f7", off_fill="#2a2a3c",
                          thumb_on="#ffffff", thumb_off="#888888",
                          parent_bg="#121220")
    """

    _STEPS = 24

    def __init__(self, parent, variable=None, command=None, **kw):
        self._track_w = _s(44)
        self._track_h = _s(24)
        self._thumb_pad = _s(3)

        bg = kw.pop("bg", kw.pop("background", parent.cget("bg")))
        super().__init__(parent, width=self._track_w, height=self._track_h,
                         highlightthickness=0, bd=0, bg=bg, cursor="hand2", **kw)

        self._var = variable
        self._command = command
        self._parent_bg = bg

        # Colour slots
        self._on_fill = "#a855f7"
        self._off_fill = "#3a3a4c"
        self._thumb_on = "#ffffff"
        self._thumb_off = "#7e7e98"

        self.bind("<ButtonRelease-1>", self._on_click)

        if self._var:
            self._var.trace_add("write", lambda *_: self.after_idle(self._draw))

        self.after_idle(self._draw)

    # ── Public API ──────────────────────────────────────────

    def set_colors(self, *, on_fill="", off_fill="", thumb_on="",
                   thumb_off="", parent_bg=None):
        """Set all colour slots and redraw."""
        if on_fill:  self._on_fill = on_fill
        if off_fill: self._off_fill = off_fill
        if thumb_on: self._thumb_on = thumb_on
        if thumb_off: self._thumb_off = thumb_off
        if parent_bg is not None:
            self._parent_bg = parent_bg
            self.config(bg=parent_bg)
        self._draw()

    # ── Internal ────────────────────────────────────────────

    def _draw(self):
        self.delete("all")
        w, h = self._track_w, self._track_h
        on = self._var.get() if self._var else False

        # Track (pill)
        track_fill = self._on_fill if on else self._off_fill
        _draw_pill(self, 1, 1, w - 1, h - 1, fill=track_fill,
                   outline=track_fill, outline_w=0, steps=self._STEPS)

        # Thumb (circle)
        pad = self._thumb_pad
        thumb_r = (h - 2 * pad) / 2
        cx = (w - pad - thumb_r - 1) if on else (pad + thumb_r + 1)
        cy = h / 2
        thumb_c = self._thumb_on if on else self._thumb_off
        self.create_oval(cx - thumb_r, cy - thumb_r,
                         cx + thumb_r, cy + thumb_r,
                         fill=thumb_c, outline="")

    def _on_click(self, _e):
        if self._var:
            self._var.set(not self._var.get())
        if self._command:
            self._command()


# ── GlassScrollbar ──────────────────────────────────────────

class GlassScrollbar(tk.Canvas):
    """
    A thin, pill-thumbed scrollbar matching Apple / liquid-glass aesthetics.

    Drop-in replacement for ttk.Scrollbar — same ``set(first, last)`` and
    ``command`` protocol.  No arrow buttons; the thumb hides when content fits.

    Usage::

        sb = GlassScrollbar(parent, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.grid(row=0, column=1, sticky="ns")
        sb.set_colors(thumb="#3a3a52", thumb_hover="#5a5a72",
                      parent_bg="#0e0e16")
    """

    def __init__(self, parent, orient="vertical", command=None, **kw):
        self._sb_width = _s(10)
        self._thumb_w = _s(5)
        self._thumb_min_h = _s(28)
        self._thumb_pad = _s(4)

        bg = kw.pop("bg", kw.pop("background", parent.cget("bg")))
        super().__init__(parent, width=self._sb_width, highlightthickness=0,
                         bd=0, bg=bg, **kw)

        self._command = command
        self._first = 0.0
        self._last = 1.0
        self._parent_bg = bg

        # Colour slots
        self._thumb_color = "#3a3a52"
        self._thumb_hover_color = "#5a5a72"

        self._hovered = False
        self._dragging = False
        self._drag_start_y = 0
        self._drag_start_first = 0.0

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda _e: self._draw())

    # ── Public API (scrollbar protocol) ─────────────────────

    def set(self, first, last):
        """Called by the scrollable widget to report its view position."""
        self._first = float(first)
        self._last = float(last)
        self._draw()

    def set_colors(self, *, thumb="", thumb_hover="", parent_bg=None):
        if thumb:       self._thumb_color = thumb
        if thumb_hover: self._thumb_hover_color = thumb_hover
        if parent_bg is not None:
            self._parent_bg = parent_bg
            self.config(bg=parent_bg)
        self._draw()

    # ── Internal drawing ────────────────────────────────────

    def _draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 2 or h < 10:
            return

        # Hide thumb when all content is visible
        if self._first <= 0.0 and self._last >= 1.0:
            return

        visible = self._last - self._first
        track_h = h - 2 * self._thumb_pad
        thumb_h = max(self._thumb_min_h, visible * track_h)

        # Thumb y-position
        scrollable = track_h - thumb_h
        if scrollable > 0 and (1.0 - visible) > 0:
            ratio = self._first / (1.0 - visible)
        else:
            ratio = 0.0
        ty = self._thumb_pad + ratio * scrollable

        # Colour
        color = self._thumb_hover_color if (self._hovered or self._dragging) \
                else self._thumb_color

        # Draw vertical pill thumb centred horizontally
        tw = self._thumb_w
        tx = (w - tw) / 2
        r = tw / 2
        # Top cap
        self.create_oval(tx, ty, tx + tw, ty + 2 * r,
                         fill=color, outline="")
        # Bottom cap
        self.create_oval(tx, ty + thumb_h - 2 * r, tx + tw,
                         ty + thumb_h, fill=color, outline="")
        # Middle
        if thumb_h > 2 * r:
            self.create_rectangle(tx, ty + r, tx + tw,
                                  ty + thumb_h - r, fill=color, outline="")

    # ── Thumb geometry helper ───────────────────────────────

    def _thumb_region(self):
        """Return (y_top, y_bottom) of the current thumb."""
        h = self.winfo_height()
        visible = self._last - self._first
        track_h = h - 2 * self._thumb_pad
        thumb_h = max(self._thumb_min_h, visible * track_h)
        scrollable = track_h - thumb_h
        if scrollable > 0 and (1.0 - visible) > 0:
            ratio = self._first / (1.0 - visible)
        else:
            ratio = 0.0
        ty = self._thumb_pad + ratio * scrollable
        return ty, ty + thumb_h

    # ── Mouse events ────────────────────────────────────────

    def _on_enter(self, _e):
        self._hovered = True
        self._draw()

    def _on_leave(self, _e):
        if not self._dragging:
            self._hovered = False
            self._draw()

    def _on_press(self, e):
        t_top, t_bot = self._thumb_region()
        if t_top <= e.y <= t_bot:
            # Start dragging
            self._dragging = True
            self._drag_start_y = e.y
            self._drag_start_first = self._first
        else:
            # Click in trough -> page scroll
            direction = -1 if e.y < t_top else 1
            if self._command:
                self._command("scroll", str(direction), "pages")

    def _on_drag(self, e):
        if not self._dragging or not self._command:
            return
        h = self.winfo_height()
        visible = self._last - self._first
        track_h = h - 2 * self._thumb_pad
        thumb_h = max(self._thumb_min_h, visible * track_h)
        scrollable = track_h - thumb_h
        if scrollable <= 0:
            return

        dy = e.y - self._drag_start_y
        d_ratio = dy / scrollable
        new_first = self._drag_start_first + d_ratio * (1.0 - visible)
        new_first = max(0.0, min(new_first, 1.0 - visible))
        self._command("moveto", str(new_first))

    def _on_release(self, _e):
        self._dragging = False
        if not self._hovered:
            self._hovered = False
        self._draw()


# ── GlassDropdown ───────────────────────────────────────────

class GlassDropdown(tk.Canvas):
    """
    A themed dropdown selector with liquid-glass styling.

    Displays the current value inside a pill-shaped button with a chevron.
    Click opens a frameless popup with hoverable option items.
    Binds to a tkinter StringVar and fires *command* on selection change.

    Usage::

        var = tk.StringVar(value="Quality")
        dd = GlassDropdown(parent, variable=var,
                           options=["Fast", "Balanced", "Quality"],
                           font=("Segoe UI", 11))
        dd.grid(row=0, column=0)
        dd.set_colors(fill="#161622", fg="#ece9f4", border="#2a2a3c",
                      hover_fill="#1e1e30", popup_bg="#161622",
                      popup_fg="#ece9f4", popup_hover_bg="#1e1e30",
                      popup_accent="#a855f7", chevron="#7e7e98",
                      parent_bg="#121220")
    """

    _STEPS = 32         # polygon steps for outlined pill shape

    def __init__(self, parent, variable=None, options=None, command=None,
                 font=("Segoe UI", 11), **kw):
        bg = kw.pop("bg", kw.pop("background", parent.cget("bg")))
        super().__init__(parent, highlightthickness=0, bd=0, bg=bg,
                         cursor="hand2", **kw)

        self._var = variable
        self._dd_options = list(options or [])
        self._command = command
        self._font_spec = font
        self._parent_bg = bg
        self._dd_hovered = False
        self._popup = None
        self._root_bind_id = None

        # DPI-scaled layout constants
        self._padx = _s(12)
        self._pady = _s(6)
        self._chevron_space = _s(24)
        self._inset = _s(1)

        # Colour slots (dark defaults)
        self._fill = "#161622"
        self._fg = "#ece9f4"
        self._border_c = "#2a2a3c"
        self._hover_fill = "#1e1e30"
        self._popup_bg = "#161622"
        self._popup_fg = "#ece9f4"
        self._popup_hover_bg = "#1e1e30"
        self._popup_accent = "#a855f7"
        self._chevron_c = "#7e7e98"

        # Measure and size
        self._font_obj = tkfont.Font(font=self._font_spec)
        self._dd_w = 0
        self._dd_h = 0
        self._recompute_size()

        # Event bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

        if self._var:
            self._var.trace_add("write", lambda *_: self.after_idle(self._draw))

        self.after_idle(self._draw)

    # ── Public API ──────────────────────────────────────────

    def set_colors(self, *, fill="", fg="", border="", hover_fill="",
                   popup_bg="", popup_fg="", popup_hover_bg="",
                   popup_accent="", chevron="", parent_bg=None):
        """Set all colour slots and redraw."""
        if fill:           self._fill = fill
        if fg:             self._fg = fg
        if border:         self._border_c = border
        if hover_fill:     self._hover_fill = hover_fill
        if popup_bg:       self._popup_bg = popup_bg
        if popup_fg:       self._popup_fg = popup_fg
        if popup_hover_bg: self._popup_hover_bg = popup_hover_bg
        if popup_accent:   self._popup_accent = popup_accent
        if chevron:        self._chevron_c = chevron
        if parent_bg is not None:
            self._parent_bg = parent_bg
            self.config(bg=parent_bg)
        self._draw()

    # ── Internal sizing ─────────────────────────────────────

    def _recompute_size(self):
        max_tw = 0
        for opt in self._dd_options:
            tw = self._font_obj.measure(opt)
            max_tw = max(max_tw, tw)
        self._dd_w = max_tw + 2 * self._padx + self._chevron_space
        th = self._font_obj.metrics("linespace")
        self._dd_h = th + 2 * self._pady
        self.config(width=self._dd_w, height=self._dd_h)

    # ── Drawing ─────────────────────────────────────────────

    def _draw(self):
        self.delete("all")
        w, h = self._dd_w, self._dd_h
        if w < 4 or h < 4:
            return

        ins = self._inset
        fill = self._hover_fill if self._dd_hovered else self._fill

        # Pill-shaped background with border
        _draw_pill(self, ins, ins, w - ins, h - ins, fill=fill,
                   outline=self._border_c, outline_w=_sf(1), steps=self._STEPS)

        # Current value text (left-aligned)
        text = self._var.get() if self._var else ""
        self.create_text(self._padx + _s(2), h / 2, text=text, fill=self._fg,
                         font=self._font_spec, anchor="w")

        # Chevron indicator (right side)
        cx = w - _s(14)
        cy = h / 2
        # Small downward triangle
        sz = _sf(3.5)
        self.create_polygon(
            cx - sz, cy - sz * 0.5,
            cx + sz, cy - sz * 0.5,
            cx,      cy + sz * 0.6,
            fill=self._chevron_c, outline="",
        )

    # ── Mouse events ────────────────────────────────────────

    def _on_enter(self, _e):
        self._dd_hovered = True
        self._draw()

    def _on_leave(self, _e):
        self._dd_hovered = False
        self._draw()

    def _on_click(self, _e):
        if self._popup and self._popup.winfo_exists():
            self._close_popup()
            return
        self._open_popup()

    # ── Popup ───────────────────────────────────────────────

    def _open_popup(self):
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + _s(3)

        popup = tk.Toplevel(self)
        popup.withdraw()                # hide until positioned
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)

        # Outer frame = 1 px border via background colour
        popup.config(bg=self._border_c)

        inner = tk.Frame(popup, bg=self._popup_bg)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        current = self._var.get() if self._var else ""

        for opt in self._dd_options:
            item_frame = tk.Frame(inner, bg=self._popup_bg, cursor="hand2")
            item_frame.pack(fill="x")

            is_current = (opt == current)
            lbl = tk.Label(
                item_frame,
                text=opt,
                font=self._font_spec,
                bg=self._popup_bg,
                fg=self._popup_accent if is_current else self._popup_fg,
                anchor="w",
                padx=self._padx + _s(4),
                pady=_s(5),
            )
            lbl.pack(fill="x")

            # Hover effects (capture variables properly via defaults)
            def _enter(e, f=item_frame, l=lbl):
                f.config(bg=self._popup_hover_bg)
                l.config(bg=self._popup_hover_bg)

            def _leave(e, f=item_frame, l=lbl):
                f.config(bg=self._popup_bg)
                l.config(bg=self._popup_bg)

            def _click(e, o=opt):
                self._select(o)

            for w in (item_frame, lbl):
                w.bind("<Enter>", _enter)
                w.bind("<Leave>", _leave)
                w.bind("<ButtonRelease-1>", _click)

        # Measure actual popup size and position
        popup.update_idletasks()
        pw = max(self._dd_w, popup.winfo_reqwidth())
        ph = popup.winfo_reqheight()

        # Clamp to screen boundaries
        screen_h = self.winfo_screenheight()
        screen_w = self.winfo_screenwidth()
        if y + ph > screen_h - _s(20):
            y = self.winfo_rooty() - ph - _s(3)   # open above instead
        if x + pw > screen_w - _s(10):
            x = screen_w - pw - _s(10)

        popup.geometry(f"{pw}x{ph}+{x}+{y}")
        popup.deiconify()

        # Dismissal bindings
        popup.bind("<Escape>", lambda e: self._close_popup())
        popup.focus_set()

        self._popup = popup

        # Listen for clicks outside the popup on the root window
        self._root_bind_id = self.winfo_toplevel().bind(
            "<ButtonPress-1>", self._on_root_press, add="+"
        )

    def _on_root_press(self, event):
        """Close popup when clicking outside it (but not on the button itself)."""
        if not self._popup or not self._popup.winfo_exists():
            return

        # Check if click is inside the popup
        px = self._popup.winfo_rootx()
        py = self._popup.winfo_rooty()
        pw = self._popup.winfo_width()
        ph = self._popup.winfo_height()
        in_popup = (px <= event.x_root <= px + pw and
                    py <= event.y_root <= py + ph)

        # Check if click is on this dropdown button (toggle handled by _on_click)
        bx = self.winfo_rootx()
        by = self.winfo_rooty()
        bw = self.winfo_width()
        bh = self.winfo_height()
        in_button = (bx <= event.x_root <= bx + bw and
                     by <= event.y_root <= by + bh)

        if not in_popup and not in_button:
            self._close_popup()

    def _select(self, option):
        if self._var:
            self._var.set(option)
        self._close_popup()
        if self._command:
            self._command()

    def _close_popup(self):
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None
        # Remove the root-level click binding
        if self._root_bind_id is not None:
            try:
                self.winfo_toplevel().unbind("<ButtonPress-1>",
                                            self._root_bind_id)
            except Exception:
                pass
            self._root_bind_id = None


# ── Shared helpers ──────────────────────────────────────────

def _draw_pill(canvas: tk.Canvas, x1, y1, x2, y2, *,
               fill, outline, outline_w=0, steps=16):
    """
    Draw a smooth pill (stadium) shape on *canvas*.

    When no visible outline is needed the shape is composed of
    hardware-rendered ``create_oval`` caps + ``create_rectangle`` middle
    for perfectly smooth curves.  When an outline stroke IS visible a
    single-path polygon is used so the stroke is seamless.
    """
    r = (y2 - y1) / 2
    needs_outline = outline_w > 0 and outline and outline != fill

    if not needs_outline:
        # ── Oval + rect approach: pixel-perfect at any DPI ──
        # Left cap
        canvas.create_oval(x1, y1, x1 + 2 * r, y2,
                           fill=fill, outline="")
        # Right cap
        canvas.create_oval(x2 - 2 * r, y1, x2, y2,
                           fill=fill, outline="")
        # Middle rectangle (only if wider than two caps)
        mid_l = x1 + r
        mid_r = x2 - r
        if mid_r > mid_l:
            canvas.create_rectangle(mid_l, y1, mid_r, y2,
                                    fill=fill, outline="")
    else:
        # ── Polygon path for seamless outline stroke ────────
        cx_l = x1 + r
        cx_r = x2 - r
        cy = (y1 + y2) / 2

        pts = []
        # Right semicircle  (-90 deg -> +90 deg)
        for i in range(steps + 1):
            a = -math.pi / 2 + i * math.pi / steps
            pts.extend([cx_r + r * math.cos(a), cy + r * math.sin(a)])
        # Left semicircle   (+90 deg -> +270 deg)
        for i in range(steps + 1):
            a = math.pi / 2 + i * math.pi / steps
            pts.extend([cx_l + r * math.cos(a), cy + r * math.sin(a)])

        canvas.create_polygon(pts, fill=fill, outline=outline,
                              width=outline_w, smooth=False)
