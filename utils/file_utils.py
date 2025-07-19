# utils/file_utils.py

import os

def load_text_list(filepath):
    """Load non-empty stripped lines from a file, return list of strings."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def normalize_string(s):
    """Simple normalization: lowercase and strip whitespace."""
    return s.strip().lower() if s else ""

def update_text_file(filepath, value, log_func=None):
    """
    Insert `value` at top of file if not already present (case-insensitive).
    Creates file if missing.
    """
    value = value.strip()
    if not value:
        return
    try:
        lines = []
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

        # Avoid duplicates, case-insensitive
        if any(line.lower() == value.lower() for line in lines):
            return

        lines.insert(0, value)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        if log_func:
            log_func(f"✏️ Added to {os.path.basename(filepath)}: {value}")
    except Exception as e:
        if log_func:
            log_func(f"❌ Could not update {filepath}: {e}")
