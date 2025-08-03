import os
import json
from pathlib import Path
from typing import List

ASSETS_DIR = Path("assets")
CACHE_FILE = Path("cache/asset_lists.json")

ARTISTS_FILE = ASSETS_DIR / "artists.txt"
VENUES_FILE = ASSETS_DIR / "venues.txt"
CITIES_FILE = ASSETS_DIR / "cities.txt"

DEFAULTS = {
    "artists.txt": ["Phish", "Grateful Dead", "Widespread Panic", "Leftover Salmon"],
    "venues.txt": ["Red Rocks", "Madison Square Garden", "The Fillmore"],
    "cities.txt": ["Boulder, CO", "New York, NY", "San Francisco, CA"],
}

def ensure_asset_files_exist(log_callback=None):
    """Create default asset files if missing."""
    ASSETS_DIR.mkdir(exist_ok=True)
    created = []

    for fname, lines in DEFAULTS.items():
        path = ASSETS_DIR / fname
        if not path.exists():
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            created.append(fname)
            if log_callback:
                log_callback(f"✅ Created default {fname} with {len(lines)} entries.")

    return created

def load_list(path: Path) -> List[str]:
    """Load a list of non-empty lines from a text file."""
    try:
        with path.open(encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return []

def load_asset_lists(log_callback=None):
    artists = load_list(ARTISTS_FILE)
    venues = load_list(VENUES_FILE)
    cities = load_list(CITIES_FILE)

    if log_callback:
        log_callback(f"Loaded {len(artists)} artists, {len(venues)} venues, {len(cities)} cities from TXT files.")

    return artists, venues, cities

def save_asset_cache(artists, venues, cities):
    """Save asset lists to cache for faster future loads."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CACHE_FILE.open("w", encoding="utf-8") as f:
        json.dump({"artists": artists, "venues": venues, "cities": cities}, f, indent=2)


# Load the lists once on import for convenience
artists_list, venues_list, cities_list = load_asset_lists()
artist_aliases = {}  # You can load or define this here if needed
