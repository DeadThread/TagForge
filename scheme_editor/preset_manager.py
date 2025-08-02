import configparser
from pathlib import Path

class PresetManager:
    def __init__(self, preset_file: Path, log_callback=None):
        self.preset_file = preset_file
        self.log_callback = log_callback
        self._ensure_preset_file()

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def _ensure_preset_file(self):
        """Create scheme_preset.ini with default preset if it doesn't exist."""
        if not self.preset_file.exists():
            self.preset_file.parent.mkdir(parents=True, exist_ok=True)
            config = configparser.ConfigParser(interpolation=None)
            config["Default"] = {
                "saving_scheme": "%artist%/$year(%date%)",
                "folder_scheme": "%date% - %venue% - %city% [%format%] [%additional%]"
            }
            with open(self.preset_file, "w", encoding="utf-8") as f:
                config.write(f)
            self._log("Created scheme_preset.ini with default preset")

    def load_presets(self):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        return list(config.sections())

    def get_preset(self, preset_name):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        if preset_name in config:
            return {
                "saving_scheme": config[preset_name].get("saving_scheme", ""),
                "folder_scheme": config[preset_name].get("folder_scheme", "")
            }
        return None

    def add_preset(self, name, saving_scheme, folder_scheme):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)

        config[name] = {
            "saving_scheme": saving_scheme,
            "folder_scheme": folder_scheme
        }

        with open(self.preset_file, "w", encoding="utf-8") as f:
            config.write(f)

        self._log(f"Added/Updated preset: {name}")

    def remove_preset(self, name):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)

        if name in config:
            config.remove_section(name)
            with open(self.preset_file, "w", encoding="utf-8") as f:
                config.write(f)
            self._log(f"Removed preset: {name}")

    def find_matching_preset(self, saving_scheme, folder_scheme):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        for preset_name in config.sections():
            if (config[preset_name].get("saving_scheme", "") == saving_scheme and
                config[preset_name].get("folder_scheme", "") == folder_scheme):
                return preset_name
        return None
