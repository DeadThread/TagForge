import tkinter as tk
import re
from tkinter import ttk, filedialog
from datetime import datetime
from pathlib import Path
import json
from utils.constants import DEFAULTS, HISTORY_FILE
from gui.metadata_gui import handle_tree_selection, on_tree_open
from utils.audio_player import AudioPlayer
from utils.autocomplete import AutocompleteCombobox
from utils.logger import log_message  # Make sure this is imported


def build_main_gui(app):
    self = app  # Use self as alias for convenience

    # Ensure history_cache is loaded once before merging dropdown values
    def load_history_cache():
        path = Path(HISTORY_FILE)
        if not path.exists():
            print(f"[WARNING] History file not found at {path.resolve()}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"[DEBUG] Loaded history cache keys: {list(data.keys())}")
                return data
        except Exception as e:
            print(f"[ERROR] Failed to load history cache: {e}")
            return {}

    if not hasattr(self, "history_cache"):
        self.history_cache = load_history_cache()
    else:
        print("[DEBUG] history_cache already set, skipping load.")

    # Check required attributes
    if not hasattr(self, "config_file"):
        raise AttributeError("TagForge app must set self.config_file before calling build_main_gui.")
    if not hasattr(self, "ini_file"):
        self.ini_file = self.config_file  # fallback for legacy code
    if not hasattr(self, "get_current_folder"):
        self.get_current_folder = lambda: getattr(self, "current", None)

    def split_and_clean_ordered(items):
        """Helper to split comma/semicolon separated items, strip whitespace, and keep order without duplicates."""
        seen = set()
        result = []
        for item in items:
            parts = [part.strip() for part in re.split(r'[;,]', item) if part.strip()]
            for part in parts:
                if part not in seen:
                    seen.add(part)
                    result.append(part)
        return result

    def merge_dropdown_values(field: str):
        defaults_raw = DEFAULTS.get(field, [])
        history_raw = self.history_cache.get(field, []) if hasattr(self, "history_cache") else []

        defaults_set = set(defaults_raw)
        history_set = set(history_raw)

        # Unique history items that aren't already in defaults
        unique_history = history_set - defaults_set

        combined = list(defaults_raw) + sorted(unique_history, key=str.lower)


        return combined


    # --- Top toolbar ---
    top = tk.Frame(self.root, pady=4)
    top.pack(fill=tk.X)
    tk.Label(top, text="Root Folder:").pack(side=tk.LEFT, padx=4)
    tk.Entry(top, textvariable=self.root_var, state="readonly", width=70).pack(side=tk.LEFT, padx=4)
    ttk.Button(top, text="Browse", command=self._browse).pack(side=tk.LEFT, padx=4)
    ttk.Button(top, text="Refresh", command=self._refresh).pack(side=tk.LEFT, padx=4)

    # --- Outer PanedWindow ---
    self.outer_pane = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
    self.outer_pane.pack(fill=tk.BOTH, expand=True)

    # --- Main PanedWindow (horizontal) ---
    self.paned_main = ttk.PanedWindow(self.outer_pane, orient=tk.HORIZONTAL)
    self.outer_pane.add(self.paned_main, weight=10)

    # Left and right frames inside paned_main
    self.left = tk.Frame(self.paned_main, padx=6, pady=6)
    self.right = tk.Frame(self.paned_main, padx=6, pady=6)
    self.paned_main.add(self.left, weight=1)
    self.paned_main.add(self.right, weight=1)

    # --- Left PanedWindow (vertical) ---
    self.left_paned = ttk.PanedWindow(self.left, orient=tk.VERTICAL)
    self.left_paned.pack(fill=tk.BOTH, expand=True)

    # --- Top Left Frame (Metadata + Folder Tree) ---
    top_left_frame = tk.Frame(self.left_paned)
    self.left_paned.add(top_left_frame, weight=7)

    # --- Metadata Fields ---
    meta = tk.Frame(top_left_frame)
    meta.pack(fill=tk.X)

    # StringVars for metadata
    self.artist = tk.StringVar()
    self.venue = tk.StringVar()
    self.city = tk.StringVar()
    self.year = tk.StringVar()
    self.mo = tk.StringVar()
    self.da = tk.StringVar()
    self.genre = tk.StringVar()
    self.source = tk.StringVar()
    self.fmt = tk.StringVar()
    self.add = tk.StringVar()

    # Row 0: Artist and Date
    tk.Label(meta, text="Artist:").grid(row=0, column=0, sticky="w")
    self.c_art = AutocompleteCombobox(meta, textvariable=self.artist, width=30, state="normal")
    self.c_art.set_completion_list(getattr(self, 'artists_list', []))
    self.c_art.grid(row=0, column=1, sticky="w", padx=4)

    tk.Label(meta, text="Date:").grid(row=0, column=2, sticky="w")
    df = tk.Frame(meta)
    df.grid(row=0, column=3, sticky="w")
    years = [str(y) for y in range(datetime.now().year, 1999, -1)]
    ttk.Combobox(df, textvariable=self.year, values=years, width=6).pack(side=tk.LEFT)
    ttk.Combobox(df, textvariable=self.mo, values=[f"{m:02d}" for m in range(1, 13)], width=4).pack(side=tk.LEFT, padx=1)
    ttk.Combobox(df, textvariable=self.da, values=[f"{d:02d}" for d in range(1, 32)], width=4).pack(side=tk.LEFT)

    # Row 1: Venue, Genre, Format
    tk.Label(meta, text="Venue:").grid(row=1, column=0, sticky="w")
    self.c_ven = AutocompleteCombobox(meta, textvariable=self.venue, width=30, state="normal")
    self.c_ven.set_completion_list(getattr(self, 'venues_list', []))
    self.c_ven.grid(row=1, column=1, sticky="w", padx=4)

    tk.Label(meta, text="Genre(s):").grid(row=1, column=2, sticky="w")
    self.c_gen = AutocompleteCombobox(meta, textvariable=self.genre, width=21, state="normal")
    self.c_gen.set_completion_list(merge_dropdown_values("genre"))
    self.c_gen.grid(row=1, column=3, sticky="w", padx=4)

    tk.Label(meta, text="Format:").grid(row=1, column=4, sticky="w")
    self.c_fmt = AutocompleteCombobox(meta, textvariable=self.fmt, width=18, state="normal")
    self.c_fmt.set_completion_list(merge_dropdown_values("format"))
    self.c_fmt.grid(row=1, column=5, sticky="w", padx=4)

    # Row 2: City, Source, Additional
    tk.Label(meta, text="City:").grid(row=2, column=0, sticky="w")
    self.c_city = AutocompleteCombobox(meta, textvariable=self.city, width=25, state="normal")
    self.c_city.set_completion_list(getattr(self, 'cities_list', []))
    self.c_city.grid(row=2, column=1, sticky="w", padx=4)

    tk.Label(meta, text="Source:").grid(row=2, column=2, sticky="w")
    self.c_src = AutocompleteCombobox(meta, textvariable=self.source, width=21, state="normal")
    self.c_src.set_completion_list(merge_dropdown_values("source"))
    self.c_src.grid(row=2, column=3, sticky="w", padx=4)

    tk.Label(meta, text="Additional:").grid(row=2, column=4, sticky="w")
    self.c_add = AutocompleteCombobox(meta, textvariable=self.add, width=18, state="normal")
    self.c_add.set_completion_list(merge_dropdown_values("add"))
    self.c_add.grid(row=2, column=5, sticky="w", padx=4)

    # --- Folder Tree ---
    tree_fr = tk.Frame(top_left_frame)
    tree_fr.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
    tk.Label(tree_fr, text="Folders:").grid(row=0, column=0, sticky="w", columnspan=2)

    self.tree = ttk.Treeview(tree_fr, columns=("folder_path",))
    self.tree.grid(row=1, column=0, sticky="nsew")
    self.tree.heading("#0", text="Folder Name")
    self.tree.heading("folder_path", text="Folder Path")
    self.tree.column("#0", width=400, anchor="w")
    self.tree.column("folder_path", width=800, anchor="w")

    self.scrollbar_tree_v = ttk.Scrollbar(tree_fr, orient=tk.VERTICAL, command=self.tree.yview)
    self.scrollbar_tree_v.grid(row=1, column=1, sticky="ns")
    self.scrollbar_tree_h = ttk.Scrollbar(tree_fr, orient=tk.HORIZONTAL, command=self.tree.xview)
    self.scrollbar_tree_h.grid(row=2, column=0, columnspan=2, sticky="ew")
    self.tree.configure(yscrollcommand=self.scrollbar_tree_v.set, xscrollcommand=self.scrollbar_tree_h.set)
    tree_fr.grid_rowconfigure(1, weight=1)
    tree_fr.grid_columnconfigure(0, weight=1)

    self.tree.bind("<<TreeviewSelect>>", handle_tree_selection.__get__(self))
    self.tree.bind("<<TreeviewOpen>>", lambda e: on_tree_open(self, e))

    # --- Bottom Left: Folder Queue ---
    bottom_left_frame = tk.Frame(self.left_paned)
    self.left_paned.add(bottom_left_frame, weight=3)
    bottom_left_frame.pack_propagate(False)

    btn_fr = tk.Frame(bottom_left_frame, pady=6)
    btn_fr.pack(fill=tk.X)
    ttk.Button(btn_fr, text="Save Selected Folder", command=self._queue).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_fr, text="Remove Selected Folder", command=self._dequeue).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_fr, text="Process All Saved Folders", command=self._process).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_fr, text="Clear Fields", command=self._clear).pack(side=tk.LEFT, padx=4)

    q_fr = tk.Frame(bottom_left_frame)
    q_fr.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
    tk.Label(q_fr, text="Folders to Process:").grid(row=0, column=0, sticky="w", columnspan=2)

    self.queue = ttk.Treeview(q_fr, columns=("folder_path", "proposed_name"), show="headings")
    self.queue.heading("folder_path", text="Folder Path")
    self.queue.heading("proposed_name", text="Proposed Folder Name")
    self.queue.column("folder_path", width=500, anchor="w", stretch=False)
    self.queue.column("proposed_name", width=1000, anchor="w", stretch=False)
    self.queue.grid(row=1, column=0, sticky="nsew")

    self.scrollbar_queue_v = ttk.Scrollbar(q_fr, orient=tk.VERTICAL, command=self.queue.yview)
    self.scrollbar_queue_v.grid(row=1, column=1, sticky="ns")
    self.scrollbar_queue_h = ttk.Scrollbar(q_fr, orient=tk.HORIZONTAL, command=self.queue.xview)
    self.scrollbar_queue_h.grid(row=2, column=0, columnspan=2, sticky="ew")
    self.queue.configure(yscrollcommand=self.scrollbar_queue_v.set, xscrollcommand=self.scrollbar_queue_h.set)
    q_fr.grid_rowconfigure(1, weight=1)
    q_fr.grid_columnconfigure(0, weight=1)

    # --- Right Pane: Log Panel ---
    log_frame = tk.Frame(self.right)
    log_frame.pack(fill=tk.BOTH, expand=True)
    tk.Label(log_frame, text="Log:").grid(row=0, column=0, sticky="w")

    self.log = tk.Text(log_frame, wrap="none")
    self.log.grid(row=1, column=0, columnspan=2, sticky="nsew")

    vbar_log = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log.yview)
    vbar_log.grid(row=1, column=2, sticky="ns")
    hbar_log = ttk.Scrollbar(log_frame, orient=tk.HORIZONTAL, command=self.log.xview)
    hbar_log.grid(row=2, column=0, columnspan=2, sticky="ew")
    self.log.configure(yscrollcommand=vbar_log.set, xscrollcommand=hbar_log.set)
    log_frame.grid_rowconfigure(1, weight=1)
    log_frame.grid_columnconfigure(0, weight=1)

    def clear_log():
        self.log.config(state='normal')
        self.log.delete("1.0", "end")
        self.log.config(state='normal')

    ttk.Button(log_frame, text="Clear Logs", command=clear_log).grid(row=0, column=1, sticky="e", padx=10)

    self.log.tag_config("folder_scheme", foreground="green")
    self.log.tag_config("saving_scheme", foreground="purple")
    self.log.tag_config("preview_label", foreground="orange", font=("TkDefaultFont", 10, "bold"))
    self.log.tag_config("preview_path_orange", foreground="orange")
    self.log.tag_config("preview_path_blue", foreground="blue")
    self.log.tag_config("error", foreground="red")
    self.log.tag_config("warning", foreground="orange")

    # --- Tab Order ---
    self.c_art.focus_set()
    date_widgets = df.winfo_children()

    def set_tab_order(ws):
        for i, w in enumerate(ws):
            def handler(e, i=i):
                if e.keysym == "Tab":
                    if e.state & 0x0001:  # Shift pressed
                        ws[(i - 1) % len(ws)].focus_set()
                    else:
                        ws[(i + 1) % len(ws)].focus_set()
                    return "break"
            w.bind("<KeyPress>", handler)

    set_tab_order([self.c_art, self.c_ven, self.c_city, *date_widgets, self.c_gen, self.c_src, self.c_fmt, self.c_add])

    # --- Audio Player Frame ---
    self.audio_frame = tk.Frame(self.outer_pane, height=240)
    self.audio_frame.pack_propagate(False)
    self.outer_pane.add(self.audio_frame, weight=3)

    print("[DEBUG] Added audio_frame to outer_pane with fixed height.")

    try:
        self.audio_player = AudioPlayer(
            self.audio_frame,
            get_current_folder_callback=self.get_current_folder,
            log_widget=self.log,
            set_artist=self.artist.set,
            set_date=self.year.set,
            set_venue=self.venue.set,
        )
        self.audio_player.pack(fill=tk.BOTH, expand=True)
    except Exception as e:
        err_msg = f"[ERROR] Failed to load AudioPlayer: {e}"
        print(err_msg)
        if hasattr(self, 'log') and self.log:
            log_message(self.log, err_msg, level="error")
        fallback = tk.Label(self.audio_frame, text="AudioPlayer failed to load")
        fallback.pack(fill=tk.BOTH, expand=True)

    def _update_artist_city_venue_dropdowns():
        try:
            self.c_art.set_completion_list(getattr(self, 'artists_list', []))
            self.c_city.set_completion_list(getattr(self, 'cities_list', []))
            self.c_ven.set_completion_list(getattr(self, 'venues_list', []))
        except Exception as e:
            if hasattr(self, 'log') and self.log:
                log_message(self.log, f"[ERROR] Failed to update dropdowns: {e}", level="error")

    self._update_artist_city_venue_dropdowns = _update_artist_city_venue_dropdowns
