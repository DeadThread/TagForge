import os
from utils.logger import log_message
from utils.scheme_evaluator import load_schemes_from_ini, evaluate_schemes
from utils.cache_manager import update_used_cache, save_used_cache

def remove_empty_parents(path, stop_at, log_func=None):
    path = os.path.abspath(path)
    stop_at = os.path.abspath(stop_at)

    while True:
        if not os.path.isdir(path):
            break
        if path == stop_at:
            break

        try:
            entries = os.listdir(path)
            # Optionally filter out hidden files if you want to ignore them:
            entries = [e for e in entries if e not in {'.DS_Store', 'Thumbs.db', 'desktop.ini'}]
            if entries:
                break  # Folder not empty, stop here
            os.rmdir(path)
            if log_func:
                log_func(f"Removed empty source folder: {path}", level="info")
        except Exception as e:
            if log_func:
                log_func(f"Failed to remove folder {path}: {e}", level="warning")
            break
        path = os.path.dirname(path)

def process_thread(gui_instance):
    log_message(gui_instance.log, "Starting process_thread", level="debug")

    # Initialize processor if not present
    if not hasattr(gui_instance, "processor"):
        from utils.processor import Processor
        gui_instance.processor = Processor()

    def evaluate_all_schemes(md):
        log_message(gui_instance.log, "Loading fresh schemes in evaluate_all_schemes", level="debug")
        current_folder_scheme, current_saving_scheme = load_schemes_from_ini(
            log=lambda m, level="info": log_message(gui_instance.log, m, level=level)
        )
        log_message(gui_instance.log, f"Fresh schemes loaded - Folder: {current_folder_scheme}", level="debug")
        log_message(gui_instance.log, f"Fresh schemes loaded - Saving: {current_saving_scheme}", level="debug")

        folder_name = evaluate_schemes(
            md, current_folder_scheme, current_saving_scheme,
            log_func=lambda m, level="debug": log_message(gui_instance.log, m, level=level)
        ).strip()
        md["filename"] = folder_name  # for $filename() in schemes
        log_message(gui_instance.log, f"=> Output folder:\n{folder_name}", level="info")
        return folder_name

    gui_instance.processor.evaluate_schemes_func = evaluate_all_schemes

    queue = getattr(gui_instance, "queue_manager", None)
    if queue is None:
        log_message(gui_instance.log, "Queue manager not initialized.", level="error")
        return

    saved = queue.saved
    saved_meta = queue.saved_meta

    if not saved:
        log_message(gui_instance.log, "No folders queued for processing.", level="warn")
        return

    processed_folders = []

    base_input_folder = "M:/Test-Folder"  # Adjust as needed

    # Capture current form values into histories BEFORE processing
    for key, var_name in [
        ("artist", "artist"),
        ("venue", "venue"), 
        ("city", "city"),
        ("add", "add"),
        ("source", "source"),
        ("format", "fmt"),
        ("genre", "genre"),
    ]:
        var = getattr(gui_instance, var_name, None)
        if var:
            val = var.get().strip()
            if val:
                gui_instance.histories[key].add(val)

    for folder in saved[:]:
        meta = saved_meta.get(folder, {})

        fallback_date = meta.get("date")
        if not fallback_date or not fallback_date.strip():
            y = gui_instance.year.get()
            mo = gui_instance.mo.get().zfill(2) if gui_instance.mo.get() else "01"
            da = gui_instance.da.get().zfill(2) if gui_instance.da.get() else "01"
            if y and y.isdigit():
                fallback_date = f"{y}-{mo}-{da}"
            else:
                fallback_date = ""

        def get_fallback_value(meta_val, gui_val, last_used_val=""):
            if meta_val and meta_val.strip():
                return meta_val.strip()
            if gui_val and gui_val.strip():
                return gui_val.strip()
            if last_used_val and last_used_val.strip():
                return last_used_val.strip()
            return ""

        fallback = {
            "artist": get_fallback_value(meta.get("artist"), gui_instance.artist.get(), getattr(gui_instance, "last_artist", "")),
            "venue": get_fallback_value(meta.get("venue"), gui_instance.venue.get()),
            "city": get_fallback_value(meta.get("city"), gui_instance.city.get()),
            "source": get_fallback_value(meta.get("source"), gui_instance.source.get(), getattr(gui_instance, "last_source", "")),
            "format": get_fallback_value(meta.get("format"), gui_instance.fmt.get(), getattr(gui_instance, "last_format", "")),
            "add": get_fallback_value(meta.get("additional") or meta.get("add"), gui_instance.add.get(), getattr(gui_instance, "last_add", "")),
            "genre": get_fallback_value(meta.get("genre"), gui_instance.genre.get(), getattr(gui_instance, "last_genre", "")),
            "date": fallback_date,
            "currentfoldername": os.path.basename(os.path.normpath(folder)),
            "filename": os.path.basename(os.path.normpath(folder)),
        }

        log_message(gui_instance.log, f"Metadata with currentfoldername for processing: {fallback}", level="debug")

        # Add processed values to histories as well
        for key in ["artist", "venue", "city", "source", "format", "add", "genre"]:
            value = fallback.get(key)
            if value and value.strip():
                gui_instance.histories[key].add(value.strip())

        try:
            result = gui_instance.processor.process_folders([folder], fallback)
            processed_folders.extend(result)

            remove_empty_parents(folder, base_input_folder, log_func=lambda m, level="info": log_message(gui_instance.log, m, level=level))

            if fallback.get("artist") and fallback.get("genre"):
                update_used_cache(
                    gui_instance.used_cache,
                    fallback["artist"],
                    fallback["genre"],
                    log_func=lambda m, level="debug": log_message(gui_instance.log, m, level=level),
                )
        except Exception as e:
            log_message(gui_instance.log, f"Error processing folder '{folder}': {e}", level="error")

    for folder in processed_folders:
        if folder in saved:
            saved.remove(folder)
        if folder in saved_meta:
            del saved_meta[folder]

    gui_instance.last_source = gui_instance.processor.last_source
    gui_instance.last_format = gui_instance.processor.last_format
    gui_instance.last_genre = gui_instance.processor.last_genre
    gui_instance.last_add = gui_instance.processor.last_add  # Added this line

    # Save history cache after processing
    gui_instance._save_history()

    # All GUI updates should be done safely on main thread:
    def gui_updates():
        gui_instance.refresh_queue_ui()
        gui_instance._refresh()
        gui_instance._update_combobox_values()  # Update with fresh history data
        gui_instance._update_used_cache()
        try:
            save_used_cache(
                gui_instance.used_cache,
                log_func=lambda m, level="info": log_message(gui_instance.log, m, level=level),
            )
        except Exception as e:
            log_message(gui_instance.log, f"Failed to save used cache: {e}", level="error")

    gui_instance.root.after(0, gui_updates)