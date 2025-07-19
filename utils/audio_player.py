import tkinter as tk
from tkinter import ttk
import vlc
import threading
import time
import mutagen
import os
import sys
import ctypes
from utils.rename_manager import RenameManager


class AudioPlayer(tk.Frame):
    def __init__(
        self,
        parent,
        get_current_folder_callback=None,
        log_widget=None,
        set_artist=None,
        set_date=None,
        set_venue=None,
    ):
        super().__init__(parent)
        self.parent = parent  # Fixed: store actual parent widget reference
        self.get_current_folder = get_current_folder_callback
        self.log = log_widget
        self.set_artist = set_artist
        self.set_date = set_date
        self.set_venue = set_venue

        self.audio_files = []
        self._audio_length_ms = 0
        self._stop_flag = False
        self.track_titles_txt = []
        self.show_metadata = {}
        self._user_seeking = False
        self.rename_manager = None

        # Inline log insert function (safe if no log widget)
        self.log_insert = lambda msg: self.log.insert(tk.END, msg + "\n") if self.log else None

        # VLC Setup - Load DLLs if bundled
        base = getattr(sys, '_MEIPASS', os.path.abspath("."))
        vlc_dir = os.path.join(base, "vlc")
        if os.path.isdir(vlc_dir):
            try:
                if sys.platform.startswith("win"):
                    ctypes.CDLL(os.path.join(vlc_dir, "libvlc.dll"))
                    ctypes.CDLL(os.path.join(vlc_dir, "libvlccore.dll"))
            except Exception as e:
                self.log_insert(f"[ERROR] Failed to load VLC DLLs: {e}")
            os.environ["VLC_PLUGIN_PATH"] = os.path.join(vlc_dir, "plugins")

        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()

        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="Audio File List & Playback", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=6)

        playback_frame = tk.Frame(self)
        playback_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        columns = ("track", "title", "filename")
        self.audio_list = ttk.Treeview(playback_frame, columns=columns, show="headings", height=6)
        self.audio_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.audio_list.heading("track", text="Track #")
        self.audio_list.heading("title", text="Title")
        self.audio_list.heading("filename", text="Filename")
        self.audio_list.column("track", width=50, anchor="center")
        self.audio_list.column("title", width=250, anchor="w")
        self.audio_list.column("filename", width=350, anchor="w")

        scrollbar_audio = ttk.Scrollbar(playback_frame, orient=tk.VERTICAL, command=self.audio_list.yview)
        scrollbar_audio.pack(side=tk.LEFT, fill=tk.Y)
        self.audio_list.configure(yscrollcommand=scrollbar_audio.set)

        self.audio_list.bind("<Double-1>", self._on_track_double_click)
        self.audio_list.bind("<Return>", self._on_track_enter)

        controls_frame = tk.Frame(self)
        controls_frame.pack(fill=tk.X, padx=6, pady=(4, 0))

        ttk.Button(controls_frame, text="Play", command=self._play_audio).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls_frame, text="Stop", command=self._stop_audio).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls_frame, text="Add to Audio Player", command=self._add_audio_folder).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls_frame, text="Clear Audio Player", command=self._clear_audio_player).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls_frame, text="Rename Track Names", command=self._open_rename_window).pack(side=tk.LEFT, padx=4)

        tk.Label(controls_frame, text="Volume:").pack(side=tk.LEFT, padx=(12, 4))
        self.volume_scale = ttk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=120, command=self._set_volume)
        self.volume_scale.set(80)
        self.volume_scale.pack(side=tk.LEFT, padx=4)

        self.seek_scale = ttk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=300)
        self.seek_scale.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)
        self.seek_scale.bind("<Button-1>", self._seek_start)
        self.seek_scale.bind("<ButtonRelease-1>", self._seek_end)

        self.playback_time_label = tk.Label(controls_frame, text="00:00 / 00:00")
        self.playback_time_label.pack(side=tk.LEFT, padx=12)

    def _on_track_double_click(self, event):
        item = self.audio_list.identify_row(event.y)
        if item:
            index = self.audio_list.index(item)
            self._play_audio_at_index(index)

    def _on_track_enter(self, event):
        selection = self.audio_list.selection()
        if selection:
            index = self.audio_list.index(selection[0])
            self._play_audio_at_index(index)

    def _add_audio_folder(self):
        folder = self.get_current_folder() if self.get_current_folder else None
        if folder and os.path.isdir(folder):
            self.log_insert(f"[DEBUG] Loading audio from: {folder}")
            self.load_audio_files(folder)
        else:
            self.log_insert("[ERROR] Could not access selected folder from GUI context.")

    def _clear_audio_player(self):
        self._stop_audio()
        self.audio_list.delete(*self.audio_list.get_children())
        self.audio_files = []
        self._audio_length_ms = 0
        self.track_titles_txt = []
        self.show_metadata = {}
        self.rename_manager = None
        self.log_insert("[INFO] Audio player cleared")

    def load_audio_files(self, folder_path):
        self.audio_list.delete(*self.audio_list.get_children())
        self.audio_files = []
        self.track_titles_txt = []
        self.show_metadata = {}

        try:
            files = sorted(os.listdir(folder_path))
        except Exception as e:
            self.log_insert(f"[ERROR] Could not list directory {folder_path}: {e}")
            return

        # Try to find a tracklist txt file
        txt_path = next(
            (
                os.path.join(folder_path, f)
                for f in [f"{os.path.basename(folder_path)}.txt", "tracklist.txt", "tracks.txt"]
                if os.path.exists(os.path.join(folder_path, f))
            ),
            None,
        )
        if txt_path:
            self._load_txt_tracklist(txt_path)

        self._update_show_metadata_ui()
        track_num = 1
        for f in files:
            if f.lower().endswith(('.mp3', '.flac', '.wav', '.ogg')):
                full = os.path.join(folder_path, f)
                self.audio_files.append(full)
                title = self.track_titles_txt[track_num - 1] if len(self.track_titles_txt) >= track_num else ''
                try:
                    if not title:
                        tags = mutagen.File(full)
                        title = tags.get("title", [""])[0] if tags and tags.get("title") else ""
                except Exception:
                    pass
                self.audio_list.insert("", "end", values=(f"D1T{track_num}", title, f))
                track_num += 1

        if self.audio_files:
            try:
                self._audio_length_ms = int(mutagen.File(self.audio_files[0]).info.length * 1000)
            except Exception:
                self._audio_length_ms = 0

        self.initialize_rename_manager()

    def _load_txt_tracklist(self, path):
        try:
            with open(path, encoding='utf-8') as f:
                lines = f.readlines()
            self.track_titles_txt = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
        except Exception as e:
            self.log_insert(f"[ERROR] Failed to read tracklist: {e}")

    def _update_show_metadata_ui(self):
        if self.set_artist:
            self.set_artist(self.show_metadata.get("artist", ""))
        if self.set_date:
            self.set_date(self.show_metadata.get("date", ""))
        if self.set_venue:
            self.set_venue(self.show_metadata.get("venue", ""))

    def initialize_rename_manager(self):
        if self.rename_manager is None:
            self.rename_manager = RenameManager(
                parent=self,
                audio_player=self,
                audio_files=self.audio_files,
                audio_list=self.audio_list,
                log_insert=self.log_insert
            )
        else:
            # Update the audio_files and audio_list references
            self.rename_manager.audio_files = self.audio_files
            self.rename_manager.audio_list = self.audio_list

    def _play_audio(self):
        selection = self.audio_list.selection()
        if not selection:
            self.log_insert("[WARN] No track selected")
            return
        index = self.audio_list.index(selection[0])
        self._play_audio_at_index(index)

    def _play_audio_at_index(self, index):
        if 0 <= index < len(self.audio_files):
            filepath = self.audio_files[index]
            media = self.vlc_instance.media_new(filepath)
            self.player.set_media(media)
            self.player.play()
            self._stop_flag = False
            self._start_playback_updater()
            self.log_insert(f"[INFO] Playing: {filepath}")

    def _stop_audio(self):
        self._stop_flag = True
        self.player.stop()
        self.seek_scale.set(0)
        self.playback_time_label.config(text="00:00 / 00:00")
        self.log_insert("[INFO] Playback stopped")

    def _seek_start(self, event):
        self._user_seeking = True

    def _seek_end(self, event):
        self._user_seeking = False
        pos_ms = self.seek_scale.get() / 100 * self._audio_length_ms
        self.player.set_time(int(pos_ms))

    def _set_volume(self, value):
        try:
            self.player.audio_set_volume(int(float(value)))
        except Exception:
            pass

    def _start_playback_updater(self):
        def loop():
            while not self._stop_flag:
                try:
                    current = self.player.get_time()
                    total = self.player.get_length()
                    if total > 0:
                        percent = (current / total) * 100
                        if not self._user_seeking:
                            self.seek_scale.set(percent)
                        self.playback_time_label.config(
                            text=f"{self._format_time(current / 1000)} / {self._format_time(total / 1000)}"
                        )
                except Exception:
                    pass
                time.sleep(0.25)

        threading.Thread(target=loop, daemon=True).start()

    def _format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _open_rename_window(self):
        if self.rename_manager:
            self.rename_manager._open_rename_window()
