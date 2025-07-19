import os
import re
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import tkinter as tk

LOG_DIR = "logs"
MASTER_LOG_FILE = os.path.join(LOG_DIR, "master_log.log")
GUI_LOG_FILE = os.path.join(LOG_DIR, "gui_log.log")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Logger setup with UTF-8 encoding
logger = logging.getLogger("tagforge")
logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers if this module is reloaded
if not logger.hasHandlers():

    # Formatter that prefixes level in brackets, e.g. [INFO]
    formatter = logging.Formatter('[%(levelname)s] %(message)s')

    master_log_handler = RotatingFileHandler(
        MASTER_LOG_FILE,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    master_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(master_log_handler)

    gui_log_handler = RotatingFileHandler(
        GUI_LOG_FILE,
        maxBytes=5*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    gui_log_handler.setLevel(logging.INFO)
    gui_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(gui_log_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def cleanup_old_logs():
    """Clean up log files older than 30 days."""
    cutoff = datetime.now() - timedelta(days=30)
    for fname in os.listdir(LOG_DIR):
        fpath = os.path.join(LOG_DIR, fname)
        if os.path.isfile(fpath):
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)
                    logger.info(f"Deleted old log file: {fpath}")
            except Exception as e:
                logger.error(f"Failed to remove log file {fpath}: {e}")


def sanitize_message_for_console(msg):
    """
    Sanitize message for console output to avoid Unicode encoding errors.
    """
    replacements = {
        "→": "->",
        "←": "<-",
        "✅": "[OK]",
        "✔": "[OK]",
        "✓": "[OK]",
        "❌": "[ERROR]",
        "⚠": "[WARNING]",
        "—": "-",
        "–": "-",
        "…": "...",
        "®": "(R)",
        "©": "(C)",
        "™": "(TM)",
        "'": "'",
        '"': '"',
    }

    for uni_char, ascii_sub in replacements.items():
        msg = msg.replace(uni_char, ascii_sub)

    # Remove any remaining non-ASCII characters for console output
    return re.sub(r'[^\x00-\x7F]+', '?', msg)


def safe_log_to_backend(msg, level="info"):
    """
    Safely log message to backend logger with Unicode error handling.
    """
    try:
        if level == "debug":
            logger.debug(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "warning":
            logger.warning(msg)
        else:
            logger.info(msg)
    except UnicodeEncodeError:
        safe_msg = sanitize_message_for_console(msg)
        try:
            if level == "debug":
                logger.debug(safe_msg)
            elif level == "error":
                logger.error(safe_msg)
            elif level == "warning":
                logger.warning(safe_msg)
            else:
                logger.info(safe_msg)
        except Exception as e:
            error_msg = "[Unicode encoding error - message lost] - " + str(e)
            try:
                logger.error(error_msg)
            except:
                print(f"CRITICAL: Could not log error - {error_msg}")
    except Exception as e:
        error_msg = "[Logging error] - " + str(e)
        try:
            logger.error(error_msg)
        except:
            print(f"CRITICAL: Could not log error - {error_msg}")


def log_message(log_widget, msg, *, level="info"):
    """
    Central log function for GUI and console output.
    Logs safely to both the Text widget and the backend logger.
    """
    # Log to backend (without manual prefix in msg!)
    safe_log_to_backend(msg, level)

    # Insert message with prefix to GUI log widget, if any
    if log_widget:
        try:
            log_widget.insert("end", f"[{level.upper()}] {msg}\n")
            log_widget.see("end")
        except Exception:
            pass


# Initialize cleanup on import
cleanup_old_logs()
