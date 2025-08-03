import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path
import configparser
import logging
import tkinter.font as tkfont
from scheme_editor.scheme_evaluator import SchemeEvaluator, TOKENS, SAMPLE_METADATA
from scheme_editor.preset_manager import PresetManager

logging.basicConfig(level=logging.ERROR, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class SchemeEditor(tk.Toplevel):
    CONFIG_DIR = Path("config")
    CONFIG_FILE = CONFIG_DIR / "config.ini"
    PRESET_FILE = CONFIG_DIR / "scheme_preset.ini"
    CONFIG_SECTION = "SchemeEditor"

    def __init__(self, master=None, log_callback=None, on_save_callback=None, config_file=None):
        super().__init__(master)
        self.title("Folder Naming Scheme Editor")
        self.geometry("900x650")
        self.minsize(700, 530)
        self.log_callback = log_callback
        self.on_save_callback = on_save_callback

        # Support injected config file or fallback
        self.config_file = Path(config_file) if config_file else self.CONFIG_FILE
        self.config_dir = self.config_file.parent
        self.preset_file = self.config_dir / "scheme_preset.ini"

        self.text_font = tkfont.Font(family="TkDefaultFont", size=11, weight="bold")

        # Track if user has manually modified schemes (to avoid auto-preset selection)
        self.user_modified = False
        self.loading_preset = False  # Flag to prevent marking as user-modified during preset loading
        self.initializing = True  # Flag to prevent any modification events during initial setup

        # Use PresetManager for all preset-related tasks
        self.preset_manager = PresetManager(self.preset_file, log_callback=self._log)

        self._build_widgets()
        self._load_presets()
        self._load_config()
        self._refresh_preview()
        # Bind events AFTER initial setup to avoid spurious modification events
        self._bind_events()
        # Mark initialization as complete AFTER a brief delay to ensure all events are processed
        self.after_idle(self._complete_initialization)

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def normalize_path_slashes(self, path: str) -> str:
        return path.replace("\\", "/") if path else ""

    def _build_widgets(self):
        style = ttk.Style()
        fg = style.lookup("TEntry", "foreground", default="black")
        bg = style.lookup("TEntry", "fieldbackground", default="white")

        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left panel for tokens
        frm_tokens = ttk.Frame(main_frame)
        frm_tokens.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        ttk.Label(frm_tokens, text="Tokens / Functions").pack(anchor="nw", padx=4, pady=4)

        self.lst_tokens = tk.Listbox(
            frm_tokens,
            exportselection=False,
            width=30,
            bg=bg,
            fg=fg,
            highlightbackground=bg,
            highlightcolor=fg,
            selectbackground="#5078ff",
            selectforeground="#ffffff",
            font=self.text_font
        )
        self.lst_tokens.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        for t in TOKENS:
            self.lst_tokens.insert(tk.END, t)
        self.lst_tokens.bind("<Double-Button-1>", self._on_token_insert)

        # Right panel for schemes and controls
        frm_right = ttk.Frame(main_frame)
        frm_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Preset controls at the top
        preset_frame = ttk.Frame(frm_right)
        preset_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(preset_frame, text="Select Preset:").pack(side=tk.LEFT, padx=(0, 4))
        
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(preset_frame, textvariable=self.preset_var, state="readonly", width=20)
        self.preset_combo.pack(side=tk.LEFT, padx=(0, 4))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_selected)

        self.btn_add_preset = ttk.Button(preset_frame, text="Add Preset", command=self._add_preset)
        self.btn_add_preset.pack(side=tk.LEFT, padx=2)

        self.btn_remove_preset = ttk.Button(preset_frame, text="Remove Preset", command=self._remove_preset)
        self.btn_remove_preset.pack(side=tk.LEFT, padx=2)

        # Colors for schemes
        self.saving_bg = "#e6f2ff"   # Light blue background
        self.saving_fg = "#003366"   # Dark blue text

        self.folder_bg = "#fff0e6"   # Light orange background
        self.folder_fg = "#663300"   # Dark orange text

        # Saving Folder Scheme Label and Text with color
        lbl_saving = ttk.Label(frm_right, text="Saving Folder Scheme:")
        lbl_saving.pack(anchor="w")
        lbl_saving.configure(foreground=self.saving_fg)

        self.txt_saving = tk.Text(
            frm_right, height=5, wrap="word",
            background=self.saving_bg,
            foreground=self.saving_fg,
            insertbackground=self.saving_fg,
            font=self.text_font
        )
        self.txt_saving.pack(fill=tk.X, pady=(0, 4))

        # Folder Naming Scheme Label and Text with different color
        lbl_folder = ttk.Label(frm_right, text="Folder Naming Scheme:")
        lbl_folder.pack(anchor="w")
        lbl_folder.configure(foreground=self.folder_fg)

        self.txt_folder = tk.Text(
            frm_right, height=5, wrap="word",
            background=self.folder_bg,
            foreground=self.folder_fg,
            insertbackground=self.folder_fg,
            font=self.text_font
        )
        self.txt_folder.pack(fill=tk.X, pady=(0, 4))

        btn_frame = ttk.Frame(frm_right)
        btn_frame.pack(fill=tk.X, pady=(0, 12))

        self.btn_save = ttk.Button(btn_frame, text="Save Schemes", command=self._save_schemes)
        self.btn_save.pack(side=tk.LEFT, padx=2)

        self.btn_reset = ttk.Button(btn_frame, text="Reset to Default", command=self._reset_to_default)
        self.btn_reset.pack(side=tk.LEFT, padx=2)

        ttk.Label(frm_right, text="Live Preview:").pack(anchor="w")

        self.txt_preview = tk.Text(
            frm_right, height=7, wrap="word",
            state="disabled",
            font=self.text_font
        )
        self.txt_preview.pack(fill=tk.BOTH, expand=True)

        # Define tags for preview coloring
        self.txt_preview.tag_configure("saving_scheme", foreground=self.saving_fg)
        self.txt_preview.tag_configure("folder_scheme", foreground=self.folder_fg)

    def _load_presets(self):
        """Load presets from preset manager and populate combobox."""
        try:
            presets = self.preset_manager.load_presets()
            if not presets:
                presets = ["Default"]
            self.preset_combo['values'] = presets
            # Auto-select Default if no config exists yet
            if not self.config_file.exists():
                self.preset_var.set("Default")
                self.preset_combo.set("Default")
                self._on_preset_selected()
        except Exception as e:
            logger.error(f"Error loading presets: {e}")
            self.preset_combo['values'] = ["Default"]
            if not self.config_file.exists():
                self.preset_var.set("Default")
                self.preset_combo.set("Default")
                self._on_preset_selected()

    def _on_preset_selected(self, event=None):
        """Handle preset selection from dropdown."""
        if self.loading_preset:
            return

        preset_name = self.preset_var.get()
        if not preset_name:
            return

        # Set loading flag
        self.loading_preset = True

        try:
            preset = self.preset_manager.get_preset(preset_name)
            if preset:
                # Clear and update text fields
                self.txt_saving.delete("1.0", tk.END)
                self.txt_saving.insert("1.0", preset["saving_scheme"])

                self.txt_folder.delete("1.0", tk.END)
                self.txt_folder.insert("1.0", preset["folder_scheme"])

                # Ensure the combobox displays the selected preset
                self.preset_combo.set(preset_name)
                
                self._refresh_preview()

        except Exception as e:
            logger.error(f"Error loading preset {preset_name}: {e}")
        finally:
            # Clear loading flag after all pending events are processed
            self.after_idle(self._clear_loading_flag)

    def _add_preset(self):
        """Add a new preset with current scheme values."""
        name = simpledialog.askstring("Add Preset", "Enter preset name:")
        if not name or not name.strip():
            return

        name = name.strip()

        try:
            existing_presets = self.preset_manager.load_presets()
            if name in existing_presets:
                if not messagebox.askyesno("Preset Exists", f"Preset '{name}' already exists. Overwrite?"):
                    return

            self.preset_manager.add_preset(
                name,
                self.txt_saving.get("1.0", "end-1c").strip(),
                self.txt_folder.get("1.0", "end-1c").strip()
            )

            self._load_presets()
            self.preset_var.set(name)
            self.preset_combo.set(name)

        except Exception as e:
            logger.error(f"Error adding preset: {e}")
            messagebox.showerror("Error", f"Failed to add preset: {e}")

    def _remove_preset(self):
        """Remove the currently selected preset."""
        preset_name = self.preset_var.get()
        if not preset_name:
            messagebox.showwarning("No Selection", "Please select a preset to remove.")
            return

        if preset_name == "Default":
            messagebox.showwarning("Cannot Remove", "Cannot remove the Default preset.")
            return

        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete preset '{preset_name}'?"):
            return

        try:
            self.preset_manager.remove_preset(preset_name)
            self._load_presets()
            self.preset_var.set("")
            self.preset_combo.set("")

        except Exception as e:
            logger.error(f"Error removing preset: {e}")
            messagebox.showerror("Error", f"Failed to remove preset: {e}")

    def _set_default_texts(self):
        self.txt_saving.delete("1.0", tk.END)
        self.txt_saving.insert("1.0", "%artist%/$year(%date%)")
        self.txt_folder.delete("1.0", tk.END)
        self.txt_folder.insert("1.0", "%date% - %venue% - %city% [%format%] [%additional%]")

    def _bind_events(self):
        self.txt_saving.bind("<<Modified>>", self._on_text_modified)
        self.txt_folder.bind("<<Modified>>", self._on_text_modified)

    def _on_text_modified(self, event):
        # Always clear the modified flag first
        event.widget.edit_modified(False)

        # If we're still initializing or loading a preset, ignore this modification
        if self.initializing or self.loading_preset:
            return

        # Only mark as user modified if we're not in the middle of loading
        self.user_modified = True
        if self.preset_var.get():
            self.preset_var.set("")
            self.preset_combo.set("")

        self._refresh_preview()

    def _on_token_insert(self, event):
        token = self.lst_tokens.get("active")
        target = self.focus_get() if self.focus_get() in (self.txt_saving, self.txt_folder) else self.txt_folder
        target.insert("insert", token)
        self._refresh_preview()

    def _refresh_preview(self):
        saving = self.txt_saving.get("1.0", "end-1c").strip()
        folder = self.txt_folder.get("1.0", "end-1c").strip()
        md = SAMPLE_METADATA.copy()

        # Evaluate folder scheme first to get the foldername token value
        folder_eval = SchemeEvaluator(md).eval(folder).replace("\\", "/").rstrip("/")
        md["foldername"] = folder_eval  # Inject foldername into metadata

        # Evaluate saving scheme with extended metadata including foldername and currentfoldername
        saving_eval = SchemeEvaluator(md).eval(saving).replace("\\", "/").rstrip("/")

        # Compose full path for preview
        if not saving_eval or saving_eval.lower() == "(root)":
            preview_path = folder_eval
            saving_part = ""
            folder_part = preview_path
        else:
            # Use pathlib to join, then normalize
            preview_path = Path(saving_eval) / Path(folder_eval)
            preview_path = str(preview_path).replace("\\", "/").rstrip("/")
            saving_part = str(Path(saving_eval)).replace("\\", "/").rstrip("/")
            folder_part = str(Path(folder_eval)).replace("\\", "/").rstrip("/")

        # Insert with tags for color coding
        self.txt_preview.config(state="normal")
        self.txt_preview.delete("1.0", tk.END)

        if saving_part:
            self.txt_preview.insert(tk.END, saving_part, "saving_scheme")
            if folder_part:
                self.txt_preview.insert(tk.END, "/")
                self.txt_preview.insert(tk.END, folder_part, "folder_scheme")
        else:
            self.txt_preview.insert(tk.END, folder_part, "folder_scheme")

        self.txt_preview.config(state="disabled")

    def _reset_to_default(self):
        # Set loading flag
        self.loading_preset = True
        
        try:
            self._set_default_texts()
            self.preset_var.set("Default")
            self.preset_combo.set("Default")
            self._refresh_preview()
            self.user_modified = False
        finally:
            # Clear loading flag after all pending events are processed
            self.after_idle(self._clear_loading_flag)

    def _clear_loading_flag(self):
        """Helper method to clear the loading_preset flag."""
        self.loading_preset = False

    def _complete_initialization(self):
        """Helper method to mark initialization as complete."""
        self.initializing = False

    def _load_config(self):
        """Load saved schemes from config.ini, but don't auto-select preset if user has custom schemes."""
        if not self.config_file.exists():
            # If no config exists, load Default preset
            if not self.preset_var.get():
                self.preset_var.set("Default")
                self.preset_combo.set("Default")
                self._on_preset_selected()
            return

        config = configparser.ConfigParser(interpolation=None)
        config.read(self.config_file)

        if self.CONFIG_SECTION in config:
            section = config[self.CONFIG_SECTION]
            saving_scheme = section.get("saving_scheme", "")
            folder_scheme = section.get("folder_scheme", "")

            if saving_scheme or folder_scheme:
                # Set loading flag during config load
                self.loading_preset = True

                try:
                    self.txt_saving.delete("1.0", tk.END)
                    self.txt_saving.insert("1.0", saving_scheme)
                    self.txt_folder.delete("1.0", tk.END)
                    self.txt_folder.insert("1.0", folder_scheme)

                    # Check if current schemes match any preset
                    preset_match = self.preset_manager.find_matching_preset(saving_scheme, folder_scheme)
                    if preset_match:
                        self.preset_var.set(preset_match)
                        self.preset_combo.set(preset_match)
                    else:
                        # User has custom schemes, don't select any preset
                        self.preset_var.set("")
                        self.preset_combo.set("")
                        self.user_modified = True
                finally:
                    # Clear loading flag
                    self.loading_preset = False
            else:
                # Empty schemes in config, load Default
                if not self.preset_var.get():
                    self.preset_var.set("Default")
                    self.preset_combo.set("Default")
                    self._on_preset_selected()
        else:
            # No section in config, load Default
            if not self.preset_var.get():
                self.preset_var.set("Default")
                self.preset_combo.set("Default")
                self._on_preset_selected()

    def _save_schemes(self):
        saving_scheme = self.txt_saving.get("1.0", "end-1c").strip()
        folder_scheme = self.txt_folder.get("1.0", "end-1c").strip()
        md = SAMPLE_METADATA.copy()
        folder_eval = SchemeEvaluator(md).eval(folder_scheme).replace("\\", "/").rstrip("/")
        md["foldername"] = folder_eval
        saving_eval = SchemeEvaluator(md).eval(saving_scheme).replace("\\", "/").rstrip("/")
        if not saving_eval or saving_eval.lower() == "(root)":
            preview_path = folder_eval
        else:
            preview_path = str(Path(saving_eval) / Path(folder_eval)).replace("\\", "/").rstrip("/")

        self._save_config()

        # Update main config.ini
        self._update_main_config(saving_scheme, folder_scheme)

        if self.on_save_callback:
            # Pass evaluated live preview as third param
            self.on_save_callback(saving_scheme, folder_scheme, preview_path)
        self.destroy()

    def _update_main_config(self, saving_scheme, folder_scheme):
        """Update the main config.ini file with current schemes."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            main_config = configparser.ConfigParser(interpolation=None)
            if self.config_file.exists():
                main_config.read(self.config_file)

            if self.CONFIG_SECTION not in main_config:
                main_config.add_section(self.CONFIG_SECTION)

            main_config.set(self.CONFIG_SECTION, "saving_scheme", saving_scheme)
            main_config.set(self.CONFIG_SECTION, "folder_scheme", folder_scheme)

            with open(self.config_file, "w", encoding="utf-8") as f:
                main_config.write(f)

        except Exception as e:
            logger.error(f"Error updating main config: {e}")

    def _save_config(self):
        """Save current schemes to config file."""
        try:
            self.config_dir.mkdir(exist_ok=True)
            config = configparser.ConfigParser(interpolation=None)

            # Read existing config first
            if self.config_file.exists():
                config.read(self.config_file)

            # Add section if it doesn't exist
            if self.CONFIG_SECTION not in config:
                config.add_section(self.CONFIG_SECTION)

            # Set the values
            config.set(self.CONFIG_SECTION, "saving_scheme", self.txt_saving.get("1.0", "end-1c"))
            config.set(self.CONFIG_SECTION, "folder_scheme", self.txt_folder.get("1.0", "end-1c"))

            with open(self.config_file, "w", encoding="utf-8") as f:
                config.write(f)

        except Exception as e:
            logger.error(f"Error saving config: {e}")


if __name__ == "__main__":
    SchemeEditor().mainloop()