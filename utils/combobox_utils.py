from gui.build_gui import DEFAULTS

def update_combobox_values(
    artists_list,
    venues_list,
    cities_list,
    artist_cache,
    genre_cache,
    histories,
    last_source,
    last_format,
    last_genre,
    comboboxes_dict,
):
    """
    Update combobox values for artist, venue, city, add, source, format, genre.

    Args:
        artists_list (list): List of artists from assets.
        venues_list (list): List of venues from assets.
        cities_list (list): List of cities from assets.
        artist_cache (set): Cached artist entries.
        genre_cache (set): Cached genre entries.
        histories (dict): Dict of sets containing history entries keyed by category.
        last_source (str): Last used source value.
        last_format (str): Last used format value.
        last_genre (str): Last used genre value.
        comboboxes_dict (dict): Mapping of keys to combobox widgets, e.g.
            {
                "artist": ttk.Combobox,
                "venue": ttk.Combobox,
                "city": ttk.Combobox,
                "add": None,
                "source": ttk.Combobox,
                "format": ttk.Combobox,
                "genre": ttk.Combobox,
            }

    Returns:
        None. Modifies comboboxes in place.
    """
    for key in ["artist", "venue", "city", "add", "source", "format", "genre"]:
        combobox = comboboxes_dict.get(key)
        seen = set()
        final_list = []

        # Load base list from .txt file or DEFAULTS
        if key == "artist":
            base_defaults = artists_list.copy()
        elif key == "venue":
            base_defaults = venues_list.copy()
        elif key == "city":
            base_defaults = cities_list.copy()
        else:
            base_defaults = DEFAULTS.get(key, []).copy()

        # Get last used
        last_used_val = {
            "source": last_source,
            "format": last_format,
            "genre": last_genre,
        }.get(key, "")

        if last_used_val and last_used_val not in seen:
            final_list.append(last_used_val)
            seen.add(last_used_val)

        # Append base defaults (preserve order)
        for val in base_defaults:
            if val and val not in seen:
                final_list.append(val)
                seen.add(val)

        # Append extra cached values for artist/genre
        if key == "artist":
            extra_cache = sorted(artist_cache, key=lambda x: x.lower())
        elif key == "genre":
            extra_cache = sorted(genre_cache, key=lambda x: x.lower())
        else:
            extra_cache = []

        for val in extra_cache:
            if val and val not in seen:
                final_list.append(val)
                seen.add(val)

        # Append history values (unordered)
        for val in histories.get(key, set()):
            if val and val not in seen:
                final_list.append(val)
                seen.add(val)

        # Set combobox values if exists
        if combobox:
            combobox["values"] = final_list
