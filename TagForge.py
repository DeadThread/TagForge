import os
import threading
import configparser
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

# Audio tagging libs
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

# --- internal modules ---
from utils.constants import HISTORY_FILE, USED_CACHE_FILE, ASSETS_DIR, CACHE_FILE, ARTISTS_FILE, VENUES_FILE, CITIES_FILE
from utils.asset_loader import ensure_asset_files_exist, load_asset_lists
from utils import theme_manager
from utils.logger import logger, log_message
from utils.gui_logger import GuiLogger
from utils.process_thread import process_thread
from utils.queue_manager import QueueManager
from utils.cache_manager import CacheController
from utils.combobox_utils import update_combobox_values
from utils.scheme_evaluator import load_schemes_from_ini, apply_schemes_to_processor, SchemeEvaluator
from gui.build_gui import build_main_gui
from scheme_editor.scheme_editor import SchemeEditor
from gui.metadata_gui import handle_tree_selection, populate_tree, on_tree_open
from gui.build_menu import build_menu
from utils.audio_player import AudioPlayer

# Import sash persistence functions
from gui.pane_sash_persistence import (
    install_outer_pane_sash_persistence,
    install_main_pane_sash_persistence,
    install_left_paned_sash_persistence,
    install_main_window_size_persistence,
)

# Import Processor and match_folder
from utils.processor import Processor
from utils.match_folder import match_folder


