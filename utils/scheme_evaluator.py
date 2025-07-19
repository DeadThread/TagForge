import re
import os
import configparser
import pathlib
from pathlib import Path
from utils.logger import log_message  # Optional, for external logging

CONFIG_PATH = Path("config/config.ini")

class SchemeEvaluator:
    def __init__(self, folder_scheme, saving_scheme, log_func=None):
        self.folder_scheme = folder_scheme
        self.saving_scheme = saving_scheme
        self.log = log_func or (lambda msg, level="info": None)

    def evaluate(self, md):
        md_extended = md.copy()
        # Sync 'add' and 'additional'
        if "add" in md_extended and "additional" not in md_extended:
            md_extended["additional"] = md_extended["add"]
        if "additional" in md_extended and "add" not in md_extended:
            md_extended["add"] = md_extended["additional"]

        # --- Inject currentfoldername token support ---
        current_folder_path = md_extended.get("current_folder", "")
        if current_folder_path:
            try:
                md_extended["currentfoldername"] = Path(current_folder_path).name
            except Exception as e:
                self.log(f"Error extracting currentfoldername: {e}", level="error")
                md_extended["currentfoldername"] = ""
        else:
            md_extended.setdefault("currentfoldername", "")

        self.log(f"Evaluating folder scheme with metadata: {md_extended}", level="debug")

        def replace_token(match):
            token = match.group(1).lower()
            val = md_extended.get(token, "")
            return str(val) if val else ""

        def repl_year(m):
            inside = m.group(1).strip()
            inside_token = inside.strip("%").lower()
            if inside_token in md_extended:
                val = md_extended.get(inside_token, "")
                return val[:4] if len(val) >= 4 else ""
            else:
                m2 = re.match(r"(\d{4})", inside)
                return m2.group(1) if m2 else ""

        def clean_brackets(text):
            pattern = re.compile(r"[\[\(\{][^\[\]\(\)\{\}]*[\]\)\}]")
            prev_text = None
            curr_text = text
            while prev_text != curr_text:
                prev_text = curr_text

                def replacer(m):
                    inner = m.group(0)[1:-1]
                    return "" if inner.strip() == "" else m.group(0)

                curr_text = pattern.sub(replacer, curr_text)
            return curr_text

        # --- Evaluate folder scheme first ---
        folder_eval = self.folder_scheme or ""
        folder_eval = re.sub(r"%(\w+)%", replace_token, folder_eval)
        folder_eval = re.sub(r"\$year\(([^)]+)\)", repl_year, folder_eval)
        folder_eval = clean_brackets(folder_eval)
        folder_eval = re.sub(r"\s{2,}", " ", folder_eval).strip()

        # Insert the evaluated folder scheme as 'foldername' token in metadata
        md_extended["foldername"] = folder_eval

        self.log(f"Folder scheme evaluated to: {folder_eval}", level="debug")

        # --- Evaluate saving scheme with extended metadata ---
        def replace_token_saving(match):
            token = match.group(1).lower()
            val = md_extended.get(token, "")
            return str(val) if val else ""

        saving_eval = self.saving_scheme or ""
        saving_eval = re.sub(r"%(\w+)%", replace_token_saving, saving_eval)
        saving_eval = re.sub(r"\$year\(([^)]+)\)", repl_year, saving_eval)
        saving_eval = clean_brackets(saving_eval)
        saving_eval = re.sub(r"\s{2,}", " ", saving_eval).strip()

        if not folder_eval:
            self.log("Folder scheme evaluated to empty — check tokens and metadata.", level="error")
            return ""

        if saving_eval.lower() == "(root)" or saving_eval == "":
            full_path = folder_eval
        else:
            full_path = str(pathlib.Path(saving_eval) / folder_eval)

        full_path = full_path.replace("\\", "/").strip()

        if not full_path:
            self.log("Final evaluated path is empty.", level="error")
        else:
            # Extract and log only the base output folder from saving_eval
            base_output = saving_eval.split("/")[0] + ("/" + saving_eval.split("/")[1] if "/" in saving_eval else "")
            self.log(f"=> Output folder: {base_output}", tag="output_folder")


        return full_path


# === External utilities ===

def evaluate_schemes(md, folder_scheme, saving_scheme, log_func=None):
    """Evaluates folder + saving scheme and returns final path string."""
    evaluator = SchemeEvaluator(folder_scheme, saving_scheme, log_func)
    return evaluator.evaluate(md)


def load_schemes_from_ini(log=None, log_loaded=True):
    if not CONFIG_PATH.exists():
        return "", ""
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(CONFIG_PATH, encoding="utf-8")
        folder_scheme = config.get("SchemeEditor", "folder_scheme", fallback="")
        saving_scheme = config.get("SchemeEditor", "saving_scheme", fallback="")
        if log and log_loaded:
            log(f"Loaded folder scheme: {folder_scheme}")
            log(f"Loaded saving scheme: {saving_scheme}")
        return folder_scheme, saving_scheme
    except Exception as e:
        if log:
            log(f"Failed to load config.ini: {e}", level="error")
        return "", ""


def apply_schemes_to_processor(processor, folder_scheme, saving_scheme):
    """
    Updates processor's schemes and assigns the scheme evaluator function.
    Assumes processor has `update_schemes(folder_scheme, saving_scheme)` and `log_func` attribute.
    """
    if processor:
        # Update internal schemes
        processor.update_schemes(folder_scheme, saving_scheme)

        # Create a SchemeEvaluator instance
        evaluator = SchemeEvaluator(folder_scheme, saving_scheme, log_func=getattr(processor, "log_func", None))

        # Assign the evaluate method as the processor's scheme evaluator function
        processor.evaluate_schemes = evaluator.evaluate
