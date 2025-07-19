import os
import re

class TxtMetadataParser:
    def __init__(self, artists_list=None, venues_list=None, cities_list=None):
        self.artists_list = artists_list or []
        self.venues_list = venues_list or []
        self.cities_list = cities_list or []

    def parse(self, folder_path, audio_basename=None, log_func=None):
        if log_func is None:
            def log_func(msg, level="debug"): pass  # No-op logger

        metadata = {}

        if audio_basename is None:
            audio_basename = os.path.basename(os.path.normpath(folder_path))

        log_func(f"Looking for .txt files in folder: {folder_path}", level="debug")

        try:
            files = os.listdir(folder_path)
        except Exception as e:
            log_func(f"Failed to list directory '{folder_path}': {e}", level="debug")
            return {}

        log_func(f"All files in directory: {files}", level="debug")

        txt_files = [f for f in files if f.lower().endswith(".txt")]
        log_func(f"Found .txt files: {txt_files}", level="debug")

        if not txt_files:
            log_func(f"No .txt files found in: {folder_path}", level="debug")
            return {}

        # Sort txt files by length descending (prioritize longer files)
        txt_files.sort(key=lambda f: self._file_line_count(os.path.join(folder_path, f)), reverse=True)

        for txt_file in txt_files:
            txt_file_path = os.path.join(folder_path, txt_file)
            log_func(f"Trying to read metadata from: {txt_file_path}", level="debug")

            if not os.path.isfile(txt_file_path):
                log_func(f"Not a file or missing: {txt_file_path}", level="debug")
                continue
            if not os.access(txt_file_path, os.R_OK):
                log_func(f"File not readable: {txt_file_path}", level="debug")
                continue

            try:
                with open(txt_file_path, encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                log_func(f"Error reading {txt_file_path}: {e}", level="debug")
                continue

            # Initialize extracted metadata fields
            artist = ''
            venue = ''
            city = ''
            source = ''
            fmt = ''

            # First pass: look for explicit lines with labels
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.lower().startswith("artist:"):
                    m = re.match(r"artist:\s*(.*)", line, re.IGNORECASE)
                    if m:
                        artist = m.group(1).strip()
                elif line.lower().startswith("venue:"):
                    m = re.match(r"venue:\s*(.*)", line, re.IGNORECASE)
                    if m:
                        venue = m.group(1).strip()
                elif line.lower().startswith("city:") or line.lower().startswith("location:"):
                    m = re.match(r"(city|location):\s*(.*)", line, re.IGNORECASE)
                    if m:
                        city = m.group(2).strip()

            # Fallback: try to find known artists if none found
            if not artist and self.artists_list:
                for line in lines:
                    for a in self.artists_list:
                        if a.lower() in line.lower():
                            artist = a
                            break
                    if artist:
                        break

            # Fallback: try to find known venues if none found
            if not venue and self.venues_list:
                for line in lines:
                    for v in self.venues_list:
                        if v.lower() in line.lower():
                            venue = v
                            break
                    if venue:
                        break

            # Fallback: try to find known cities if none found
            if not city and self.cities_list:
                for line in lines:
                    for c in self.cities_list:
                        if c.lower() in line.lower():
                            city = c
                            break
                    if city:
                        break

            # Guess source from audio_basename
            if not source:
                for src in ["AUD", "SBD", "FM", "DAT", "MTX"]:
                    if src in audio_basename.upper():
                        source = src
                        break

            # Guess format from audio_basename
            if not fmt:
                ab = audio_basename.lower()
                if "flac16" in ab:
                    fmt = "FLAC16"
                elif "flac24" in ab:
                    fmt = "FLAC24"
                elif "mp3" in ab:
                    fmt = "MP3"

            # Build metadata dictionary only if values are present
            if artist:
                metadata['artist'] = artist
            if venue:
                metadata['venue'] = venue
            if city:
                metadata['city'] = city
            if source:
                metadata['source'] = source
            if fmt:
                metadata['format'] = fmt

            log_func(f"Extracted metadata: {metadata}", level="debug")

            # Return early on first successful extraction
            if metadata:
                return metadata

        # No metadata found in any txt files
        return {}

    def _file_line_count(self, filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0
