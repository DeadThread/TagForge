import os
import sys
import subprocess
import tkinter as tk
from utils import theme_manager

def build_menu(gui_instance):
    menubar = tk.Menu(gui_instance.root)
    gui_instance.root.config(menu=menubar)

    # Helper function to open a file in the system default text editor
    def open_in_default_editor(path):
        try:
            if sys.platform.startswith('win'):
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
            gui_instance.log_message(f"Opened {path} in default editor.", "info")
        except Exception as e:
            gui_instance.log_message(f"[ERROR] Failed to open {path}: {e}", "error")

    # Edit menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Edit", menu=edit_menu)

    edit_menu.add_command(label="Scheme Editor...", command=gui_instance._open_scheme_editor)

    # Add links to open asset files
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
    artists_file = os.path.abspath(os.path.join(assets_dir, "Artists.txt"))
    cities_file = os.path.abspath(os.path.join(assets_dir, "Cities.txt"))
    venues_file = os.path.abspath(os.path.join(assets_dir, "Venues.txt"))

    edit_menu.add_separator()
    edit_menu.add_command(label="Open Artists.txt", command=lambda: open_in_default_editor(artists_file))
    edit_menu.add_command(label="Open Cities.txt", command=lambda: open_in_default_editor(cities_file))
    edit_menu.add_command(label="Open Venues.txt", command=lambda: open_in_default_editor(venues_file))

    # View menu
    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="View", menu=view_menu)

    def select_theme():
        theme_path = theme_manager.select_and_load_theme(
            root=gui_instance.root,
            ini_parser=gui_instance.cfg,
            config_file=gui_instance.config_file,
            themes_dir="themes",
            log_func=gui_instance.log_message,
        )
        if theme_path:
            gui_instance.log_message(f"Theme applied: {theme_path}", "info")

    def reset_theme():
        theme_manager.remove_theme(
            root=gui_instance.root,
            ini_parser=gui_instance.cfg,
            config_file=gui_instance.config_file,
            log_func=gui_instance.log_message,
        )

    view_menu.add_command(label="Select Theme...", command=select_theme)
    view_menu.add_command(label="Use Default Theme", command=reset_theme)
