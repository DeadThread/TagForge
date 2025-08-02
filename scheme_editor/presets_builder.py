# /scheme_editor/presets_builder.py

import configparser
from tkinter import messagebox, simpledialog
import tkinter as tk
from pathlib import Path

def load_presets(preset_file, preset_combo, preset_var, config_file, on_preset_selected, log):
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(preset_file)

        presets = list(config.sections()) or ["Default"]
        preset_combo['values'] = presets

        if not config_file.exists():
            preset_var.set("Default")
            on_preset_selected()
    except Exception as e:
        log(f"Error loading presets: {e}")
        preset_combo['values'] = ["Default"]
        if not config_file.exists():
            preset_var.set("Default")
            on_preset_selected()

def on_preset_selected(preset_var, txt_saving, txt_folder, preset_file, loading_flag, _refresh_preview, log):
    if loading_flag[0]:
        return

    preset_name = preset_var.get()
    if not preset_name:
        return

    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(preset_file)

        if preset_name in config:
            loading_flag[0] = True
            saving_scheme = config[preset_name].get("saving_scheme", "")
            folder_scheme = config[preset_name].get("folder_scheme", "")

            txt_saving.delete("1.0", tk.END)
            txt_saving.insert("1.0", saving_scheme)

            txt_folder.delete("1.0", tk.END)
            txt_folder.insert("1.0", folder_scheme)

            _refresh_preview()
            log(f"Loaded preset: {preset_name}")
    except Exception as e:
        log(f"Error loading preset {preset_name}: {e}")
    finally:
        loading_flag[0] = False

def add_preset(preset_file, preset_var, txt_saving, txt_folder, preset_combo, log, load_presets_func):
    name = simpledialog.askstring("Add Preset", "Enter preset name:")
    if not name or not name.strip():
        return

    name = name.strip()
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(preset_file)

        if name in config:
            if not messagebox.askyesno("Preset Exists", f"Preset '{name}' already exists. Overwrite?"):
                return

        config[name] = {
            "saving_scheme": txt_saving.get("1.0", "end-1c").strip(),
            "folder_scheme": txt_folder.get("1.0", "end-1c").strip()
        }

        with open(preset_file, "w", encoding="utf-8") as f:
            config.write(f)

        load_presets_func()
        preset_var.set(name)
        log(f"Added preset: {name}")
    except Exception as e:
        log(f"Error adding preset: {e}")
        messagebox.showerror("Error", f"Failed to add preset: {e}")

def remove_preset(preset_file, preset_var, preset_combo, config_file, log, load_presets_func):
    preset_name = preset_var.get()
    if not preset_name:
        messagebox.showwarning("No Selection", "Please select a preset to remove.")
        return

    if preset_name == "Default":
        messagebox.showwarning("Cannot Remove", "Cannot remove the Default preset.")
        return

    if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete preset '{preset_name}'?"):
        return

    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(preset_file)

        if preset_name in config:
            config.remove_section(preset_name)
            with open(preset_file, "w", encoding="utf-8") as f:
                config.write(f)

            load_presets_func()
            preset_var.set("")
            log(f"Removed preset: {preset_name}")
    except Exception as e:
        log(f"Error removing preset: {e}")
        messagebox.showerror("Error", f"Failed to remove preset: {e}")

def find_matching_preset(preset_file, saving_scheme, folder_scheme):
    try:
        config = configparser.ConfigParser(interpolation=None)
        config.read(preset_file)
        for name in config.sections():
            if config[name].get("saving_scheme") == saving_scheme and config[name].get("folder_scheme") == folder_scheme:
                return name
    except Exception:
        pass
    return None
