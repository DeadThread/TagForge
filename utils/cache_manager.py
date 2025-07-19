import os
import json
from utils.constants import DEFAULTS, HISTORY_FILE, USED_CACHE_FILE

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
                cleaned = [v for v in vals if v]
                histories[key] = set(cleaned)
                if cleaned and set_last_used_callback:
                    set_last_used_callback(key, cleaned[0])
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

    def load_history(self):
        def set_last_used(key, value):
            if self.gui:
                if key == "source":
                    self.gui.last_source = value
                elif key == "format":
                    self.gui.last_format = value
                elif key == "genre":
                    self.gui.last_genre = value

        load_history(self.histories, set_last_used_callback=set_last_used, log_func=self.log)
        self.log("History loaded.", level="debug")

    def save_history(self):
        last_source = getattr(self.gui, "last_source", "")
        last_format = getattr(self.gui, "last_format", "")
        last_genre = getattr(self.gui, "last_genre", "")

        save_history(self.histories, last_source, last_format, last_genre, log_func=self.log)

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
