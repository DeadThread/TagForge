import os
import re
from datetime import datetime
from utils.match_folder import match_folder
from utils.txt_parser import TxtMetadataParser  # ✅ Import the parser class
import tkinter as tk
from tkinter import ttk  # Import ttk for Treeview


def handle_tree_selection(self, event=None):
    """
    Called when user selects a folder in the treeview.
    Parses folder name metadata and .txt metadata,
    updates GUI fields (artist, venue, city, date, source, format, genre, additional),
    updates combobox dropdown lists, and sets audio player track titles if available.
    """

    def update_dropdown(combo, var, value):
        """
        Update a combobox and linked StringVar with a new value.
        Clears if empty. Adds new value to combobox list if missing.
        """
        if not value:
            combo.set("")
            var.set("")
            return

        combo.set(value)
        var.set(value)

        # Add to dropdown list if new (case-sensitive)
        current_values = list(combo['values'])
        if value not in current_values:
            combo['values'] = current_values + [value]

    def try_parse_date(date_str):
        """
        Attempt to parse various common date string formats.
        Returns date in YYYY-MM-DD or None if parsing fails.
        """
        if not date_str:
            return None
        formats = [
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%m/%d/%Y",
            "%d %B %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
            except Exception:
                continue
        return None

    selected = self.tree.selection()
    if not selected:
        return

    node = selected[0]
    folder_path = self.tree.item(node, "values")[0]
    folder_name = os.path.basename(folder_path)
    self.current = folder_path

    # --- 1. Folder name inference metadata ---
    md = match_folder(
        folder_name,
        normalized_artists=self.artists_list,
        normalized_venues=self.venues_list,
        normalized_cities=self.cities_list,
        log=self.log_message
    )
    self.log_message(f"[DEBUG] Folder name parsed metadata: {md}", level="debug")

    # --- 2. .txt metadata parsing ---
    parser = TxtMetadataParser(
        artists_list=self.artists_list,
        venues_list=self.venues_list,
        cities_list=self.cities_list
    )
    txt_md = parser.parse(folder_path, log_func=self.log_message)
    self.log_message(f"[DEBUG] TXT metadata parsed: {txt_md}", level="debug")

    # Override md keys with .txt metadata if present
    for key in ('artist', 'venue', 'city', 'date', 'source'):
        if txt_md.get(key):
            md[key] = txt_md[key]

    # --- 3. Merge + normalize date ---
    parsed_date = try_parse_date(txt_md.get("date") or txt_md.get("release date")) or try_parse_date(md.get("date"))
    if parsed_date:
        md["date"] = parsed_date

    # --- 3.5 fallback source from folder name tokens ---
    if not md.get("source"):
        match = re.search(r"\b(aud|sbd|fm|dsbd|mtx|matrix)\b", folder_name.lower())
        if match:
            md["source"] = match.group(1).upper()
            self.log_message(f"[DEBUG] Set source from folder name token: {md['source']}", level="debug")

    # --- 4. Clear current metadata GUI fields (except genre/source/format) ---
    self.artist.set("")
    self.venue.set("")
    self.city.set("")
    self.add.set("")

    # --- 5. Prepare final values for each metadata field ---
    artist_val = md.get("artist", "")
    venue_val = md.get("venue", "")
    city_val = md.get("city", "")
    add_val = md.get("add", "") or md.get("additional", "")

    # For genre, source, format, use new metadata if present, else keep current GUI value (last used)
    genre_val = md.get("genre") or self.genre.get()
    source_val = md.get("source") or self.source.get()
    fmt_val = md.get("format") or self.fmt.get()

    # --- 6. Update the GUI comboboxes and StringVars ---
    update_dropdown(self.c_art, self.artist, artist_val)
    update_dropdown(self.c_ven, self.venue, venue_val)
    update_dropdown(self.c_city, self.city, city_val)
    update_dropdown(self.c_src, self.source, source_val)
    update_dropdown(self.c_fmt, self.fmt, fmt_val)
    update_dropdown(self.c_gen, self.genre, genre_val)
    self.add.set(add_val)

    # --- 7. Update date controls ---
    if md.get("date"):
        try:
            dt_obj = datetime.strptime(md["date"], "%Y-%m-%d")
            self.year.set(str(dt_obj.year))
            self.mo.set(f"{dt_obj.month:02d}")
            self.da.set(f"{dt_obj.day:02d}")
        except Exception:
            self.year.set("")
            self.mo.set("")
            self.da.set("")
    else:
        self.year.set("")
        self.mo.set("")
        self.da.set("")

    # --- 8. Genre fallback from used_cache for artist if genre missing ---
    artist_val_current = self.artist.get()
    if artist_val_current and hasattr(self, 'used_cache'):
        artists_dict = self.used_cache.get("artists", {})
        if isinstance(artists_dict, dict) and artist_val_current in artists_dict:
            cached_genre = artists_dict[artist_val_current]
            if cached_genre:
                self.genre.set(cached_genre)

    # --- 9. Send track titles to audio player if available ---
    if hasattr(self, 'audio_player') and callable(getattr(self.audio_player, 'set_track_titles', None)):
        if txt_md.get("tracks"):
            self.audio_player.set_track_titles(txt_md["tracks"])


def populate_tree(tree: ttk.Treeview, log: tk.Text, root_path: str):
    """Clear and populate the treeview starting from root_path."""
    tree.delete(*tree.get_children())
    top = tree.insert("", tk.END, text=os.path.basename(root_path), open=True, values=(root_path,))
    add_children(tree, log, top, root_path)


def add_children(tree: ttk.Treeview, log: tk.Text, parent, path: str):
    """Add child nodes for directories under `path` to the given parent in the tree."""
    try:
        for name in sorted(os.listdir(path), key=str.lower):
            full_path = os.path.join(path, name)
            if os.path.isdir(full_path):
                node = tree.insert(parent, tk.END, text=name, values=(full_path,))
                # Add dummy child for lazy loading if directory has subdirectories
                try:
                    if any(os.path.isdir(os.path.join(full_path, d)) for d in os.listdir(full_path)):
                        tree.insert(node, tk.END, text="...", values=("dummy",))
                except Exception:
                    # Permission errors or others; skip silently
                    pass
    except Exception as e:
        if log:
            log.insert(tk.END, f"Error building tree: {e}\n")
            log.see(tk.END)


def on_tree_open(tree: ttk.Treeview, log: tk.Text, event=None):
    """Event handler for when a tree node is expanded; loads children lazily."""
    nid = tree.focus()
    children = tree.get_children(nid)
    if children and tree.item(children[0], "values")[0] == "dummy":
        tree.delete(children[0])
        path = tree.item(nid, "values")[0]
        add_children(tree, log, nid, path)
