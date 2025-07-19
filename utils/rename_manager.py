import tkinter as tk
from tkinter import ttk, filedialog
import mutagen
import re
import os

class RenameManager:
    def __init__(self, parent, audio_player, audio_list, audio_files, log_insert):
        self.parent = parent
        self.audio_player = audio_player  # Ensure the audio player is passed here
        self.audio_list = audio_list
        self.audio_files = audio_files
        self.log_insert = log_insert
        self.rename_window = None
        self.track_titles_txt = []
        self.track_title_entries = []
        self.track_frame = None
        self.canvas = None
        self.total_discs = 1

    def _open_rename_window(self):
        """Open or focus the rename window."""
        if self.rename_window and self.rename_window.winfo_exists():
            self.rename_window.lift()
            self.rename_window.focus_force()
            return

        self.rename_window = tk.Toplevel(self.parent)
        self.rename_window.title("Rename Track Titles")
        self.rename_window.geometry("700x500")

        self.rename_window.wm_attributes("-topmost", 1)
        self.rename_window.after(100, lambda: self.rename_window.attributes("-topmost", 1))

        rename_frame = tk.Frame(self.rename_window, padx=10, pady=10)
        rename_frame.grid(row=0, column=0, sticky="nsew")

        title_label = tk.Label(rename_frame, text="Rename Track Titles", font=("Segoe UI", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        self.track_frame = tk.Frame(rename_frame)
        self.track_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        tk.Label(self.track_frame, text="Track No.", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=15, pady=5)
        tk.Label(self.track_frame, text="Original Name", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=15, pady=5)
        tk.Label(self.track_frame, text="Updated Name", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=15, pady=5)

        self.canvas = tk.Canvas(self.track_frame)
        scrollbar = ttk.Scrollbar(self.track_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        track_list_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=track_list_frame, anchor="nw")
        self.canvas.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        scrollbar.grid(row=1, column=3, sticky="ns")

        self.track_title_entries = []

        track_names = [self.audio_list.item(child)["values"][1] for child in self.audio_list.get_children()]
        track_numbers = [self.audio_list.item(child)["values"][0] for child in self.audio_list.get_children()]

        if not track_names:
            self.log_insert("[ERROR] No tracks available to rename.")
            return

        for i, (track_no, track) in enumerate(zip(track_numbers, track_names)):
            tk.Label(track_list_frame, text=track_no).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            tk.Label(track_list_frame, text=track, anchor="w").grid(row=i, column=1, padx=5, pady=5, sticky="w")

            updated_entry = tk.Entry(track_list_frame, font=("Segoe UI", 10))
            updated_entry.grid(row=i, column=2, padx=5, pady=5, sticky="w")
            updated_entry.insert(0, track)
            self.track_title_entries.append(updated_entry)

        import_button = ttk.Button(self.rename_window, text="Import .txt File", command=self.import_txt_file)
        import_button.grid(row=2, column=0, columnspan=3, pady=10)

        save_button = ttk.Button(self.rename_window, text="Save Changes", command=self.save_changes)
        save_button.grid(row=3, column=0, columnspan=3, pady=10)

        track_list_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

        self.rename_window.grid_rowconfigure(0, weight=1)
        self.rename_window.grid_rowconfigure(1, weight=1)
        self.rename_window.grid_columnconfigure(0, weight=0)
        self.rename_window.grid_columnconfigure(1, weight=1)
        self.rename_window.grid_columnconfigure(2, weight=1)

        self.rename_window.bind("<FocusOut>", self._on_rename_focus_out)
        self.rename_window.bind("<Deactivate>", self._on_rename_deactivate)

    def _close_rename_window(self):
        """Properly close/destroy the rename window."""
        if self.rename_window and self.rename_window.winfo_exists():
            self.rename_window.destroy()
            self.rename_window = None

    def _on_rename_focus_out(self, event):
        self.rename_window.wm_attributes("-topmost", 0)

    def _on_rename_deactivate(self, event):
        self.rename_window.lift()
        self.rename_window.focus_force()

    def import_txt_file(self):
        """Open a file dialog to select a .txt file and load track titles."""
        if self.rename_window and self.rename_window.winfo_exists():
            self.rename_window.withdraw()  # Hide the window only if it exists

        file_path = filedialog.askopenfilename(
            title="Select Tracklist .txt File", filetypes=[("Text Files", "*.txt")]
        )

        if file_path:
            # Load the tracklist from the selected file only (no full audio reload)
            self._load_txt_tracklist(file_path)
            self._update_rename_window()

        if self.rename_window and self.rename_window.winfo_exists():
            self.rename_window.deiconify()
            self.rename_window.lift()
            self.rename_window.focus_force()

    def save_changes(self):
        updated_titles = [entry.get() for entry in self.track_title_entries]

        if len(updated_titles) != len(self.audio_files):
            self.log_insert(f"[ERROR] Track count mismatch: {len(updated_titles)} updated titles vs {len(self.audio_files)} audio files.")
            return

        total_discs = getattr(self, 'total_discs', 1)  # default 1 if not set

        for idx, updated_title in enumerate(updated_titles):
            old_title = self.audio_list.item(self.audio_list.get_children()[idx])["values"][1]

            if old_title != updated_title:
                if idx < len(self.track_titles_txt):
                    disc, track_num, _, _ = self.track_titles_txt[idx]
                else:
                    disc, track_num = 1, idx + 1

                track_number_gui = f"{disc}.{track_num}"

                self.audio_list.item(self.audio_list.get_children()[idx], values=(track_number_gui, updated_title))
                self.log_insert(f"[INFO] Renamed track in GUI: '{old_title}' → '{updated_title}'")

                try:
                    audio_file_path = self.audio_files[idx]
                    audio = mutagen.File(audio_file_path, easy=True)

                    if audio and audio.tags:
                        audio["title"] = updated_title
                        audio["tracknumber"] = str(track_num)
                        # discnumber with total discs, e.g. "1/3"
                        audio["discnumber"] = f"{disc}/{total_discs}"
                        audio.save()
                        self.log_insert(f"[INFO] Updated metadata for {audio_file_path}.")

                        file_name = os.path.basename(audio_file_path)
                        self.audio_list.item(self.audio_list.get_children()[idx], values=(track_number_gui, updated_title, file_name))
                    else:
                        self.log_insert(f"[WARN] No tags found in {audio_file_path}, skipping metadata update.")
                except Exception as e:
                    self.log_insert(f"[ERROR] Failed to update metadata for {self.audio_files[idx]}: {e}")

        self._close_rename_window()

    def _load_txt_tracklist(self, txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                self.track_titles_txt = []

                disc = 0
                track_in_disc = 0
                set_header_re = re.compile(r"^--\s*(Set \d+|Encore)\s*--$", re.IGNORECASE)
                track_line_re = re.compile(r"^(\d{3})-(d\d{1}t\d{2})\s-\s(.*)$")

                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    if set_header_re.match(line):
                        disc += 1
                        track_in_disc = 0
                        continue

                    match = track_line_re.match(line)
                    if match:
                        track_in_disc += 1
                        track_code = match.group(2)
                        track_name = match.group(3)
                        self.log_insert(f"[DEBUG] Disc {disc}, Track {track_in_disc}: {track_name}")
                        self.track_titles_txt.append((disc, track_in_disc, track_code, track_name))

                self.total_discs = disc if disc > 0 else 1

        except Exception as e:
            self.log_insert(f"[ERROR] Failed to load tracklist from {txt_path}: {e}")
            self.track_titles_txt = []
            self.total_discs = 1

    def _update_rename_window(self):
        if not self.rename_window or not self.rename_window.winfo_exists():
            return

        if not self.track_title_entries:
            return

        if self.track_titles_txt:
            for idx, (_, _, _, track_name) in enumerate(self.track_titles_txt):
                if idx < len(self.track_title_entries):
                    try:
                        self.track_title_entries[idx].delete(0, tk.END)
                        self.track_title_entries[idx].insert(0, track_name)
                    except tk.TclError:
                        continue

            if self.canvas and self.canvas.winfo_exists():
                self.canvas.update_idletasks()
                self.canvas.config(scrollregion=self.canvas.bbox("all"))
