import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from pathlib import Path
import configparser
import logging
import tkinter.font as tkfont

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

SUPPRESS_LOGGING = False


class SchemeEvaluator:
    TOKEN_RE = re.compile(r'%([a-zA-Z0-9_]+)%')
    FUNC_RE = re.compile(r'\$(\w+)\((.*?)\)')

    def __init__(self, metadata):
        # Copy metadata to avoid mutating original
        self.metadata = dict(metadata)
        # Inject currentfoldername if possible
        self._inject_currentfoldername()

    def _inject_currentfoldername(self):
        """
        If metadata contains a 'current_folder' key with a path,
        extract the last folder name and set 'currentfoldername' token.
        """
        folder_path = self.metadata.get("current_folder", "")
        if folder_path:
            # Normalize path and get last folder name
            folder_name = Path(folder_path).name
            self.metadata["currentfoldername"] = folder_name
        else:
            # Ensure token exists as empty string if no current_folder key
            self.metadata.setdefault("currentfoldername", "")

    def eval(self, text):
        for _ in range(20):
            new = self._eval_once(text)
            if new == text:
                break
            text = new
        return text

    def _eval_once(self, text):
        def token_repl(m):
            token = m.group(1)
            # Handle numbered tokens like formatN2, additionalN3, sourceN4 etc.
            m2 = re.match(r'^(format|additional|source)(N(\d+))?$', token)
            if m2:
                base = m2.group(1)
                n_part = m2.group(2)  # like 'N3' or None
                n_num_str = m2.group(3)  # '3' or None
                values = self.metadata.get(base + "N", [])
                if isinstance(values, str):
                    values = [values]
                if n_part is None:
                    # %format% etc.
                    return self.metadata.get(base, "")
                elif n_num_str is None:
                    # %formatN%
                    return ", ".join(values)
                else:
                    # %formatN2%
                    idx = int(n_num_str) - 1
                    return values[idx] if 0 <= idx < len(values) else ""
            else:
                val = self.metadata.get(token, "")
                if isinstance(val, list):
                    return ", ".join(val)
                return val

        def func_repl(m):
            fname, fargs = m.group(1), m.group(2)
            args = self._split_args(fargs)
            args = [self.eval(arg) for arg in args]
            return self._apply_func(fname, args)

        text = self.TOKEN_RE.sub(token_repl, text)
        text = self.FUNC_RE.sub(func_repl, text)
        return text

    def _split_args(self, argstr):
        args, current, depth, i = [], [], 0, 0
        while i < len(argstr):
            c = argstr[i]
            if c == ',' and depth == 0:
                args.append(''.join(current).strip())
                current = []
            else:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                current.append(c)
            i += 1
        if current:
            args.append(''.join(current).strip())
        return args

    def _apply_func(self, fname, args):
        def to_num(x): return float(x) if x.replace('.', '', 1).isdigit() else 0.0
        def to_bool(x): return x == "1"
        if fname == "upper" and len(args) == 1: return args[0].upper()
        if fname == "lower" and len(args) == 1: return args[0].lower()
        if fname == "title" and len(args) == 1: return args[0].title()
        if fname == "substr" and (2 <= len(args) <= 3):
            s, start = args[0], int(args[1])
            return s[start:int(args[2])] if len(args) == 3 else s[start:]
        if fname == "left" and len(args) == 2: return args[0][:int(args[1])]
        if fname == "right" and len(args) == 2: return args[0][-int(args[1]):]
        if fname == "replace" and len(args) == 3: return args[0].replace(args[1], args[2])
        if fname == "len" and len(args) == 1: return str(len(args[0]))
        if fname == "pad" and (2 <= len(args) <= 3):
            s, n, ch = args[0], int(args[1]), (args[2] if len(args) == 3 else " ")[0]
            return s.ljust(n, ch) if len(s) < n else s[:n]
        if fname == "add" and len(args) == 2: return str(to_num(args[0]) + to_num(args[1]))
        if fname == "sub" and len(args) == 2: return str(to_num(args[0]) - to_num(args[1]))
        if fname == "mul" and len(args) == 2: return str(to_num(args[0]) * to_num(args[1]))
        if fname == "div" and len(args) == 2:
            denom = to_num(args[1])
            return str(to_num(args[0]) / denom) if denom != 0 else "0"
        if fname == "eq" and len(args) == 2: return "1" if args[0] == args[1] else "0"
        if fname == "lt" and len(args) == 2: return "1" if to_num(args[0]) < to_num(args[1]) else "0"
        if fname == "gt" and len(args) == 2: return "1" if to_num(args[0]) > to_num(args[1]) else "0"
        if fname == "and": return "1" if all(to_bool(a) for a in args) else "0"
        if fname == "or": return "1" if any(to_bool(a) for a in args) else "0"
        if fname == "not" and len(args) == 1: return "1" if not to_bool(args[0]) else "0"
        if fname == "datetime" and len(args) == 0: return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if fname == "year" and len(args) == 1: return args[0][:4]
        if fname == "month" and len(args) == 1: return args[0][5:7]
        if fname == "day" and len(args) == 1: return args[0][8:10]
        if fname == "if" and len(args) == 3: return args[1] if args[0] == "1" else args[2]
        if fname == "if2" and len(args) >= 2:
            for val in args[:-1]:
                if val: return val
            return args[-1]
        return ""

