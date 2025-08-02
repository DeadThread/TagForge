import os
import re
from datetime import datetime
from utils.match_folder import match_folder
from utils.txt_parser import TxtMetadataParser
from utils.constants import DEFAULTS
import tkinter as tk
from tkinter import ttk
import mutagen  # Make sure mutagen is installed: pip install mutagen


def handle_tree_selection(self, event=None):
    def update_dropdown(combo, var, value):
        if not value:
            combo.set("")
            var.set("")
            return
        combo.set(value)
        var.set(value)
        current_values = list(combo['values'])
        if value not in current_values:
            combo['values'] = current_values + [value]

    def try_parse_date(text):
        if not text:
            return None
        date_formats = [
            "%Y-%m-%d", "%Y%m%d", "%m/%d/%Y", "%d %b %Y",
            "%b %d, %Y", "%B %d, %Y",
        ]
        date_regex = re.compile(r"\b(\d{4}[-/]?\d{2}[-/]?\d{2})\b")
        match = date_regex.search(text)
        if match:
            candidate = match.group(1).replace("/", "-")
            for fmt in date_formats:
                try:
                    return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d")
                except Exception:
                    continue
        for fmt in date_formats:
            try:
                dt = datetime.strptime(text.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue
        return None

    def parse_album_flexible(album_str, venues_list, cities_list):
        result = {"date": "", "venue": "", "city": "", "source": "", "format": ""}
        if not album_str:
            return result

        # Normalize date string: replace dots with dashes
        album_str_norm = album_str.replace('.', '-')

        # Try to extract date anywhere in string (improved)
        date = None
        date_formats = [
            "%Y-%m-%d", "%Y%m%d", "%m/%d/%Y", "%d %b %Y",
            "%b %d, %Y", "%B %d, %Y",
        ]
        date_regex = re.compile(r"\b(\d{4}[-/]?\d{2}[-/]?\d{2})\b")
        match = date_regex.search(album_str_norm)
        if match:
            candidate = match.group(1).replace("/", "-")
            for fmt in date_formats:
                try:
                    date = datetime.strptime(candidate, fmt).strftime("%Y-%m-%d")
                    break
                except Exception:
                    continue
        result["date"] = date or ""

        venues_norm = {v.lower(): v for v in venues_list}
        cities_norm = {c.lower(): c for c in cities_list}

        album_lower = album_str.lower()
        # Find city by substring match (case-insensitive)
        for city in cities_list:
            if city.lower() in album_lower:
                result["city"] = city
                break

        # Find venue by substring match (case-insensitive), skip if equal to city
        for venue in venues_list:
            if venue.lower() in album_lower:
                if result["city"] and venue.lower() == result["city"].lower():
                    continue
                result["venue"] = venue
                break

        # Match source and format using DEFAULTS (case-insensitive)
        lowered = album_str.lower()
        for src in DEFAULTS["source"]:
            if src.lower() in lowered:
                result["source"] = src
                break
        for fmt in DEFAULTS["format"]:
            if fmt.lower() in lowered:
                result["format"] = fmt
                break

        return result

    def parse_tags_from_folder(folder_path):
        tags = {}
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.flac', '.mp3', '.m4a', '.wav', '.ogg')):
                    file_path = os.path.join(root, file)
                    try:
                        audio = mutagen.File(file_path, easy=True)
                        if audio:
                            for tag_key in ['artist', 'albumartist', 'album', 'date', 'genre', 'comment']:
                                if tag_key in audio and audio[tag_key]:
                                    tags[tag_key] = audio[tag_key][0]
                            return tags
                    except Exception:
                        continue
        return tags

    selected = self.tree.selection()
    if not selected:
        return

    node = selected[0]
    folder_path = self.tree.item(node, "values")[0]
    folder_name = os.path.basename(folder_path)
    self.current = folder_path

    file_tags = parse_tags_from_folder(folder_path)
    self.log_message(f"[DEBUG] Parsed file tags from folder: {file_tags}", level="debug")

    album_val = file_tags.get("album", "").strip()
    album_parsed = parse_album_flexible(album_val, self.venues_list, self.cities_list)
    self.log_message(f"[DEBUG] Parsed album flexibly: {album_parsed}", level="debug")

    md = {
        "artist": file_tags.get("artist") or file_tags.get("albumartist") or "",
        "venue": album_parsed.get("venue") or "",
        "city": album_parsed.get("city") or "",
        "date": album_parsed.get("date") or file_tags.get("date") or "",
        "source": album_parsed.get("source") or "",
        "format": album_parsed.get("format") or "",
        "genre": file_tags.get("genre") or "",
        "add": "",
        "additional": "",
    }

    folder_md = match_folder(
        folder_name,
        normalized_artists=self.artists_list,
        normalized_venues=self.venues_list,
        normalized_cities=self.cities_list,
        log=self.log_message
    )
    self.log_message(f"[DEBUG] Folder name parsed metadata: {folder_md}", level="debug")

    for key in ['artist', 'venue', 'city', 'date', 'source', 'format', 'genre', 'add', 'additional']:
        # Only update if md[key] is empty or not valid in DEFAULTS for source/format
        if key in ("source", "format"):
            val = md.get(key)
            if not val or val.upper() not in [x.upper() for x in DEFAULTS[key]]:
                if folder_md.get(key) and folder_md[key].upper() in [x.upper() for x in DEFAULTS[key]]:
                    md[key] = folder_md[key]
        else:
            if not md.get(key) and folder_md.get(key):
                md[key] = folder_md[key]

    parser = TxtMetadataParser(
        artists_list=self.artists_list,
        venues_list=self.venues_list,
        cities_list=self.cities_list
    )
    txt_md = parser.parse(folder_path, log_func=self.log_message)
    self.log_message(f"[DEBUG] TXT metadata parsed: {txt_md}", level="debug")

    for key in ('artist', 'venue', 'city', 'date', 'source', 'format'):
        if key in ("source", "format"):
            val = md.get(key)
            # Only update if current md[key] is missing or invalid
            txt_val = txt_md.get(key)
            if txt_val and txt_val.upper() in [x.upper() for x in DEFAULTS[key]]:
                md[key] = txt_val
        else:
            if txt_md.get(key):
                md[key] = txt_md[key]

    # Improved date selection logic:
    candidate_dates = []

    # From txt metadata
    txt_date = txt_md.get("date") or txt_md.get("release date")
    if txt_date:
        candidate_dates.append(txt_date)

    # From folder metadata
    folder_date = folder_md.get("date")
    if folder_date:
        candidate_dates.append(folder_date)

    # From album_parsed
    album_date = album_parsed.get("date")
    if album_date:
        candidate_dates.append(album_date)

    # From file tags
    filetag_date = file_tags.get("date")
    if filetag_date:
        candidate_dates.append(filetag_date)

    def normalize_date(d):
        if not d:
            return None
        try:
            dt = datetime.strptime(d.strip(), "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        formats = ["%Y%m%d", "%m/%d/%Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%Y"]
        for fmt in formats:
            try:
                dt = datetime.strptime(d.strip(), fmt)
                if fmt == "%Y":
                    return dt.strftime("%Y-01-01")
                return dt.strftime("%Y-%m-%d")
            except Exception:
                continue
        return None

    selected_date = None
    for cd in candidate_dates:
        nd = normalize_date(cd)
        if nd and not nd.endswith("-01-01"):  # exclude year-only fallback
            selected_date = nd
            break
    if not selected_date:
        for cd in candidate_dates:
            nd = normalize_date(cd)
            if nd:
                selected_date = nd
                break

    if selected_date:
        md["date"] = selected_date

    # If still no source, try regex match from folder name and ensure it is in DEFAULTS["source"]
    if not md.get("source"):
        match = re.search(r"\b(aud|sbd|fm|dsbd|mtx|matrix)\b", folder_name.lower())
        if match:
            candidate = match.group(1).upper()
            if candidate in DEFAULTS["source"]:
                md["source"] = candidate
                self.log_message(f"[DEBUG] Set source from folder name token: {md['source']}", level="debug")

    self.artist.set("")
    self.venue.set("")
    self.city.set("")
    self.add.set("")

    artist_val = md.get("artist", "")
    venue_val = md.get("venue", "")
    city_val = md.get("city", "")
    add_val = md.get("add", "") or md.get("additional", "")

    genre_val = md.get("genre") or self.genre.get()
    source_val = md.get("source") or self.source.get()
    fmt_val = md.get("format") or self.fmt.get()

    update_dropdown(self.c_art, self.artist, artist_val)
    update_dropdown(self.c_ven, self.venue, venue_val)
    update_dropdown(self.c_city, self.city, city_val)
    update_dropdown(self.c_src, self.source, source_val)
    update_dropdown(self.c_fmt, self.fmt, fmt_val)
    update_dropdown(self.c_gen, self.genre, genre_val)
    self.add.set(add_val)

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

    artist_val_current = self.artist.get()
    if artist_val_current and hasattr(self, 'used_cache'):
        artists_dict = self.used_cache.get("artists", {})
        if isinstance(artists_dict, dict) and artist_val_current in artists_dict:
            cached_genre = artists_dict[artist_val_current]
            if cached_genre:
                self.genre.set(cached_genre)

    if hasattr(self, 'audio_player') and callable(getattr(self.audio_player, 'set_track_titles', None)):
        if txt_md.get("tracks"):
            self.audio_player.set_track_titles(txt_md["tracks"])


def populate_tree(tree: ttk.Treeview, log: tk.Text, root_path: str):
    tree.delete(*tree.get_children())
    top = tree.insert("", tk.END, text=os.path.basename(root_path), open=True, values=(root_path,))
    add_children(tree, log, top, root_path)


def add_children(tree: ttk.Treeview, log: tk.Text, parent, path: str):
    try:
        for name in sorted(os.listdir(path), key=str.lower):
            full_path = os.path.join(path, name)
            if os.path.isdir(full_path):
                node = tree.insert(parent, tk.END, text=name, values=(full_path,))
                try:
                    if any(os.path.isdir(os.path.join(full_path, d)) for d in os.listdir(full_path)):
                        tree.insert(node, tk.END, text="...", values=("dummy",))
                except Exception:
                    pass
    except Exception as e:
        if log:
            log.insert(tk.END, f"Error building tree: {e}\n")
            log.see(tk.END)


def on_tree_open(tree: ttk.Treeview, log: tk.Text, event=None):
    nid = tree.focus()
    children = tree.get_children(nid)
    if children and tree.item(children[0], "values")[0] == "dummy":
        tree.delete(children[0])
        path = tree.item(nid, "values")[0]
        add_children(tree, log, nid, path)
