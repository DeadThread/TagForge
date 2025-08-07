import os
import re
import shutil
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3 as MP3
import threading
from datetime import datetime

HISTORY_FILE = "history_cache.json"

patterns = [
    (
        re.compile(
            r'^(?P<date>\d{4}-\d{2}-\d{2})\s*-\s*(?P<venue>.+?)\s*-\s*(?P<city>.+?)\s*(\[(?P<id>.+?)\])?.*$',
            re.IGNORECASE
        ),
        ["date", "venue", "city", "id"]
    ),
    (
        re.compile(
            r'^(?P<artist>.+?)\s*-\s*(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<venue>[^,]+),\s+(?P<city>[^\[\]]+)(\s*\[(?P<id>.+?)\])?$',
            re.IGNORECASE
        ),
        ["artist", "date", "venue", "city", "id"]
    ),
    (
        re.compile(
            r'^(?P<artist>.+?)\s+(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<venue>.+?),\s+(?P<city>[^\[\]]+?)(?:\.(?P<format>\w+))?$',
            re.IGNORECASE
        ),
        ["artist", "date", "venue", "city", "format"]
    ),
]

date_regexes = [
    re.compile(r'\d{4}-\d{2}-\d{2}'),
    re.compile(r'\d{2}-\d{2}-\d{4}'),
    re.compile(r'\d{2}-\d{2}-\d{2}')
]

def extract_date(text):
    for regex in date_regexes:
        m = regex.search(text)
        if m:
            return m.group(0)
    return ""

def extract_city(text):
    m = re.search(r'([A-Za-z\s\.]+,\s*[A-Z]{2})', text)
    if m:
        return m.group(1).strip()
    return ""