TOKENS = [
    "%artist%", "%date%", "%venue%", "%city%", "%format%", "%additional%", "%source%", "%foldername%", "%currentfoldername%",
    "%formatN%", "%formatN2%", "%formatN3%", "%formatN4%", "%formatN5%",
    "%additionalN%", "%additionalN2%", "%additionalN3%", "%additionalN4%", "%additionalN5%",
    "%sourceN%", "%sourceN2%", "%sourceN3%", "%sourceN4%", "%sourceN5%",
    "$upper(text)", "$lower(text)", "$title(text)", "$substr(text,start[,end])",
    "$left(text,n)", "$right(text,n)", "$replace(text,search,replace)",
    "$len(text)", "$pad(text,n,ch)", "$add(x,y)", "$sub(x,y)", "$mul(x,y)",
    "$div(x,y)", "$eq(x,y)", "$lt(x,y)", "$gt(x,y)", "$and(x,y,…)", "$or(x,y,…)",
    "$not(x)", "$datetime()", "$year(date)", "$month(date)", "$day(date)",
    "$if(cond,T,F)", "$if2(v1,v2,…,fallback)",
]


SAMPLE_METADATA = {
    "artist": "Phish", "venue": "Madison Square Garden", "city": "New York, NY",
    "date": "1995-12-31", "source": "SBD", "format": "FLAC24", "additional": "NYE95",
    "formatN": ["FLAC24", "MP3_320"], "additionalN": ["NYE95", "Remastered"],
    "sourceN": ["SBD", "Audience"], "year": "1995",
    "current_folder": "ph1995-12-31 - Madison Square Garden - New York, NY"  # Example current folder path for demo
}


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

        self._ensure_preset_file()
        self._build_widgets()
        self._load_presets()
        self._load_config()
        self._refresh_preview()
        self._bind_events()

    def _log(self, msg):
        if not SUPPRESS_LOGGING:
            logger.info(msg)
            if self.log_callback:
                self.log_callback(msg)

    def normalize_path_slashes(self, path: str) -> str:
        return path.replace("\\", "/") if path else ""

    def _ensure_preset_file(self):
        """Create scheme_preset.ini with default preset if it doesn't exist."""
        if not self.preset_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            config = configparser.ConfigParser(interpolation=None)
            
            # Add default preset
            config["Default"] = {
                "saving_scheme": "%artist%/$year(%date%)",
                "folder_scheme": "%date% - %venue% - %city% [%format%] [%additional%]"
            }
            
            with open(self.preset_file, "w", encoding="utf-8") as f:
                config.write(f)
            self._log("Created scheme_preset.ini with default preset")

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
        """Load presets from preset file and populate combobox."""
        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(self.preset_file)
            
            presets = list(config.sections())
            if not presets:
                presets = ["Default"]
            
            self.preset_combo['values'] = presets
            
            # Auto-select Default if no config exists yet
            if not self.config_file.exists():
                self.preset_var.set("Default")
                self._on_preset_selected()
            
        except Exception as e:
            self._log(f"Error loading presets: {e}")
            self.preset_combo['values'] = ["Default"]
            # Auto-select Default on error too
            if not self.config_file.exists():
                self.preset_var.set("Default")
                self._on_preset_selected()

    def _on_preset_selected(self, event=None):
        """Handle preset selection from dropdown."""
        if self.loading_preset:
            return
            
        preset_name = self.preset_var.get()
        if not preset_name:
            return
            
        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(self.preset_file)
            
            if preset_name in config:
                self.loading_preset = True  # Prevent marking as user-modified
                
                saving_scheme = config[preset_name].get("saving_scheme", "")
                folder_scheme = config[preset_name].get("folder_scheme", "")
                
                self.txt_saving.delete("1.0", tk.END)
                self.txt_saving.insert("1.0", saving_scheme)
                
                self.txt_folder.delete("1.0", tk.END)
                self.txt_folder.insert("1.0", folder_scheme)
                
                self._refresh_preview()
                self._log(f"Loaded preset: {preset_name}")
                
                self.loading_preset = False
        except Exception as e:
            self._log(f"Error loading preset {preset_name}: {e}")
            self.loading_preset = False

    def _add_preset(self):
        """Add a new preset with current scheme values."""
        name = simpledialog.askstring("Add Preset", "Enter preset name:")
        if not name or not name.strip():
            return
            
        name = name.strip()
        
        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(self.preset_file)
            
            # Check if preset already exists
            if name in config:
                if not messagebox.askyesno("Preset Exists", f"Preset '{name}' already exists. Overwrite?"):
                    return
            
            # Add/update preset
            config[name] = {
                "saving_scheme": self.txt_saving.get("1.0", "end-1c").strip(),
                "folder_scheme": self.txt_folder.get("1.0", "end-1c").strip()
            }
            
            with open(self.preset_file, "w", encoding="utf-8") as f:
                config.write(f)
            
            # Refresh preset list and select the new preset
            self._load_presets()
            self.preset_var.set(name)
            
            self._log(f"Added preset: {name}")
            
        except Exception as e:
            self._log(f"Error adding preset: {e}")
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
            config = configparser.ConfigParser(interpolation=None)
            config.read(self.preset_file)
            
            if preset_name in config:
                config.remove_section(preset_name)
                
                with open(self.preset_file, "w", encoding="utf-8") as f:
                    config.write(f)
                
                # Refresh preset list and clear selection
                self._load_presets()
                self.preset_var.set("")
                
                self._log(f"Removed preset: {preset_name}")
            
        except Exception as e:
            self._log(f"Error removing preset: {e}")
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
        event.widget.edit_modified(False)
        
        # Only mark as user-modified if we're not loading a preset
        if not self.loading_preset:
            self.user_modified = True
            # Clear preset selection since user has manually modified
            if self.preset_var.get():
                self.preset_var.set("")
        
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
        self.loading_preset = True
        self._set_default_texts()
        self.preset_var.set("Default")
        self._refresh_preview()
        self.user_modified = False
        self.loading_preset = False

    def _load_config(self):
        """Load saved schemes from config.ini, but don't auto-select preset if user has custom schemes."""
        if not self.config_file.exists():
            # If no config exists, load Default preset
            if not self.preset_var.get():
                self.preset_var.set("Default")
                self._on_preset_selected()
            return
            
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.config_file)
        
        if self.CONFIG_SECTION in config:
            section = config[self.CONFIG_SECTION]
            saving_scheme = section.get("saving_scheme", "")
            folder_scheme = section.get("folder_scheme", "")
            
            if saving_scheme or folder_scheme:
                self.loading_preset = True
                
                self.txt_saving.delete("1.0", tk.END)
                self.txt_saving.insert("1.0", saving_scheme)
                self.txt_folder.delete("1.0", tk.END)
                self.txt_folder.insert("1.0", folder_scheme)
                
                # Check if current schemes match any preset
                preset_match = self._find_matching_preset(saving_scheme, folder_scheme)
                if preset_match:
                    self.preset_var.set(preset_match)
                else:
                    # User has custom schemes, don't select any preset
                    self.preset_var.set("")
                    self.user_modified = True
                
                self.loading_preset = False
            else:
                # Empty schemes in config, load Default
                if not self.preset_var.get():
                    self.preset_var.set("Default")
                    self._on_preset_selected()
        else:
            # No section in config, load Default
            if not self.preset_var.get():
                self.preset_var.set("Default")
                self._on_preset_selected()

    def _find_matching_preset(self, saving_scheme, folder_scheme):
        """Find if current schemes match any existing preset."""
        try:
            config = configparser.ConfigParser(interpolation=None)
            config.read(self.preset_file)
            
            for preset_name in config.sections():
                if (config[preset_name].get("saving_scheme", "") == saving_scheme and
                    config[preset_name].get("folder_scheme", "") == folder_scheme):
                    return preset_name
        except Exception:
            pass
        return None

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
                
            self._log("Updated main config.ini with current schemes")
            
        except Exception as e:
            self._log(f"Error updating main config: {e}")
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}")

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
                
            self._log("Saved schemes to config file")
            
        except Exception as e:
            self._log(f"Error saving config: {e}")
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    SchemeEditor().mainloop()