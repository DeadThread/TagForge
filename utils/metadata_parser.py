import os
import re
from datetime import datetime
import mutagen
from utils.constants import DEFAULTS
from utils.match_folder import match_folder
from utils.txt_parser import TxtMetadataParser


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

    # Try to find city by checking if any city in cities_list
    # is fully contained as a substring in the original album string (case insensitive)
    album_lower = album_str.lower()
    for city in cities_list:
        if city.lower() in album_lower:
            result["city"] = city
            break

    # Try to find venue by checking if any venue in venues_list
    # is fully contained as substring (case insensitive), excluding the city if found
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


def merge_metadata(folder_name, folder_path, artists_list, venues_list, cities_list, log_func=None):
    """
    Parse and merge metadata from file tags, folder name, and TXT metadata files.
    Returns a dict with keys: artist, venue, city, date, source, format, genre, add, additional.
    """

    # Parse tags from files
    file_tags = parse_tags_from_folder(folder_path)
    if log_func:
        log_func(f"[DEBUG] Parsed file tags from folder: {file_tags}", level="debug")

    album_val = file_tags.get("album", "").strip()
    album_parsed = parse_album_flexible(album_val, venues_list, cities_list)
    if log_func:
        log_func(f"[DEBUG] Parsed album flexibly: {album_parsed}", level="debug")

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
        normalized_artists=artists_list,
        normalized_venues=venues_list,
        normalized_cities=cities_list,
        log=log_func
    )
    if log_func:
        log_func(f"[DEBUG] Folder name parsed metadata: {folder_md}", level="debug")

    for key in ['artist', 'venue', 'city', 'date', 'source', 'format', 'genre', 'add', 'additional']:
        if key in ("source", "format"):
            val = md.get(key)
            if not val or val.upper() not in [x.upper() for x in DEFAULTS[key]]:
                if folder_md.get(key) and folder_md[key].upper() in [x.upper() for x in DEFAULTS[key]]:
                    md[key] = folder_md[key]
        else:
            if not md.get(key) and folder_md.get(key):
                md[key] = folder_md[key]

    parser = TxtMetadataParser(
        artists_list=artists_list,
        venues_list=venues_list,
        cities_list=cities_list
    )
    txt_md = parser.parse(folder_path, log_func=log_func)
    if log_func:
        log_func(f"[DEBUG] TXT metadata parsed: {txt_md}", level="debug")

    for key in ('artist', 'venue', 'city', 'date', 'source', 'format'):
        if key in ("source", "format"):
            txt_val = txt_md.get(key)
            if txt_val and txt_val.upper() in [x.upper() for x in DEFAULTS[key]]:
                md[key] = txt_val
        else:
            if txt_md.get(key):
                md[key] = txt_md[key]

    # Date selection logic - prioritize more precise dates over year-only
    candidate_dates = [
        txt_md.get("date") or txt_md.get("release date"),
        folder_md.get("date"),
        album_parsed.get("date"),
        file_tags.get("date"),
    ]
    candidate_dates = [d for d in candidate_dates if d]

    selected_date = None
    for cd in candidate_dates:
        nd = normalize_date(cd)
        if nd and not nd.endswith("-01-01"):
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
                if log_func:
                    log_func(f"[DEBUG] Set source from folder name token: {md['source']}", level="debug")

    return md