class TkTagForge:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.withdraw()  # Hide immediately to avoid startup flash

        self.root.title("TagForge")
        self.root.geometry("1600x1100")

        icon_path = os.path.join("assets", "tagforge.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                logger.warning(f"Failed to set window icon '{icon_path}': {e}")

        # --- GUI Logger ---
        self.gui_logger = GuiLogger()
        self.log_message = self.gui_logger.log  # shorthand log function to GUI logger

        # Placeholder for log Text widget (will be set by build_main_gui)
        self.log = None

        # --- State Variables ---
        self.current = None
        self.saved = []
        self.meta = {}
        self.last_source = ""
        self.last_format = ""
        self.last_genre = ""
        self.last_add = ""

        self.histories = {k: set() for k in ("artist", "venue", "city", "add", "source", "format", "genre")}
        self.used_cache = {"artists": {}, "genres": {}}
        self.artist_cache = set()
        self.genre_cache = set()

        # Tkinter StringVars for UI
        self.root_var = tk.StringVar()
        self.current_folder_path_var = tk.StringVar()
        self.proposed_folder_path_var = tk.StringVar()

        self.artist = tk.StringVar()
        self.venue = tk.StringVar()
        self.city = tk.StringVar()
        self.source = tk.StringVar()
        self.fmt = tk.StringVar()
        self.add = tk.StringVar()
        self.genre = tk.StringVar()
        self.year = tk.StringVar()
        self.mo = tk.StringVar()
        self.da = tk.StringVar()

        self.saving_scheme = ""
        self.folder_scheme = ""
        self.saved_meta = {}

        # Config parser and config file path
        self.config_file = Path("config/config.ini")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.cfg = configparser.ConfigParser(interpolation=None)
        self.cfg.read(self.config_file)

        # Prepare themes folder
        os.makedirs("themes", exist_ok=True)
        self.gui_logger.log("Verified themes folder at: themes", level="debug")

        # Load saved theme early (before building widgets)
        theme_manager.load_saved_theme(
            root=self.root,
            ini_parser=self.cfg,
            config_file=self.config_file,
            log_func=self.gui_logger.buffer,
        )

        # Set window background to match theme to reduce flash
        bg, _ = theme_manager._current_theme_colors(self.root)
        self.root.configure(bg=bg)

        # Ensure assets
        ensure_asset_files_exist(self.gui_logger.buffer)
        self.artists_list, self.venues_list, self.cities_list = load_asset_lists(log_callback=self.gui_logger.buffer)

        # Default scheme evaluator for processor initialization
        def default_evaluate_schemes(metadata):
            return metadata.get("artist", "Unknown Artist")

        self.processor = Processor(
            evaluate_schemes_func=default_evaluate_schemes,
            match_folder_func=match_folder,
            log_func=self.gui_logger.log,
            artists_list=self.artists_list,
            venues_list=self.venues_list,
            cities_list=self.cities_list,
            artist_cache=self.artist_cache,
            genre_cache=self.genre_cache,
            used_cache=self.used_cache,
            histories=self.histories,
        )

        self.load_schemes_from_config()
        self.update_processor_schemes()

        # Build GUI widgets (this should assign self.log, etc)
        build_main_gui(self)

        # Attach GUI logger to main log widget and configure color tags for logging
        if self.log:
            self.gui_logger.attach(self.log)
            self._configure_log_tags()

        # Initialize queue manager after GUI is ready
        self.queue_manager = QueueManager(getattr(self, "queue", None), self.log)
        self.queue_manager.set_scheme_evaluator(self.processor._evaluate_schemes)

        # Debug keypress logging for comboboxes
        def debug_keypress(ev):
            print(f"Combobox {ev.widget} KeyPress: keysym={ev.keysym} char={repr(ev.char)}")

        for cb_name in ("c_art", "c_ven", "c_city", "c_src", "c_fmt", "c_gen"):
            cb = getattr(self, cb_name, None)
            if cb:
                cb.bind("<KeyPress>", debug_keypress, add="+")

        # Sash persistence
        self._install_sash_persistence()
        self._install_outer_pane_sash_persistence()
        self._install_left_paned_sash_persistence()
        self._install_main_window_size_persistence()

        # Cache controller for histories and used caches
        self.cache_controller = CacheController(
            histories=self.histories,
            used_cache=self.used_cache,
            log_func=self.gui_logger.log,
            gui_instance=self,
        )
        self.cache_controller.load_history()
        self.cache_controller.load_used_cache()

        # Refresh queue UI and combobox dropdowns
        self.queue_manager.refresh_ui()
        self._update_combobox_values()

        # Build menu
        build_menu(self)

        # Initialize audio player in bottom pane
        self._init_audio_player()

        # Bind treeview events if tree exists
        if hasattr(self, "tree") and self.tree:
            self.tree.bind("<<TreeviewOpen>>", lambda e: on_tree_open(self.tree, self.log, e))
            self.tree.bind("<<TreeviewSelect>>", lambda e: handle_tree_selection(self, e))

        # Window close event handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Flush logs and signal initialization done
        self.gui_logger.flush()
        self.gui_logger.log("TagForge GUI initialization complete.", level="debug")

        # Update the UI and finally show window to avoid flashing
        self.root.update_idletasks()
        self.root.deiconify()

    # --- Sash persistence wrappers ---
    def _install_outer_pane_sash_persistence(self):
        install_outer_pane_sash_persistence(self)

    def _install_sash_persistence(self):
        install_main_pane_sash_persistence(self)

    def _install_left_paned_sash_persistence(self):
        install_left_paned_sash_persistence(self)

    def _install_main_window_size_persistence(self):
        install_main_window_size_persistence(self)

    # --- Audio Player Initialization ---
    def _init_audio_player(self):
        try:
            audio_frame = self.outer_pane.panes()[-1]
            bottom_pane = self.root.nametowidget(audio_frame)
        except Exception:
            bottom_pane = tk.Frame(self.root)
            bottom_pane.pack(side=tk.BOTTOM, fill=tk.X)
            logger.warning("Fallback: created bottom pane frame for AudioPlayer")

        try:
            self.audio_player = AudioPlayer(
                bottom_pane,
                log_widget=self.log,
                get_current_folder_callback=lambda: self.current,
                set_artist=lambda v: self.artist.set(v) if hasattr(self, "artist") else None,
                set_date=lambda v: self.year.set(v.split("-")[0]) if v and hasattr(self, "year") else None,
                set_venue=lambda v: self.venue.set(v) if hasattr(self, "venue") else None,
            )
        except Exception as e:
            self.gui_logger.log(f"Audio player init failed: {e}", level="error")
            logger.exception("Failed to create AudioPlayer")

    # --- Cache/history methods ---
    def load_used_cache(self):
        self.cache_controller.load_used_cache()

    def _save_used_cache(self):
        self.cache_controller.save_used_cache()

    def _update_used_cache(self):
        self.cache_controller.update_used_cache_with_ui()

    def _save_history(self):
        self.cache_controller.save_history()

    def _load_history(self):
        self.cache_controller.load_history()

    # --- Combobox update ---
    def _update_combobox_values(self):
        update_combobox_values(
            artists_list=self.artists_list,
            venues_list=self.venues_list,
            cities_list=self.cities_list,
            artist_cache=self.artist_cache,
            genre_cache=self.genre_cache,
            histories=self.histories,
            last_source=self.last_source,
            last_format=self.last_format,
            last_genre=self.last_genre,
            last_add=self.last_add,
            comboboxes_dict={
                "artist": getattr(self, "c_art", None),      # Changed from artist_combobox to c_art
                "venue": getattr(self, "c_ven", None),       # Changed from venue_combobox to c_ven  
                "city": getattr(self, "c_city", None),       # Changed from city_combobox to c_city
                "add": getattr(self, "c_add", None),         # Changed from add_combobox to c_add
                "source": getattr(self, "c_src", None),      # Changed from source_combobox to c_src
                "format": getattr(self, "c_fmt", None),      # Changed from format_combobox to c_fmt
                "genre": getattr(self, "c_gen", None),       # Changed from genre_combobox to c_gen
            },
        )

    def load_schemes_from_config(self, log_loaded=True):
        """Load schemes from config.ini, or Default preset if no schemes exist."""
        # First try to load from existing config
        self.folder_scheme, self.saving_scheme = load_schemes_from_ini(log=self.gui_logger.log, log_loaded=False)
        
        # If no schemes found, try to load Default preset
        if not self.folder_scheme and not self.saving_scheme:
            self._load_default_preset()
        
        if log_loaded:
            self.gui_logger.log(f"Loaded folder scheme: {self.folder_scheme}", level="info")
            self.gui_logger.log(f"Loaded saving scheme: {self.saving_scheme}", level="info")

    def _load_default_preset(self):
        """Load the Default preset from scheme_preset.ini if available."""
        try:
            preset_file = Path("config/scheme_preset.ini")
            
            # Ensure preset file exists with Default
            if not preset_file.exists():
                self._create_default_preset_file(preset_file)
            
            # Load Default preset
            config = configparser.ConfigParser(interpolation=None)
            config.read(preset_file)
            
            if "Default" in config:
                self.saving_scheme = config["Default"].get("saving_scheme", "%artist%/$year(%date%)")
                self.folder_scheme = config["Default"].get("folder_scheme", "%date% - %venue% - %city% [%format%] [%additional%]")
                
                # Also update the main config.ini with these values
                self._save_schemes_to_config()
                
                self.gui_logger.log("Loaded Default preset schemes", level="debug")
            else:
                # Fallback to hardcoded defaults
                self.saving_scheme = "%artist%/$year(%date%)"
                self.folder_scheme = "%date% - %venue% - %city% [%format%] [%additional%]"
                self.gui_logger.log("Using hardcoded default schemes", level="debug")
                
        except Exception as e:
            # Fallback to hardcoded defaults
            self.saving_scheme = "%artist%/$year(%date%)"
            self.folder_scheme = "%date% - %venue% - %city% [%format%] [%additional%]"
            self.gui_logger.log(f"Error loading Default preset, using hardcoded defaults: {e}", level="warn")

    def _create_default_preset_file(self, preset_file):
        """Create scheme_preset.ini with Default preset."""
        try:
            preset_file.parent.mkdir(parents=True, exist_ok=True)
            config = configparser.ConfigParser(interpolation=None)
            
            # Add default preset
            config.add_section("Default")
            config.set("Default", "saving_scheme", "%artist%/$year(%date%)")
            config.set("Default", "folder_scheme", "%date% - %venue% - %city% [%format%] [%additional%]")
            
            with open(preset_file, "w", encoding="utf-8") as f:
                config.write(f)
            
            self.gui_logger.log("Created scheme_preset.ini with Default preset", level="debug")
            
        except Exception as e:
            self.gui_logger.log(f"Error creating preset file: {e}", level="error")

    def _save_schemes_to_config(self):
        """Save current schemes to config.ini while preserving existing sections."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use the existing self.cfg instead of creating a new one
            # This preserves all existing sections that were loaded at startup
            section_name = "SchemeEditor"
            
            # Check if section exists before trying to add it
            if not self.cfg.has_section(section_name):
                self.cfg.add_section(section_name)
            
            self.cfg.set(section_name, "saving_scheme", self.saving_scheme or "")
            self.cfg.set(section_name, "folder_scheme", self.folder_scheme or "")
            
            # Write the entire config back
            with open(self.config_file, "w", encoding="utf-8") as f:
                self.cfg.write(f)
            
            self.gui_logger.log(f"Updated config.ini with schemes - saving: '{self.saving_scheme}', folder: '{self.folder_scheme}'", level="debug")
            
            # Verify the write worked by reading back
            verify_config = configparser.ConfigParser(interpolation=None)  # Also disable interpolation here
            verify_config.read(self.config_file)
            if verify_config.has_section(section_name):
                saved_saving = verify_config.get(section_name, "saving_scheme", fallback="")
                saved_folder = verify_config.get(section_name, "folder_scheme", fallback="")
                self.gui_logger.log(f"Verified config.ini - saving: '{saved_saving}', folder: '{saved_folder}'", level="debug")
            else:
                self.gui_logger.log("ERROR: Section not found in config.ini after saving!", level="error")
            
        except Exception as e:
            self.gui_logger.log(f"Error saving schemes to config: {e}", level="error")
            import traceback
            self.gui_logger.log(f"Traceback: {traceback.format_exc()}", level="error")

    def update_processor_schemes(self):
        self.gui_logger.log("Updating processor schemes...", level="debug")
        old_folder = getattr(self, "folder_scheme", None)
        old_saving = getattr(self, "saving_scheme", None)
        self.gui_logger.log(f"Old folder scheme: {old_folder}", level="debug")
        self.gui_logger.log(f"Old saving scheme: {old_saving}", level="debug")

        evaluator = SchemeEvaluator(
            self.folder_scheme,
            self.saving_scheme,
            log_func=self.gui_logger.log,
        )
        self.processor.scheme_evaluator = evaluator
        self.processor._evaluate_schemes = evaluator.evaluate

        if hasattr(self, "queue_manager") and self.queue_manager:
            self.queue_manager.set_scheme_evaluator(self.processor._evaluate_schemes)
            self.gui_logger.log("QueueManager scheme evaluator updated.", level="debug")

    def _configure_log_tags(self):
        """Configure color tags in the main log widget."""
        if not self.log:
            return
        bold_font = ("TkDefaultFont", 10, "bold")

        self.log.tag_config("folder_scheme_line", foreground="orange", font=bold_font)
        self.log.tag_config("saving_scheme_line", foreground="blue", font=bold_font)

        self.log.tag_config("preview_label_teal", foreground="teal", font=bold_font)  # New unique label color
        self.log.tag_config("preview_path_blue", foreground="blue", font=bold_font)
        self.log.tag_config("preview_path_orange", foreground="orange", font=bold_font)


        
    def _log_scheme_update(self, folder_scheme, saving_scheme, live_preview):
        if not self.log:
            import logging
            logger.info(f"Updated Folder Scheme: {folder_scheme}")
            logger.info(f"Updated Saving Scheme: {saving_scheme}")
            logger.info(f"Live Preview Output: {live_preview}")
            return

        self.log.config(state="normal")

        # Entire line in orange and bold
        self.log.insert("end", f"Updated Folder Scheme: {folder_scheme}\n", "folder_scheme_line")

        # Entire line in blue and bold
        self.log.insert("end", f"Updated Saving Scheme: {saving_scheme}\n", "saving_scheme_line")

        # Label in teal (or another unique color), bold
        self.log.insert("end", "Live Preview Output: ", "preview_label_teal")

        # Path coloring (blue + orange split), also bold
        if "/" in live_preview:
            base_path, current_folder = live_preview.rsplit("/", 1)
            base_path += "/"
        else:
            base_path = live_preview
            current_folder = ""

        self.log.insert("end", base_path, "preview_path_blue")
        if current_folder:
            self.log.insert("end", current_folder + "\n", "preview_path_orange")
        else:
            self.log.insert("end", "\n")

        self.log.config(state="disabled")
        self.log.see("end")


    def _open_scheme_editor(self):
        def on_scheme_saved(saving_scheme=None, folder_scheme=None, preview_path=None):
            # Sample metadata matching scheme editor's sample including current_folder key
            md = {
                "artist": "Phish",
                "venue": "Madison Square Garden",
                "city": "New York, NY",
                "date": "1995-12-31",
                "source": "SBD",
                "format": "FLAC24",
                "additional": "NYE95",
                "formatN": ["FLAC24", "MP3_320"],
                "additionalN": ["NYE95", "Remastered"],
                "sourceN": ["SBD", "Audience"],
                "year": "1995",
                "current_folder": "ph1995-12-31 - Madison Square Garden - New York, NY",  # Your sample folder name
            }

            evaluator = SchemeEvaluator(folder_scheme, saving_scheme, log_func=self.gui_logger.log)

            # Evaluate folder scheme (no current_folder needed here)
            folder_eval = evaluator.evaluate(md).replace("\\", "/").rstrip("/")

            # Use the sample current_folder value already present in md for saving scheme evaluation
            saving_eval = evaluator.evaluate(md).replace("\\", "/").rstrip("/")

            # Compose preview path the way scheme editor expects
            if not saving_eval or saving_eval.lower() == "(root)":
                preview_path = folder_eval
            else:
                preview_path = str(Path(saving_eval) / Path(folder_eval)).replace("\\", "/").rstrip("/")

            self.folder_scheme = folder_scheme
            self.saving_scheme = saving_scheme

            self.update_processor_schemes()
            self._log_scheme_update(folder_scheme, saving_scheme, preview_path)

            if hasattr(self, "queue_manager"):
                self.queue_manager.refresh_proposed_names()
            if hasattr(self, "refresh_live_preview"):
                self.refresh_live_preview()

        editor = SchemeEditor(self.root, log_callback=self.gui_logger.log, on_save_callback=on_scheme_saved)
        editor.protocol("WM_DELETE_WINDOW", editor.destroy)
        editor.grab_set()
        self.root.wait_window(editor)

    # --- Folder browsing and tree refresh ---
    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.root_var.set(path)
            populate_tree(getattr(self, "tree", None), self.log, path)

    def _refresh(self):
        root = self.root_var.get()
        if root and os.path.isdir(root):
            populate_tree(getattr(self, "tree", None), self.log, root)

    def clear_queue(self):
        self.queue_manager.clear()

    @staticmethod
    def normalize_path_slashes(path: str) -> str:
        return path.replace("\\", "/") if path else ""

    def _queue(self):
        selected_items = self.tree.selection() if hasattr(self, "tree") else []
        if not selected_items:
            return

        for iid in selected_items:
            values = self.tree.item(iid, "values")
            if not values:
                continue

            folder_path = values[0]
            normalized_path = folder_path.replace("\\", "/")
            if normalized_path in self.queue_manager.saved:
                continue

            meta = {
                "artist": self.artist.get(),
                "venue": self.venue.get(),
                "city": self.city.get(),
                "source": self.source.get(),
                "format": self.fmt.get(),
                "additional": self.add.get(),
                "genre": self.genre.get(),
                "date": f"{self.year.get()}-{self.mo.get()}-{self.da.get()}",
                "currentfoldername": os.path.basename(normalized_path),
            }

            proposed_name = ""
            if self.queue_manager.evaluate_schemes_func:
                try:
                    proposed_name = self.queue_manager.evaluate_schemes_func(meta)
                except Exception as e:
                    logger.error(f"Scheme evaluation error: {e}")

            self.queue_manager.add(normalized_path, proposed_name, meta)

    def _dequeue(self):
        self.queue_manager.remove_selected()

    def refresh_queue_ui(self):
        self.queue_manager.refresh_ui()

    def _clear(self):
        for var_name in ["artist", "source", "fmt", "venue", "city", "add", "genre", "year", "mo", "da"]:
            var = getattr(self, var_name, None)
            if var:
                var.set("")

    def _process(self):
        if not self.queue_manager.saved:
            self.gui_logger.log("No folders queued for processing.", level="warn")
            return

        root_folder = self.root_var.get()
        if root_folder and not os.path.isdir(root_folder):
            self.gui_logger.log(f"Root folder invalid or missing: {root_folder}", level="error")
            return

        # Capture current form values into histories BEFORE processing
        for key, var_name in [
            ("artist", "artist"),
            ("venue", "venue"), 
            ("city", "city"),
            ("add", "add"),
            ("source", "source"),
            ("format", "fmt"),
            ("genre", "genre"),
        ]:
            var = getattr(self, var_name, None)
            if var:
                val = var.get().strip()
                if val:
                    self.histories[key].add(val)

        self.last_source = self.source.get() if hasattr(self, "source") else ""
        self.last_format = self.fmt.get() if hasattr(self, "fmt") else ""
        self.last_genre = self.genre.get() if hasattr(self, "genre") else ""

        threading.Thread(target=lambda: process_thread(self), daemon=True).start()

    def _on_close(self):
        for key, var_name in [
            ("artist", "artist"),
            ("venue", "venue"),
            ("city", "city"),
            ("add", "add"),
            ("source", "source"),
            ("format", "fmt"),
            ("genre", "genre"),
        ]:
            var = getattr(self, var_name, None)
            if var:
                val = var.get().strip()
                if val:
                    self.histories[key].add(val)

        self._save_history()
        self._save_used_cache()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TkTagForge(root)
    root.mainloop()


if __name__ == "__main__":
    main()