def extract_format(text):
    m = re.search(r'\[(FLAC16|FLAC24|FLAC|MP3-V0|MP3-320|MP3-256|MP3-128|MP3)\]', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m2 = re.search(r'\.(flac16|flac24|flac|mp3v0|mp3320|mp3256|mp3128|mp3)$', text, re.IGNORECASE)
    if m2:
        return m2.group(1).upper()
    return ""

def extract_source(text):
    m = re.search(r'\[(SBD|AUD)\]', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return ""

def extract_id(text):
    m = re.search(r'\[([^\]]+)\]$', text)
    if m:
        val = m.group(1)
        if val.upper() not in ["SBD", "AUD", "FLAC16", "FLAC24", "FLAC", "MP3-V0", "MP3-320", "MP3-256", "MP3-128", "MP3"]:
            return val
    return ""

def match_folder(folder_name):
    info = {
        "artist": "",
        "date": "",
        "venue": "",
        "city": "",
        "id": "",
        "source": "",
        "format": "",
        "genre": ""
    }
    for pattern, groups in patterns:
        m = pattern.match(folder_name)
        if m:
            for g in groups:
                val = m.group(g)
                info[g] = val.strip() if val else ""
            break

    if not info["date"]:
        info["date"] = extract_date(folder_name)
    if not info["city"]:
        info["city"] = extract_city(folder_name)
    if not info["format"]:
        info["format"] = extract_format(folder_name)
    if not info["source"]:
        info["source"] = extract_source(folder_name)
    if not info["id"]:
        info["id"] = extract_id(folder_name)

    return info

def retag_file(filepath, artist, album, date, venue, city, genres, source, fmt, log):
    try:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".flac":
            audio = FLAC(filepath)
        elif ext == ".mp3":
            audio = MP3(filepath)
        else:
            return

        audio["artist"] = artist
        audio["album"] = album
        audio["date"] = date
        audio["venue"] = venue
        audio["location"] = city.strip()
        # Write genres as semicolon separated
        if genres:
            existing = set()
            genre_list = []
            for g in genres:
                if g and g.lower() not in existing:
                    genre_list.append(g)
                    existing.add(g.lower())
            audio["genre"] = "; ".join(genre_list)
        else:
            audio["genre"] = ""

        if source:
            audio["source"] = source
        if fmt:
            audio["comment"] = fmt
        audio.save()
        log.insert(tk.END, f"  Tagged: {os.path.basename(filepath)}\n")
        log.see(tk.END)

    except Exception as e:
        log.insert(tk.END, f"  Failed to tag {filepath}: {e}\n")
        log.see(tk.END)

class WalkThroughGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TagForge")
        self.root.geometry("1200x700")
        self.current_selection = None
        self.saved_folders = []
        self.folder_metadata = {}

        self.last_source = ""
        self.last_format = ""
        self.last_genre = ""

        self.root_folder_var = tk.StringVar()

        self.artist_history = set()
        self.venue_history = set()
        self.city_history = set()
        self.additional_history = set()
        self.source_history = set()
        self.format_history = set()
        self.genre_history = set()

        self.create_widgets()

        try:
            root.tk.call("source", "azure.tcl")
            root.tk.call("set_theme", "dark")
        except tk.TclError:
            pass

        self.load_history_cache()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        top_frame = tk.Frame(self.root, pady=5)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="Root Folder:").pack(side=tk.LEFT, padx=5)
        self.root_entry = tk.Entry(top_frame, textvariable=self.root_folder_var, width=60, state="readonly")
        self.root_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Browse Root Folder", command=self.browse_root).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Refresh Tree", command=self.refresh_tree).pack(side=tk.LEFT, padx=5)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame, padx=5, pady=5)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        right_frame = tk.Frame(main_frame, padx=10, pady=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Folder tree
        tk.Label(left_frame, text="Folders:").pack(anchor="w")
        self.tree = ttk.Treeview(left_frame)
        self.tree.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        yscroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        yscroll.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree["columns"] = ("fullpath",)
        self.tree.column("#0", width=300, anchor="w")
        self.tree.column("fullpath", width=0, stretch=False)
        self.tree.heading("#0", text="Folder")
        self.tree.heading("fullpath", text="Full Path")

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)

        middle_frame = tk.Frame(left_frame)
        middle_frame.pack(fill=tk.X, pady=10)

        # Editable comboboxes for user fields

        tk.Label(middle_frame, text="Artist:").grid(row=0, column=0, sticky="w")
        self.artist_var = tk.StringVar()
        self.artist_combo = ttk.Combobox(middle_frame, textvariable=self.artist_var, width=30)
        self.artist_combo['values'] = sorted(self.artist_history)
        self.artist_combo.grid(row=0, column=1, sticky="w", padx=5)

        tk.Label(middle_frame, text="Source:").grid(row=0, column=2, sticky="w")
        self.source_var = tk.StringVar()
        self.source_combo = ttk.Combobox(middle_frame, textvariable=self.source_var,
                                         values=["", "SBD", "AUD"], width=10)
        self.source_combo.grid(row=0, column=3, sticky="w", padx=5)
        self.source_combo.config(state="normal")  # Editable

        tk.Label(middle_frame, text="Format:").grid(row=0, column=4, sticky="w")
        self.format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(middle_frame, textvariable=self.format_var,
                                         values=["", "FLAC16", "FLAC24", "MP3-V0", "MP3-320", "MP3-256", "MP3-128"], width=10)
        self.format_combo.grid(row=0, column=5, sticky="w", padx=5)
        self.format_combo.config(state="normal")  # Editable

        tk.Label(middle_frame, text="Genre(s):").grid(row=1, column=0, sticky="w")
        self.genre_var = tk.StringVar()
        self.genre_combo = ttk.Combobox(middle_frame, textvariable=self.genre_var, width=30)
        self.genre_combo['values'] = sorted(self.genre_history)
        self.genre_combo.grid(row=1, column=1, sticky="w", padx=5, pady=(5, 0))

        tk.Label(middle_frame, text="Date:").grid(row=1, column=2, sticky="w", padx=(10, 0))
        date_frame = tk.Frame(middle_frame)
        date_frame.grid(row=1, column=3, sticky="w", padx=5, pady=(5, 0))

        self.year_var = tk.StringVar()
        self.month_var = tk.StringVar()
        self.day_var = tk.StringVar()
        current_year = datetime.now().year
        years = [str(y) for y in range(current_year, 1999, -1)]
        self.year_combo = ttk.Combobox(date_frame, textvariable=self.year_var, values=years, width=5, state="normal")
        self.year_combo.grid(row=0, column=0, sticky="w", padx=(0, 1))

        months = [f"{i:02d}" for i in range(1, 13)]
        self.month_combo = ttk.Combobox(date_frame, textvariable=self.month_var, values=months, width=3, state="normal")
        self.month_combo.grid(row=0, column=1, sticky="w", padx=(0, 1))

        days = [f"{i:02d}" for i in range(1, 32)]
        self.day_combo = ttk.Combobox(date_frame, textvariable=self.day_var, values=days, width=3, state="normal")
        self.day_combo.grid(row=0, column=2, sticky="w", padx=(0, 0))

        tk.Label(middle_frame, text="Venue:").grid(row=2, column=0, sticky="w", pady=(5, 0))
        self.venue_var = tk.StringVar()
        self.venue_combo = ttk.Combobox(middle_frame, textvariable=self.venue_var, width=30)
        self.venue_combo['values'] = sorted(self.venue_history)
        self.venue_combo.grid(row=2, column=1, sticky="w", padx=5, pady=(5, 0))

        tk.Label(middle_frame, text="City:").grid(row=2, column=2, sticky="w", pady=(5, 0))
        self.city_var = tk.StringVar()
        self.city_combo = ttk.Combobox(middle_frame, textvariable=self.city_var, width=20)
        self.city_combo['values'] = sorted(self.city_history)
        self.city_combo.grid(row=2, column=3, sticky="w", padx=5, pady=(5, 0))

        tk.Label(middle_frame, text="Additional:").grid(row=2, column=4, sticky="w", pady=(5, 0))
        self.additional_var = tk.StringVar()
        self.additional_combo = ttk.Combobox(middle_frame, textvariable=self.additional_var, width=15)
        self.additional_combo['values'] = sorted(self.additional_history)
        self.additional_combo.grid(row=2, column=5, sticky="w", padx=5, pady=(5, 0))

        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(btn_frame, text="Save Selected Folder", command=self.save_selected_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Remove Selected Folder", command=self.remove_selected_folder).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Process All Saved Folders", command=self.process_all_saved_folders).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear Fields", command=self.clear_fields).pack(side=tk.LEFT, padx=5)

        tk.Label(left_frame, text="Folders to Process:").pack(anchor="w")
        self.saved_listbox = tk.Listbox(left_frame, height=10)
        self.saved_listbox.pack(fill=tk.X, pady=5)

        tk.Label(right_frame, text="Log:").pack(anchor="w")
        self.log = tk.Text(right_frame, wrap=tk.NONE)
        self.log.pack(fill=tk.BOTH, expand=True)
        log_scroll_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.log.yview)
        log_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.log.configure(yscrollcommand=log_scroll_y.set)

    def jump_to_value(self, combo, key):
        if not key.isdigit():
            return
        values = combo.cget("values")
        for val in values:
            if val.startswith(key):
                combo.set(val)
                break

    def browse_root(self):
        folder = filedialog.askdirectory()
        if folder:
            self.root_folder_var.set(folder)
            self.populate_tree(folder)

    def refresh_tree(self):
        folder = self.root_folder_var.get()
        if folder and os.path.isdir(folder):
            self.populate_tree(folder)

    def populate_tree(self, root_folder):
        self.tree.delete(*self.tree.get_children())
        root_node = self.tree.insert("", tk.END, text=os.path.basename(root_folder), open=True, values=(root_folder,))
        self.insert_subfolders(root_node, root_folder)

    def insert_subfolders(self, parent, folder_path):
        try:
            entries = sorted(os.listdir(folder_path), key=lambda s: s.lower())
            for entry in entries:
                full_path = os.path.join(folder_path, entry)
                if os.path.isdir(full_path):
                    # Only add children if subfolders exist to avoid unnecessary expansion
                    children = [f for f in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, f))]
                    has_children = len(children) > 0
                    node = self.tree.insert(parent, tk.END, text=entry, values=(full_path,), open=False)
                    if has_children:
                        # Add a dummy child to make this node expandable
                        self.tree.insert(node, tk.END, text="Loading...", values=("dummy",))
        except Exception as e:
            self.log.insert(tk.END, f"Error reading folder {folder_path}: {e}\n")
            self.log.see(tk.END)

    def on_tree_expand(self, event):
        node = self.tree.focus()
        children = self.tree.get_children(node)
        # If first child is dummy, remove and populate real children
        if children:
            first_child = children[0]
            if self.tree.item(first_child, "values")[0] == "dummy":
                self.tree.delete(first_child)
                folder_path = self.tree.item(node, "values")[0]
                self.insert_subfolders(node, folder_path)

    def on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        folder_path = self.tree.item(sel[0], "values")[0]
        if not os.path.isdir(folder_path):
            return
        self.current_selection = folder_path

        folder_name = os.path.basename(folder_path)
        info = match_folder(folder_name)

        self.artist_var.set(info.get("artist", "") or "")
        d = info.get("date", "") or ""
        if d and len(d) == 10 and d[4] == "-" and d[7] == "-":
            y, m, day = d.split("-")
            self.year_var.set(y)
            self.month_var.set(m)
            self.day_var.set(day)
        else:
            self.year_var.set("")
            self.month_var.set("")
            self.day_var.set("")
        self.venue_var.set(info.get("venue", "") or "")
        self.city_var.set(info.get("city", "") or "")
        self.additional_var.set(info.get("id", "") or "")

        genre = info.get("genre", "") or self.last_genre
        self.genre_var.set(genre)

        source = info.get("source", "") or self.last_source
        format_ = info.get("format", "") or self.last_format

        self.source_var.set(source)
        self.format_var.set(format_)

    def save_selected_folder(self):
        if not self.current_selection:
            messagebox.showwarning("No Selection", "Please select a folder from the tree.")
            return

        artist = self.artist_var.get().strip()
        venue = self.venue_var.get().strip()
        city = self.city_var.get().strip()
        additional = self.additional_var.get().strip()
        source = self.source_var.get().strip()
        format_ = self.format_var.get().strip()
        genre = self.genre_var.get().strip()

        year = self.year_var.get().strip()
        month = self.month_var.get().strip()
        day = self.day_var.get().strip()
        date = ""
        if year and month and day:
            try:
                date = f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
            except ValueError:
                date = ""

        if not artist or not date or not venue:
            messagebox.showwarning("Missing Data", "Artist, Date and Venue are required fields.")
            return

        folder_path = self.current_selection

        if folder_path not in self.saved_folders:
            self.saved_folders.append(folder_path)
            self.saved_listbox.insert(tk.END, folder_path)

        self.folder_metadata[folder_path] = {
            "artist": artist,
            "venue": venue,
            "city": city,
            "date": date,
            "source": source,
            "format": format_,
            "genre": genre,
            "id": additional
        }

        self.last_source = source
        self.last_format = format_
        self.last_genre = genre

        self.artist_history.add(artist)
        self.venue_history.add(venue)
        self.city_history.add(city)
        self.additional_history.add(additional)
        self.source_history.add(source)
        self.format_history.add(format_)
        self.genre_history.add(genre)

        self.artist_combo['values'] = sorted(self.artist_history)
        self.venue_combo['values'] = sorted(self.venue_history)
        self.city_combo['values'] = sorted(self.city_history)
        self.additional_combo['values'] = sorted(self.additional_history)
        self.source_combo['values'] = sorted(self.source_history.union({"", "SBD", "AUD"}))
        self.format_combo['values'] = sorted(self.format_history.union({"", "FLAC16", "FLAC24", "MP3-V0", "MP3-320", "MP3-256", "MP3-128"}))
        self.genre_combo['values'] = sorted(self.genre_history)

        self.log.insert(tk.END, f"Saved folder for future processing: {folder_path}\n")
        self.log.see(tk.END)

    def remove_selected_folder(self):
        selection = self.saved_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a folder from the list.")
            return
        idx = selection[0]
        folder = self.saved_listbox.get(idx)
        if folder in self.saved_folders:
            self.saved_folders.remove(folder)
        if folder in self.folder_metadata:
            del self.folder_metadata[folder]
        self.saved_listbox.delete(idx)

    def clear_fields(self):
        self.artist_var.set("")
        self.venue_var.set("")
        self.city_var.set("")
        self.additional_var.set("")
        self.source_var.set(self.last_source)
        self.format_var.set(self.last_format)
        self.genre_var.set(self.last_genre)
        self.year_var.set("")
        self.month_var.set("")
        self.day_var.set("")

    def process_all_saved_folders(self):
        if not self.saved_folders:
            messagebox.showinfo("No folders", "No folders to process.")
            return
        
        save_root = self.root_folder_var.get()
        if not save_root or not os.path.isdir(save_root):
            messagebox.showerror("Error", "Please select a valid root folder before processing.")
            return

        threading.Thread(target=self._process_folders_thread, args=(save_root,), daemon=True).start()

    def _process_folders_thread(self, save_root):
        for folder in self.saved_folders:
            self.log.insert(tk.END, f"Processing folder:\n  {folder}\n")
            self.log.see(tk.END)

            md = self.folder_metadata.get(folder, {})
            artist = md.get("artist", "")
            venue = md.get("venue", "")
            city = md.get("city", "")
            date = md.get("date", "")
            source = md.get("source", "")
            format_ = md.get("format", "")
            genre = md.get("genre", "")
            additional = md.get("id", "")

            year = date.split("-")[0] if date else "UnknownYear"
            name_parts = [date, venue]
            if city:
                name_parts.append(city)
            folder_name = " - ".join(name_parts)
            tags = []
            if source:
                tags.append(f"[{source}]")
            if format_:
                tags.append(f"[{format_}]")
            if additional:
                tags.append(f"[{additional}]")
            folder_name += " " + " ".join(tags) if tags else ""

            new_folder_path = os.path.join(save_root, artist, year, folder_name)
            os.makedirs(os.path.join(save_root, artist, year), exist_ok=True)

            try:
                shutil.move(folder, new_folder_path)
                self.log.insert(tk.END, f"Moved folder:\n  {folder}\n  -> {new_folder_path}\n")
                self.log.see(tk.END)
            except Exception as e:
                self.log.insert(tk.END, f"Failed to move folder {folder}: {e}\n")
                self.log.see(tk.END)
                continue

            # Now retag all audio files inside moved folder
            for rootdir, _, files in os.walk(new_folder_path):
                for file in files:
                    filepath = os.path.join(rootdir, file)
                    retag_file(filepath, artist, folder_name, date, venue, city, [genre], source, format_, self.log)

            self.log.insert(tk.END, f"Completed processing: {new_folder_path}\n\n")
            self.log.see(tk.END)

        messagebox.showinfo("Processing Complete", "Finished processing all saved folders.")
        self.saved_folders.clear()
        self.saved_listbox.delete(0, tk.END)

    def load_history_cache(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.artist_history = set(data.get("artist_history", []))
                self.venue_history = set(data.get("venue_history", []))
                self.city_history = set(data.get("city_history", []))
                self.additional_history = set(data.get("additional_history", []))
                self.source_history = set(data.get("source_history", []))
                self.format_history = set(data.get("format_history", []))
                self.genre_history = set(data.get("genre_history", []))
                self.last_source = data.get("last_source", "")
                self.last_format = data.get("last_format", "")
                self.last_genre = data.get("last_genre", "")
            except Exception as e:
                self.log.insert(tk.END, f"Error loading history cache: {e}\n")
                self.log.see(tk.END)
        else:
            # Default source and format sets to ensure they appear in dropdowns
            self.source_history.update({"", "SBD", "AUD"})
            self.format_history.update({"", "FLAC16", "FLAC24", "MP3-V0", "MP3-320", "MP3-256", "MP3-128"})

        # Update dropdown values after loading
        self.artist_combo['values'] = sorted(self.artist_history)
        self.venue_combo['values'] = sorted(self.venue_history)
        self.city_combo['values'] = sorted(self.city_history)
        self.additional_combo['values'] = sorted(self.additional_history)
        self.source_combo['values'] = sorted(self.source_history.union({"", "SBD", "AUD"}))
        self.format_combo['values'] = sorted(self.format_history.union({"", "FLAC16", "FLAC24", "MP3-V0", "MP3-320", "MP3-256", "MP3-128"}))
        self.genre_combo['values'] = sorted(self.genre_history)

        # Set last used for source, format, genre
        self.source_var.set(self.last_source)
        self.format_var.set(self.last_format)
        self.genre_var.set(self.last_genre)

    def save_history_cache(self):
        data = {
            "artist_history": list(self.artist_history),
            "venue_history": list(self.venue_history),
            "city_history": list(self.city_history),
            "additional_history": list(self.additional_history),
            "source_history": list(self.source_history),
            "format_history": list(self.format_history),
            "genre_history": list(self.genre_history),
            "last_source": self.last_source,
            "last_format": self.last_format,
            "last_genre": self.last_genre,
        }
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.log.insert(tk.END, f"Error saving history cache: {e}\n")
            self.log.see(tk.END)

    def on_close(self):
        self.save_history_cache()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    root.iconbitmap(r"M:\Projects\Tagger\Tagger - V1.0 - Stable\assets\TagForge.ico")
    app = WalkThroughGUI(root)
    root.mainloop()

