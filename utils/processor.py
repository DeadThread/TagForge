import os
import re
import shutil
from datetime import datetime
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3

from utils.constants import ARTISTS_FILE, VENUES_FILE, CITIES_FILE
from utils.scheme_evaluator import SchemeEvaluator


class Processor:
    def __init__(
        self,
        evaluate_schemes_func,
        match_folder_func,
        log_func,
        artists_list,
        venues_list,
        cities_list,
        artist_cache,
        genre_cache,
        used_cache,
        histories,
        last_source="",
        last_format="",
        last_genre="",
    ):
        self._evaluate_schemes = evaluate_schemes_func
        self._match_folder = match_folder_func
        self.log = log_func

        self.artists_list = artists_list
        self.venues_list = venues_list
        self.cities_list = cities_list

        self.artist_cache = artist_cache
        self.genre_cache = genre_cache
        self.used_cache = used_cache
        self.histories = histories

        self.last_source = last_source
        self.last_format = last_format
        self.last_genre = last_genre

        # Store current folder and saving schemes and evaluator instance
        self.folder_scheme = None
        self.saving_scheme = None
        self.scheme_evaluator = None

    def update_schemes(self, folder_scheme, saving_scheme):
        """Update folder and saving schemes and recompile the evaluator."""
        self.log("Updating schemes...", level="debug")
        self.log(f"Old folder scheme: {self.folder_scheme}", level="debug")
        self.log(f"Old saving scheme: {self.saving_scheme}", level="debug")
        self.folder_scheme = folder_scheme
        self.saving_scheme = saving_scheme
        self.scheme_evaluator = SchemeEvaluator(folder_scheme, saving_scheme, log_func=self.log)
        self._evaluate_schemes = self.scheme_evaluator.evaluate
        self.log("Schemes updated and evaluator compiled.", level="info")

    def _split_genres(self, genre_str):
        if not genre_str:
            return []
        return [g.strip() for g in re.split(r"[;,]", genre_str) if g.strip()]

    def _normalize_date(self, date_str):
        if not date_str:
            return ""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return date_str.strip()

    def _update_txt_file(self, file_path, new_value):
        new_value = new_value.strip()
        if not new_value:
            return
        try:
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
            else:
                lines = []
        except Exception as e:
            self.log(f"  Failed reading {file_path}: {e}")
            return

        # Avoid duplicate (case-insensitive)
        if any(line.lower() == new_value.lower() for line in lines):
            return

        lines.insert(0, new_value)
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            self.log(f"  Updated {os.path.basename(file_path)} with: {new_value}")
        except Exception as e:
            self.log(f"  Failed writing {file_path}: {e}")

    def process_folders(self, folders, gui_fallbacks):
        """Process a list of source folders, move & tag files accordingly."""
        processed = []

        for folder in folders:
            folder_name = os.path.basename(folder)
            self.log(f"\nProcessing folder: {folder}")

            md = self._match_folder(
                folder_name,
                normalized_artists=self.artists_list,
                normalized_venues=self.venues_list,
                normalized_cities=self.cities_list,
                log=self.log,
            )

            # GUI fallbacks take precedence over parsed values
            # This ensures UI-set values override folder name parsing
            date_raw = gui_fallbacks.get("date", "") or md.get("date", "")
            date = self._normalize_date(date_raw)

            artist = gui_fallbacks.get("artist", "") or md.get("artist", "")
            venue = gui_fallbacks.get("venue", "") or md.get("venue", "")
            city = gui_fallbacks.get("city", "") or md.get("city", "")
            source = gui_fallbacks.get("source", "") or md.get("source", "")
            fmt = gui_fallbacks.get("format", "") or md.get("format", "")
            genre = gui_fallbacks.get("genre", "") or md.get("genre", "")
            add = gui_fallbacks.get("add", "") or md.get("additional", "") or md.get("add", "")

            # Update dropdown histories
            for key, val in [("source", source), ("format", fmt), ("genre", genre), ("add", add)]:
                if val:
                    self.histories.setdefault(key, set()).add(val)

            # Update artist and genre caches
            if artist:
                self.artist_cache.add(artist)
            if genre:
                for g in self._split_genres(genre):
                    self.genre_cache.add(g)

            # Update used cache linking artist to genre
            if artist and genre:
                self.used_cache.setdefault("artists", {})[artist] = genre

            # Update last used fields
            self.last_source = source
            self.last_format = fmt
            self.last_genre = genre

            # Update .txt asset lists
            self._update_txt_file(ARTISTS_FILE, artist)
            self._update_txt_file(VENUES_FILE, venue)
            self._update_txt_file(CITIES_FILE, city)

            # Compose metadata dict for scheme evaluation
            meta = {
                "artist": artist,
                "venue": venue,
                "city": city,
                "source": source,
                "format": fmt,
                "genre": genre,
                "additional": add,
                "add": add,
                "date": date,

                # Only currentfoldername (filename removed)
                "currentfoldername": gui_fallbacks.get("currentfoldername", ""),
            }

            self.log(f"Metadata for scheme evaluation: {meta}")

            self.log("Evaluating output folder path with current schemes.")

            try:
                out_folder = self._evaluate_schemes(meta).strip(os.sep)
                meta["album"] = os.path.basename(out_folder)
                self.log(f"Output folder: {out_folder}")
                os.makedirs(out_folder, exist_ok=True)
            except Exception as e:
                self.log(f"Failed evaluating output folder path: {e}")
                continue

            success = True
            for root_dir, _, files in os.walk(folder):
                for file in files:
                    src_fp = os.path.join(root_dir, file)
                    dest_fp = os.path.join(out_folder, file)

                    # Handle filename collisions
                    if os.path.exists(dest_fp):
                        base, ext = os.path.splitext(file)
                        counter = 1
                        while True:
                            new_name = f"{base}({counter}){ext}"
                            dest_fp = os.path.join(out_folder, new_name)
                            if not os.path.exists(dest_fp):
                                break
                            counter += 1
                        self.log(f"  Renaming due to collision: {file} → {os.path.basename(dest_fp)}")

                    try:
                        shutil.move(src_fp, dest_fp)
                        ext = os.path.splitext(file)[1].lower()
                        if ext in (".flac", ".mp3"):
                            genres_list = self._split_genres(genre)
                            self.retag_file(dest_fp, artist, meta["album"], date, venue, city, genres_list, source, fmt)
                    except Exception as e:
                        self.log(f"  Failed moving/tagging {file}: {e}")
                        success = False

            root_source_folder = "M:/Test-Folder"  # or get this from config/parameter
            self._cleanup_folder(folder, "Removed empty source folder", stop_at=root_source_folder)
            self._cleanup_folder(out_folder, "Removed empty output folder")  # usually you may want to clean output too if empty

            if success:
                self.log(f"Finished processing folder: {out_folder}")
                processed.append(folder)
            else:
                self.log(f"Finished processing with errors: {folder}")

        return processed

    def retag_file(self, fp, artist, album, date, venue, city, genres, src, fmt):
        """Tags an audio file (FLAC or MP3) with provided metadata."""
        try:
            ext = os.path.splitext(fp)[1].lower()
            if ext == ".flac":
                audio = FLAC(fp)
            elif ext == ".mp3":
                audio = MP3(fp, ID3=EasyID3)
                if audio.tags is None:
                    audio.add_tags()
            else:
                self.log(f"  Skipped unsupported file type: {os.path.basename(fp)}")
                return

            if artist:
                audio["artist"] = artist
            if album:
                audio["album"] = album
            if date:
                audio["date"] = date
            if venue:
                audio["venue"] = venue
            if city:
                audio["location"] = city
            if genres:
                audio["genre"] = "; ".join(sorted({g.strip() for g in genres if g.strip()}))
            if src:
                audio["source"] = src
            if fmt:
                audio["comment"] = fmt

            audio.save()
            self.log(f"  Tagged: {os.path.basename(fp)}")
        except Exception as e:
            self.log(f"  Tagging failed for {os.path.basename(fp)}: {e}")

    def _cleanup_folder(self, folder, msg, stop_at=None):
        """
        Recursively remove empty folders from `folder` up to `stop_at`.
        If `stop_at` is None, stops at first non-empty folder or root.
        """
        folder = os.path.abspath(folder)
        if stop_at is not None:
            stop_at = os.path.abspath(stop_at)

        while True:
            if not os.path.isdir(folder):
                break
            if stop_at is not None and os.path.normcase(folder) == os.path.normcase(stop_at):
                # Reached stop folder, stop here
                break

            try:
                # List folder contents ignoring some system files
                entries = os.listdir(folder)
                entries = [e for e in entries if e not in {'.DS_Store', 'Thumbs.db', 'desktop.ini'}]
                if entries:
                    # Folder not empty, stop recursion
                    break

                os.rmdir(folder)
                self.log(f"{msg}: {folder}")

            except Exception as e:
                self.log(f"  Failed cleaning folder {folder}: {e}")
                break

            folder = os.path.dirname(folder)  # move up one folder