# config_utils.py
import configparser
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = Path("config")
CONFIG_FILE = CONFIG_DIR / "config.ini"
CONFIG_SECTION = "SchemeEditor"

def load_saved_schemes():
    schemes = {
        "saving_scheme": "%artist%/$year(%date%)",
        "folder_scheme": "%date% - %venue% - %city% [%format%] [%additional%]",
    }

    if CONFIG_FILE.exists():
        config = configparser.ConfigParser(interpolation=None)
        try:
            config.read(CONFIG_FILE)
            if CONFIG_SECTION in config:
                schemes["saving_scheme"] = config[CONFIG_SECTION].get("saving_scheme", schemes["saving_scheme"])
                schemes["folder_scheme"] = config[CONFIG_SECTION].get("folder_scheme", schemes["folder_scheme"])
                logger.info(f"Loaded saved schemes from {CONFIG_FILE}")
                logger.info(f"→ Saving Scheme: {schemes['saving_scheme']}")
                logger.info(f"→ Folder Scheme: {schemes['folder_scheme']}")
        except Exception as e:
            logger.warning(f"Failed to load saved schemes: {e}")
    else:
        logger.info(f"No scheme config found at {CONFIG_FILE}, using defaults")

    return schemes
