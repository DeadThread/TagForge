import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path
from utils.constants import DEFAULTS, CONFIG_DIR  # Adjust this import path if needed

HISTORY_FILE = CONFIG_DIR / "history_cache.json"

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def merge_defaults_with_history(default_list, history_list):
    seen = set()
    merged = []
    for item in history_list + default_list:
        if item and item not in seen:
            merged.append(item)
            seen.add(item)
    return merged

class AutocompleteCombobox(ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)

        self._completion_list = []
        self._hits = []
        self._hit_index = 0
        self._ignore_autocomplete = False

        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<FocusOut>', self._reset_state)

    def set_completion_list(self, completion_list):
        self._completion_list = sorted(completion_list, key=str.lower)
        self['values'] = self._completion_list

    def _on_keyrelease(self, event):
        if self._ignore_autocomplete:
            return

        if event.keysym in ("Left", "Right", "Escape", "Return", "Tab", "Up", "Down"):
            return

        text = self.get()

        if text == "":
            self._hit_index = 0
            self['values'] = self._completion_list
            return

        self._hits = [item for item in self._completion_list if item.lower().startswith(text.lower())]

        if self._hits:
            first_hit = self._hits[0]

            if event.keysym not in ("BackSpace", "Delete") and first_hit.lower() != text.lower():
                self._ignore_autocomplete = True
                self.delete(0, tk.END)
                self.insert(0, first_hit)
                self.select_range(len(text), tk.END)
                self.icursor(len(text))
                self._ignore_autocomplete = False

            self['values'] = self._hits
        else:
            self['values'] = ()

    def _reset_state(self, event=None):
        self._hit_index = 0
        self._hits = []
        self._ignore_autocomplete = False

def create_labeled_autocomplete(parent, label_text, default_list, history_list):
    frame = ttk.Frame(parent)
    label = ttk.Label(frame, text=label_text, width=12, anchor="w")
    label.pack(side="left", padx=(0, 5))
    combo = AutocompleteCombobox(frame)
    merged_list = merge_defaults_with_history(default_list, history_list)
    combo.set_completion_list(merged_list)
    combo.pack(side="left", fill="x", expand=True)
    frame.pack(fill="x", padx=10, pady=5)
    return combo

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Metadata Autocomplete Example")
    root.geometry("450x350")

    history = load_history()

    artist_combo = create_labeled_autocomplete(root, "Artist:", DEFAULTS.get("artist", []), history.get("artist", []))
    city_combo = create_labeled_autocomplete(root, "City:", DEFAULTS.get("city", []), history.get("city", []))
    venue_combo = create_labeled_autocomplete(root, "Venue:", DEFAULTS.get("venue", []), history.get("venue", []))
    genre_combo = create_labeled_autocomplete(root, "Genre:", DEFAULTS.get("genre", []), history.get("genre", []))
    source_combo = create_labeled_autocomplete(root, "Source:", DEFAULTS.get("source", []), history.get("source", []))
    add_combo = create_labeled_autocomplete(root, "Additional:", DEFAULTS.get("add", []), history.get("add", []))

    root.mainloop()
