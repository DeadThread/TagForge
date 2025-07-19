# utils/theme_manager.py
from __future__ import annotations

import os
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

log = logging.getLogger("tagforge")

# cache of already-sourced .tcl files
_loaded_themes: set[str] = set()

# ------------------------------------------------------------------
# small helpers
# ------------------------------------------------------------------
def _current_theme_colors(root: tk.Misc) -> tuple[str, str]:
    """Return (bg, fg) from the active ttk theme."""
    style = ttk.Style(root)
    bg = style.lookup("TFrame", "background") or style.lookup(".", "background") or "#FFFFFF"
    fg = style.lookup("TLabel", "foreground") or style.lookup(".", "foreground") or "#000000"
    return bg, fg


def _restyle_existing_tk_widgets(widget: tk.Misc, bg: str, fg: str) -> None:
    """
    Recursively apply bg/fg to *classic* Tk widgets so they match ttk.
    ttk widgets are skipped.
    """
    try:
        cls = widget.winfo_class()
        if cls not in (
            "TFrame",
            "TLabel",
            "TButton",
            "Treeview",
            "TEntry",
            "TCombobox",
        ):
            if "background" in widget.config():
                widget.config(background=bg)
            if "foreground" in widget.config():
                widget.config(foreground=fg)
    except Exception:
        pass

    for child in widget.winfo_children():
        _restyle_existing_tk_widgets(child, bg, fg)


def invert_textbox_colors(widget: tk.Misc, dark: bool = True) -> None:
    """Inverts colors for classic Tk widgets like Text/Entry."""
    fg = "#ffffff" if dark else "#000000"
    bg = "#1e1e1e" if dark else "#ffffff"
    insert_bg = "#ffffff" if dark else "#000000"
    widget.configure(fg=fg, bg=bg, insertbackground=insert_bg)


# ------------------------------------------------------------------
# user-chosen .tcl themes
# ------------------------------------------------------------------
def load_ttk_theme(root: tk.Misc, tcl_path: str, log_func) -> str | None:
    """
    Source a .tcl theme file once and switch ttk to it.
    Old Tk widgets are recoloured to blend in.
    """
    try:
        abs_path = os.path.abspath(tcl_path)
        theme_name = os.path.splitext(os.path.basename(abs_path))[0]

        if theme_name not in _loaded_themes:
            try:
                root.tk.call("source", abs_path)
                _loaded_themes.add(theme_name)
                log_func(f"Sourced theme file: {theme_name}", level="debug")
            except tk.TclError as e:
                if "already exists" not in str(e):
                    raise

        ttk.Style(root).theme_use(theme_name)
        bg, fg = _current_theme_colors(root)
        _restyle_existing_tk_widgets(root, bg, fg)
        log.debug(f"Activated theme: {theme_name}")
        return abs_path

    except Exception as e:
        log_func(f"[ERROR] Failed to load theme '{tcl_path}': {e}", level="error")
        log.error("Failed to load theme %s: %s", tcl_path, e)
        return None


def select_and_load_theme(root,
                          ini_parser,
                          config_file,
                          themes_dir,
                          log_func) -> str | None:
    """Ask user for a .tcl file starting in project-root /themes."""
    fname = filedialog.askopenfilename(
        title="Select Theme File",
        filetypes=[("Tcl Theme Files", "*.tcl")],
        initialdir=os.path.abspath(themes_dir),
    )
    if not fname:
        return None

    path = load_ttk_theme(root, fname, log_func)
    if not path:
        return None

    ini_parser.setdefault("Theme", {})
    ini_parser.set("Theme", "file", path)
    with open(config_file, "w", encoding="utf-8") as f:
        ini_parser.write(f)
    return path


def save_current_theme(ini_parser, config_file, theme_path: str) -> None:
    if theme_path:
        ini_parser.setdefault("Theme", {})
        ini_parser.set("Theme", "file", theme_path)
        with open(config_file, "w", encoding="utf-8") as f:
            ini_parser.write(f)


# ------------------------------------------------------------------
# Default / native theme helper
# ------------------------------------------------------------------
def _platform_default(root: tk.Misc) -> str:
    """Return 'vista', 'aqua', or 'clam' depending on platform."""
    win_sys = root.tk.call("tk", "windowingsystem")
    if win_sys == "win32":
        return "vista"
    if win_sys == "aqua":
        return "aqua"
    return "clam"   # Linux & others


def use_default_theme(root, ini_parser, config_file, log_func) -> None:
    """
    Switch to the platform’s built-in ttk theme and save that choice.
    No .tcl files are kept, so next launch starts clean.
    """
    default_theme = _platform_default(root)
    style = ttk.Style(root)
    try:
        style.theme_use(default_theme)
    except tk.TclError:
        style.theme_use("default")
        default_theme = "default"

    bg, fg = _current_theme_colors(root)
    _restyle_existing_tk_widgets(root, bg, fg)

    ini_parser.setdefault("Theme", {})
    ini_parser.set("Theme", "file", f"builtin:{default_theme}")
    with open(config_file, "w", encoding="utf-8") as f:
        ini_parser.write(f)

    log_func(f"Using default ttk theme: {default_theme}", level="info")


# ------------------------------------------------------------------
# backward-compat “remove_theme”  → just call use_default_theme
# ------------------------------------------------------------------
def remove_theme(root, ini_parser, config_file, log_func) -> None:
    """
    Legacy entry-point: now simply switches to the platform default theme
    and wipes any saved .tcl path from the INI.
    """
    # blow away record of external themes so fresh loads don’t keep old defs
    _loaded_themes.clear()
    if ini_parser.has_section("Theme"):
        ini_parser.remove_section("Theme")  # we’ll re-add below
    use_default_theme(root, ini_parser, config_file, log_func)
    log_func("Custom theme cleared; reverted to native look.", level="info")


# Export the functions for import *
__all__ = [
    "load_ttk_theme",
    "invert_textbox_colors",
    "_current_theme_colors",
    "_restyle_existing_tk_widgets",
    "select_and_load_theme",
    "save_current_theme",
    "use_default_theme",
    "remove_theme",
    "load_saved_theme",
]


def load_saved_theme(root, ini_parser, config_file, log_func):
    """
    Load and apply the saved theme from the INI file.
    Supports both 'builtin:theme_name' and file paths.
    """
    if not os.path.exists(config_file):
        return

    ini_parser.read(config_file)

    if ini_parser.has_option("Theme", "file"):
        theme_path = ini_parser.get("Theme", "file")
        if theme_path.startswith("builtin:"):
            theme_name = theme_path.split(":", 1)[1]
            try:
                ttk.Style(root).theme_use(theme_name)
                bg, fg = _current_theme_colors(root)
                _restyle_existing_tk_widgets(root, bg, fg)
                invert_textbox_colors_safe(root)
                # Use the main logger's debug method instead of log_func
                import logging
                logging.getLogger("tagforge").debug(f"Using built-in theme: {theme_name}")
            except Exception as e:
                log_func(f"Failed to apply built-in theme: {e}", level="error")
        else:
            load_ttk_theme(root, theme_path, log_func)

def invert_textbox_colors_safe(widget: tk.Misc, dark: bool = True) -> None:
    """
    Recursively invert colors only on classic Tk Text and Entry widgets.
    Avoid calling on ttk widgets or root window directly.
    """
    try:
        cls = widget.winfo_class()
        if cls in ("Text", "Entry"):
            invert_textbox_colors(widget, dark=dark)
    except Exception:
        pass

    for child in widget.winfo_children():
        invert_textbox_colors_safe(child, dark=dark)