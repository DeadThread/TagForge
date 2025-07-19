import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Constants ---

DATE_RX = re.compile(r'(\d{2,4})-(\d{2})-(\d{2})')

STATE_ABBR = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH',
    'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
    'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
    'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN',
    'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

CITY_STATE_RE = re.compile(r'([A-Za-z.\s]+)[,\s]+([A-Za-z]{2,})', re.IGNORECASE)

KNOWN_FORMATS = {"FLAC", "FLAC16", "FLAC24", "MP3", "MP4", "WAV", "MKV", "MOV"}
KNOWN_SOURCES = {"SBD", "AUD", "FM", "SOFT"}

# --- Helper Functions ---

def extract_date(text):
    m = DATE_RX.search(text)
    if m:
        year, month, day = m.groups()
        # Normalize 2-digit years to 4-digit
        if len(year) == 2:
            y_int = int(year)
            if y_int > 50:
                year = "19" + year
            else:
                year = "20" + year
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""  # invalid date
    return ""

def extract_city(text):
    """
    Extract city and state from text, normalize state to 2-letter abbreviation.
    Return normalized "City, ST" or empty string if no match.
    """
    m = CITY_STATE_RE.search(text)
    if m:
        city = m.group(1).strip().title()
        state_raw = m.group(2).strip().title()
        state = STATE_ABBR.get(state_raw, state_raw.upper())
        return f"{city}, {state}"
    return ""

def capitalize_words_except_apostrophe(text):
    return ' '.join(word[0].upper() + word[1:] if word else '' for word in text.split(' '))

def capitalize_city_preserve_state(city):
    if "," in city:
        city_part, state_part = map(str.strip, city.split(",", 1))
        city_part = capitalize_words_except_apostrophe(city_part)
        state_part = state_part.upper()
        return f"{city_part}, {state_part}"
    else:
        return capitalize_words_except_apostrophe(city)

def find_normalized_value_exact(value, normalized_list):
    """
    Case-insensitive exact match only (no substring matches).
    Return the normalized value with original casing or None if no exact match.
    """
    if not value or not normalized_list:
        return None
    val_lower = value.lower()
    for norm_val in normalized_list:
        if norm_val.lower() == val_lower:
            logger.debug(f"Exact normalized match: {norm_val}")
            return norm_val
    return None

def find_best_match_in_name(name, normalized_list):
    """
    Find the best matching normalized entry from normalized_list that is contained
    as a substring in the name (case-insensitive). Returns the matched entry or None.
    """
    if not name or not normalized_list:
        return None
    name_lower = name.lower()
    # Prefer longest match to avoid partial short matches
    candidates = [val for val in normalized_list if val.lower() in name_lower]
    if not candidates:
        return None
    best_match = max(candidates, key=len)
    return best_match

def extract_id(text):
    m = re.search(r'\[([^\]]+)\]$', text)
    if m:
        v = m.group(1)
        if v.upper() not in KNOWN_SOURCES.union(KNOWN_FORMATS):
            return v
    return ""

def fallback_extract_city_and_venue(folder_name):
    # Split by commas
    parts = [p.strip() for p in folder_name.split(",")]
    if len(parts) < 2:
        return "", ""

    city_parts = parts[-2:]
    if len(city_parts) == 2 and len(city_parts[1]) == 2:
        city = f"{city_parts[0]}, {city_parts[1]}"
    else:
        city = city_parts[-1]

    date_match = DATE_RX.match(folder_name)
    if date_match:
        after_date = folder_name[date_match.end():].strip()
        city_str = ", ".join(city_parts)
        if after_date.endswith(city_str):
            venue = after_date[:-len(city_str)].rstrip(", ").strip()
        else:
            venue = ", ".join(parts[:-len(city_parts)]).strip()
    else:
        venue = ""

    return venue, city

# --- Patterns for regex matching folder names ---

