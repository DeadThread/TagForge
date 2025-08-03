from pathlib import Path

# --- Paths ---
CONFIG_DIR = Path("config")
ASSETS_DIR = Path("assets")
CACHE_DIR = Path("cache")

HISTORY_FILE = CONFIG_DIR / "history_cache.json"
USED_CACHE_FILE = CONFIG_DIR / "used_cache.json"

ARTISTS_FILE = ASSETS_DIR / "artists.txt"
VENUES_FILE = ASSETS_DIR / "venues.txt"
CITIES_FILE = ASSETS_DIR / "cities.txt"

# --- Default dropdown values ---
DEFAULTS = {
    "source": ["SBD", "AUD", "MTX", "FM", "DAT"],
    "format": ["FLAC16", "FLAC24", "FLAC", "MP3-V0", "MP3-320", "MP3-256", "MP3-128"],
    "genre": ["Jam", "Progressive Rock", "Bluegrass", "Rock", "Blues"],
    "artist": [],
    "venue": [],
    "city": [],
    "add": ["Remastered", "Bootleg", "5.1"],
}
