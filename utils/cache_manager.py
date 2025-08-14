import os
import json
from pathlib import Path
from utils.constants import DEFAULTS, HISTORY_FILE, USED_CACHE_FILE
from utils.logger import log_message


def load_used_cache(log_func=None):
    try:
        if os.path.exists(USED_CACHE_FILE):
            with open(USED_CACHE_FILE, "r", encoding="utf-8") as f:
                used_cache = json.load(f)
            if "artists" not in used_cache:
                used_cache["artists"] = {}
        else:
            used_cache = {"artists": {}}
        return used_cache
    except Exception as e:
        if log_func:
            log_func(f"[ERROR] Failed to load used cache: {e}", level="error")
        return {"artists": {}}


def save_used_cache(used_cache, log_func=None):
    try:
        os.makedirs(os.path.dirname(USED_CACHE_FILE), exist_ok=True)
        with open(USED_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(used_cache, f, indent=2)
        if log_func:
            log_func("Used cache saved.", level="info")
    except Exception as e:
        if log_func:
            log_func(f"[ERROR] Failed to save used cache: {e}", level="error")


def update_used_cache(used_cache, artist_val, genre_val, log_func=None):
    try:
        if artist_val and genre_val:
            used_cache.setdefault("artists", {})[artist_val] = genre_val
            if log_func:
                log_func(f"[DEBUG] Cached artist => genre: {artist_val} => {genre_val}", level="debug")
    except Exception as e:
        if log_func:
            log_func(f"[ERROR] Failed to update used cache: {e}", level="error")


def load_history(histories, set_last_used_callback=None, log_func=None):
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, vals in data.items():
                # Skip loading artist, city, venue from history file
                if key in {"artist", "city", "venue"}:
                    if log_func:
                        log_func(f"Skipping loading '{key}' from history file.", level="debug")
                    continue
                
                cleaned = [v for v in vals if v]
                histories[key] = set(cleaned)
                
                # REMOVED: Don't automatically set last used values on startup
                # if cleaned and set_last_used_callback:
                #     set_last_used_callback(key, cleaned[0])
        else:
            for key in histories:
                histories[key] = set()
    except Exception as e:
        if log_func:
            log_func(f"[ERROR] Failed to load history cache: {e}", level="error")


def save_history(histories, last_source="", last_format="", last_genre="", log_func=None):
    data = {}
    for key, values in histories.items():
        vals = sorted(values, key=lambda x: x.lower())
        defaults = DEFAULTS.get(key, [])

        last_used_val = {
            "source": last_source,
            "format": last_format,
            "genre": last_genre,
        }.get(key, None)

        combined_set = set()
        combined_list = []

        if last_used_val and last_used_val not in combined_set:
            combined_list.append(last_used_val)
            combined_set.add(last_used_val)

        for val in defaults:
            if val and val not in combined_set:
                combined_list.append(val)
                combined_set.add(val)

        for val in vals:
            if val and val not in combined_set:
                combined_list.append(val)
                combined_set.add(val)

        data[key] = combined_list

    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if log_func:
            log_func("History saved.", level="info")
    except Exception as e:
        if log_func:
            log_func(f"[ERROR] Failed to save history: {e}", level="error")


class CacheController:
    def __init__(self, histories, used_cache, log_func=None, gui_instance=None):
        """
        histories: dict of sets for dropdown histories
        used_cache: dict for artist/genre cache
        log_func: optional logging function (msg, level)
        gui_instance: optional GUI reference for accessing widget values and last-used vars
        """
        self.histories = histories
        self.used_cache = used_cache
        self.log = log_func or (lambda msg, level="info": None)
        self.gui = gui_instance

        # We set config file path to find history file relative to config
        # If gui_instance is provided, try to get config_file from it
        if gui_instance and hasattr(gui_instance, "config_file"):
            self.config_file = Path(gui_instance.config_file)
        else:
            # fallback to a sensible default or HISTORY_FILE parent folder
            self.config_file = Path(HISTORY_FILE).parent / "config.ini"

    def load_history(self):
        def set_last_used(key, value):
            # MODIFIED: Only set last used values when explicitly called, not on startup
            if self.gui:
                if key == "source":
                    self.gui.last_source = value
                elif key == "format":
                    self.gui.last_format = value
                elif key == "genre":
                    self.gui.last_genre = value
                elif key == "artist":
                    self.gui.last_artist = value
                elif key == "venue":
                    self.gui.last_venue = value
                elif key == "city":
                    self.gui.last_city = value
                elif key == "add":
                    self.gui.last_add = value

        # MODIFIED: Don't pass the callback to avoid auto-setting last used values
        load_history(self.histories, set_last_used_callback=None, log_func=self.log)
        self.log("History loaded.", level="debug")

    def set_last_used_value(self, key, value):
        """
        Explicitly set a last used value - only call this when user actually uses a value
        """
        if self.gui:
            if key == "source":
                self.gui.last_source = value
            elif key == "format":
                self.gui.last_format = value
            elif key == "genre":
                self.gui.last_genre = value
            elif key == "artist":
                self.gui.last_artist = value
            elif key == "venue":
                self.gui.last_venue = value
            elif key == "city":
                self.gui.last_city = value
            elif key == "add":
                self.gui.last_add = value

    def get_current_ui_values(self):
        """
        Get current values from UI widgets - only non-empty values
        """
        if not self.gui:
            return {}
        
        ui_values = {}
        widget_map = {
            'artist': getattr(self.gui, 'artist', None),
            'venue': getattr(self.gui, 'venue', None),
            'city': getattr(self.gui, 'city', None),
            'add': getattr(self.gui, 'add', None),
            'source': getattr(self.gui, 'source', None),
            'format': getattr(self.gui, 'format', None),
            'genre': getattr(self.gui, 'genre', None),
        }
        
        for key, widget in widget_map.items():
            if widget:
                value = widget.get().strip()
                if value:  # Only include non-empty values
                    ui_values[key] = value
                    # Update the last used value when user actually uses it
                    self.set_last_used_value(key, value)
        
        return ui_values

    def save_history(self):
        """
        Save the history cache to disk with last used values prioritized at the top.
        """
        history_to_save = {}

        last_used_map = {
            "artist": getattr(self.gui, "last_artist", None) if self.gui else None,
            "venue": getattr(self.gui, "last_venue", None) if self.gui else None,
            "city": getattr(self.gui, "last_city", None) if self.gui else None,
            "add": getattr(self.gui, "last_add", None) if self.gui else None,
            "source": getattr(self.gui, "last_source", None) if self.gui else None,
            "format": getattr(self.gui, "last_format", None) if self.gui else None,
            "genre": getattr(self.gui, "last_genre", None) if self.gui else None,
        }

        for key, last_used_value in last_used_map.items():
            values = list(self.histories.get(key, []))

            if last_used_value and last_used_value.strip():
                last_used_value = last_used_value.strip()
            else:
                last_used_value = None

            if last_used_value and last_used_value in values:
                values.remove(last_used_value)
                ordered_values = [last_used_value] + sorted(values, key=str.lower)
            else:
                ordered_values = sorted(values, key=str.lower)

            history_to_save[key] = ordered_values

        try:
            history_file_path = Path(HISTORY_FILE)
            os.makedirs(history_file_path.parent, exist_ok=True)
            with open(history_file_path, "w", encoding="utf-8") as f:
                json.dump(history_to_save, f, indent=2, ensure_ascii=False)
            self.log("Saved history with last used values prioritized on top.", level="info")
        except Exception as e:
            self.log(f"Failed to save history: {e}", level="error")

    def load_used_cache(self):
        loaded_cache = load_used_cache(log_func=self.log)
        if loaded_cache:
            self.used_cache.clear()
            self.used_cache.update(loaded_cache)
        self.log("Used cache loaded.", level="debug")

    def save_used_cache(self):
        save_used_cache(self.used_cache, log_func=self.log)

    def update_used_cache_with_ui(self):
        if not self.gui:
            self.log("No GUI instance provided for updating used cache.", level="warning")
            return
        try:
            artist_widget = getattr(self.gui, "artist", None)
            genre_widget = getattr(self.gui, "genre", None)
            if artist_widget and genre_widget:
                artist_val = artist_widget.get().strip()
                genre_val = genre_widget.get().strip()
                update_used_cache(self.used_cache, artist_val, genre_val, log_func=self.log)
                self.log("Used cache updated from UI values.", level="debug")
        except Exception as e:
            self.log(f"[ERROR] Failed to update used cache from UI: {e}", level="error")


# Aliases for backward compatibility or expected import names
load_dropdown_cache = load_history
save_dropdown_cache = save_history