patterns = [
    # Pattern 0: date venue, city,state (no artist, no hyphen, with commas)
    (
        re.compile(
            r'^(?P<date>\d{4}-\d{2}-\d{2})\s+'
            r'(?P<venue>[^,]+),\s+'
            r'(?P<city>[A-Za-z\s]+,\s*[A-Za-z]{2})'
            r'.*$',  # ignore trailing stuff
            re.IGNORECASE
        ),
        ["date", "venue", "city"]
    ),

    # Pattern 1: date - venue - city [id] (no artist)
    (
        re.compile(
            r'^(?P<date>\d{4}-\d{2}-\d{2})\s*-\s*'
            r'(?P<venue>.+?)\s*-\s*'
            r'(?P<city>[A-Za-z\s]+,\s*[A-Za-z]{2})\s*'
            r'(?:\[(?P<id>.+?)\])?.*$',
            re.IGNORECASE
        ),
        ["date", "venue", "city", "id"]
    ),

    # Pattern 2: artist - date venue, city [id]
    (
        re.compile(
            r'^(?P<artist>.+?)\s*-\s*'
            r'(?P<date>\d{4}-\d{2}-\d{2})\s+'
            r'(?P<venue>[^,]+),\s+'
            r'(?P<city>[A-Za-z\s]+,\s*[A-Za-z]{2})\s*'
            r'(?:\[(?P<id>.+?)\])?$',
            re.IGNORECASE
        ),
        ["artist", "date", "venue", "city", "id"]
    ),

    # Pattern 3: artist date venue, city [id]  -- no hyphen after artist
    (
        re.compile(
            r'^(?P<artist>.+?)\s+'
            r'(?P<date>\d{4}-\d{2}-\d{2})\s+'
            r'(?P<venue>.+?),\s+'
            r'(?P<city>[A-Za-z\s]+,\s*[A-Za-z]{2})\s*'
            r'(?:\[(?P<id>.+?)\])?$',
            re.IGNORECASE
        ),
        ["artist", "date", "venue", "city", "id"]
    ),

    # Pattern 4: artist date venue, city(.format) (optional format)
    (
        re.compile(
            r'^(?P<artist>.+?)\s+'
            r'(?P<date>\d{4}-\d{2}-\d{2})\s+'
            r'(?P<venue>.+?),\s+'
            r'(?P<city>[A-Za-z\s]+,\s*[A-Za-z]{2})'
            r'(?:\.(?P<format>\w+))?$',
            re.IGNORECASE
        ),
        ["artist", "date", "venue", "city", "format"]
    ),
]

# --- Main parsing function ---

def match_folder(name, normalized_artists=None, normalized_venues=None, normalized_cities=None, log=None):
    """
    Parse folder name and extract metadata: artist, date, venue, city, id, source, format, genre, additional.
    Uses regex patterns first, then fallbacks and normalization.
    """

    if log is None:
        def log(msg): pass

    logger.debug(f"Parsing folder name: {name}")

    # Fix missing space after commas in city names: "Manchester,TN" → "Manchester, TN"
    name = re.sub(r",(\S)", r", \1", name)

    info = dict.fromkeys(
        ["artist", "date", "venue", "city", "id", "source", "format", "genre", "additional", "add"], "")

    matched = False
    for rx, groups in patterns:
        m = rx.match(name)
        if m:
            matched = True
            logger.debug(f"Regex matched pattern: {rx.pattern}")
            for g in groups:
                val = (m.group(g) or "").strip()
                info[g] = val
                logger.debug(f"  Extracted {g}: {val}")
            break

    if not matched:
        logger.debug("No regex pattern matched.")

    # Fallback date extraction
    info["date"] = info["date"] or extract_date(name)
    logger.debug(f"  Extracted date (fallback): {info['date']}")

    # Artist resolution from normalized list
    if normalized_artists:
        artist_match = find_best_match_in_name(name, normalized_artists)
        if artist_match:
            info["artist"] = artist_match
            logger.debug(f"  Matched artist from list: {artist_match}")

    # City resolution from normalized list
    if normalized_cities:
        city_match = find_best_match_in_name(name, normalized_cities)
        if city_match:
            info["city"] = city_match
            logger.debug(f"  Matched city from list: {city_match}")

    # Remove city substring before venue search
    name_wo_city = name
    if info["city"]:
        pattern_city = re.escape(info["city"])
        name_wo_city = re.sub(pattern_city, '', name_wo_city, flags=re.IGNORECASE).strip()
        logger.debug(f"  Folder name without city: {name_wo_city}")

    # Venue resolution from normalized list
    if normalized_venues:
        venue_match = find_best_match_in_name(name_wo_city, normalized_venues)
        if venue_match:
            info["venue"] = venue_match
            logger.debug(f"  Matched venue from list: {venue_match}")

    # Extract bracket tokens for format, source, additional, etc.
    bracket_tokens = re.findall(r"\[([^\]]+)\]", name)

    format_token = next((t for t in bracket_tokens if t.upper() in KNOWN_FORMATS), None)
    if format_token:
        info["format"] = info["format"] or format_token

    source_token = next((t for t in bracket_tokens if t.upper() in KNOWN_SOURCES), None)
    if source_token:
        info["source"] = info["source"] or source_token

    info["id"] = info["id"] or extract_id(name)

    # Format fallback: check tokens that start with known formats
    if not info["format"]:
        name_upper = name.upper()
        tokens = re.findall(r'\w+', name_upper)
        for fmt in KNOWN_FORMATS:
            fmt_upper = fmt.upper()
            if any(token.startswith(fmt_upper) for token in tokens):
                info["format"] = fmt
                logger.debug(f"  Found format in name (fallback): {fmt}")
                break

    # Filter out known tokens and literal %token% placeholders from additional
    additional_tokens = [
        t for t in bracket_tokens
        if t != format_token
        and t != source_token
        and not (t.strip().startswith('%') and t.strip().endswith('%'))
    ]
    info["additional"] = info["add"] = " ".join(additional_tokens).strip()
    logger.debug(f"  Extracted additional: {info['additional']}")

    logger.debug(f"Finished parsing folder name with info: {info}")

    return info
