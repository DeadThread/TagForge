import tkinter as tk
from utils.logger import safe_log_to_backend

class GuiLogger:
    """
    GUI-aware logger that buffers messages until the Tk Text widget is ready.
    Delegates real logging to utils.logger.safe_log_to_backend.
    """
    def __init__(self):
        self._log_widget = None
        self._pending_logs = []  # (msg, level, tag)

    def attach(self, text_widget: tk.Text):
        self._log_widget = text_widget
        self._flush_pending()

    def log(self, msg: str, level: str = "info", tag: str = None):
        # Always send to backend logger
        safe_log_to_backend(msg, level)

        if level == "debug":
            return  # Skip debug messages in GUI

        if self._log_widget:
            try:
                tag_to_use = tag or level  # fallback to level as tag
                self._log_widget.config(state="normal")
                self._log_widget.insert(tk.END, msg + "\n", (tag_to_use,))
                self._log_widget.config(state="disabled")
                self._log_widget.see(tk.END)
            except Exception:
                pass
        else:
            self._pending_logs.append((msg, level, tag))

    def _flush_pending(self):
        if not self._log_widget:
            return

        self._log_widget.config(state="normal")
        for msg, level, tag in self._pending_logs:
            if level == "debug":
                continue
            try:
                tag_to_use = tag or level
                self._log_widget.insert(tk.END, msg + "\n", (tag_to_use,))
            except Exception:
                pass
        self._log_widget.config(state="disabled")
        self._log_widget.see(tk.END)
        self._pending_logs.clear()

    def buffer(self, msg: str, level: str = "info", tag: str = None):
        if level != "debug":
            self._pending_logs.append((msg, level, tag))

    def flush(self):
        self._flush_pending()
