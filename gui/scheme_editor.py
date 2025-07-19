import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
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
    CONFIG_SECTION = "SchemeEditor"

    def __init__(self, master=None, log_callback=None, on_save_callback=None, config_file=None):
        super().__init__(master)
        self.title("Folder Naming Scheme Editor")
        self.geometry("900x600")
        self.minsize(700, 480)
        self.log_callback = log_callback
        self.on_save_callback = on_save_callback

        # Support injected config file or fallback
        self.config_file = Path(config_file) if config_file else self.CONFIG_FILE
        self.config_dir = self.config_file.parent

        self.text_font = tkfont.Font(family="TkDefaultFont", size=11, weight="bold")

        self._build_widgets()
        self._set_default_texts()
        self._bind_events()
        self._load_config()
        self._refresh_preview()

    def _log(self, msg):
        if not SUPPRESS_LOGGING:
            logger.info(msg)
            if self.log_callback:
                self.log_callback(msg)

    def normalize_path_slashes(self, path: str) -> str:
        return path.replace("\\", "/") if path else ""

    def _build_widgets(self):
        style = ttk.Style()
        fg = style.lookup("TEntry", "foreground", default="black")
        bg = style.lookup("TEntry", "fieldbackground", default="white")

        frm_tokens = ttk.Frame(self)
        frm_tokens.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

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

        frm_right = ttk.Frame(self)
        frm_right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

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
        self._set_default_texts()
        self._refresh_preview()

    def _load_config(self):
        if not self.config_file.exists():
            return
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.config_file)
        if self.CONFIG_SECTION in config:
            section = config[self.CONFIG_SECTION]
            self.txt_saving.delete("1.0", tk.END)
            self.txt_saving.insert("1.0", section.get("saving_scheme", ""))
            self.txt_folder.delete("1.0", tk.END)
            self.txt_folder.insert("1.0", section.get("folder_scheme", ""))

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
        if self.on_save_callback:
            # Pass evaluated live preview as third param
            self.on_save_callback(saving_scheme, folder_scheme, preview_path)
        self.destroy()


    def _save_config(self):
        self.config_dir.mkdir(exist_ok=True)
        config = configparser.ConfigParser(interpolation=None)
        config[self.CONFIG_SECTION] = {
            "saving_scheme": self.txt_saving.get("1.0", "end-1c"),
            "folder_scheme": self.txt_folder.get("1.0", "end-1c"),
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            config.write(f)


if __name__ == "__main__":
    SchemeEditor().mainloop()
