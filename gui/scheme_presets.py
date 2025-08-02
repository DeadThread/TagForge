import configparser
from pathlib import Path

class SchemePresets:
    def __init__(self, preset_file, config_dir):
        self.preset_file = Path(preset_file)
        self.config_dir = Path(config_dir)
        self._ensure_preset_file()

    def _ensure_preset_file(self):
        if not self.preset_file.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            config = configparser.ConfigParser(interpolation=None)
            config["Default"] = {
                "saving_scheme": "%artist%/$year(%date%)",
                "folder_scheme": "%date% - %venue% - %city% [%format%] [%additional%]"
            }
            with open(self.preset_file, "w", encoding="utf-8") as f:
                config.write(f)

    def load_presets(self):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        return list(config.sections())

    def get_preset(self, name):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        if name in config:
            return config[name].get("saving_scheme", ""), config[name].get("folder_scheme", "")
        return "", ""

    def add_preset(self, name, saving_scheme, folder_scheme, overwrite=False):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        if name in config and not overwrite:
            return False
        config[name] = {
            "saving_scheme": saving_scheme,
            "folder_scheme": folder_scheme
        }
        with open(self.preset_file, "w", encoding="utf-8") as f:
            config.write(f)
        return True

    def remove_preset(self, name):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        if name in config:
            config.remove_section(name)
            with open(self.preset_file, "w", encoding="utf-8") as f:
                config.write(f)
            return True
        return False

    def find_matching_preset(self, saving_scheme, folder_scheme):
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.preset_file)
        for preset_name in config.sections():
            if (config[preset_name].get("saving_scheme", "") == saving_scheme and
                config[preset_name].get("folder_scheme", "") == folder_scheme):
                return preset_name
        return None