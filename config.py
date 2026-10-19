import os
import json
from pathlib import Path

APP_NAME = "badger_launcher"
CONFIG_DIR = Path.home() / ".config" / APP_NAME
DATA_DIR = Path.home() / ".local/share" / APP_NAME
RUNNERS_DIR = DATA_DIR / "runners"
COVERS_DIR = DATA_DIR / "covers"
PREFIXES_DIR = Path.home() / "Badger"
GAMES_FILE = CONFIG_DIR / "games.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

COMPAT_DIRS = [
    RUNNERS_DIR,
    Path.home() / ".local/share/Steam/compatibilitytools.d",
    Path("/usr/share/steam/compatibilitytools.d"),
    Path("/usr/share/compatibilitytools.d"),
]

for d in [CONFIG_DIR, DATA_DIR, RUNNERS_DIR, COVERS_DIR, PREFIXES_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class ConfigManager:
    @staticmethod
    def load_games() -> list:
        if not GAMES_FILE.exists():
            return []
        try:
            with open(GAMES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def save_games(games: list):
        with open(GAMES_FILE, "w", encoding="utf-8") as f:
            json.dump(games, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_settings() -> dict:
        default_settings = {
            "default_prefix_dir": str(PREFIXES_DIR),
            "default_runner": "System Wine",
            "steamgriddb_key": "",
            "use_discrete_gpu": True,
            "close_on_launch": False,
            "wayland_driver": False,
            "global_env": "",
            "theme": "Adwaita Dark",
            "ui_mode": "Карусель",
        }
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    default_settings.update(json.load(f))
            except Exception:
                pass
        return default_settings

    @staticmethod
    def save_settings(settings: dict):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)

    @staticmethod
    def get_api_key() -> str:
        return ConfigManager.load_settings().get("steamgriddb_key", "")

    @staticmethod
    def set_api_key(key: str):
        settings = ConfigManager.load_settings()
        settings["steamgriddb_key"] = key.strip()
        ConfigManager.save_settings(settings)

    @staticmethod
    def get_installed_runners() -> list[dict]:
        runners = [{"name": "System Wine", "path": "System Wine"}]
        seen_paths = set()

        for c_dir in COMPAT_DIRS:
            if c_dir.exists():
                for item in sorted(c_dir.iterdir()):
                    item_str = str(item)
                    if item.is_dir() and item_str not in seen_paths:
                        if (item / "proton").exists() or (item / "files").exists():
                            runners.append({"name": item.name, "path": item_str})
                            seen_paths.add(item_str)

        cachy_direct = Path("/usr/share/proton-cachyos")
        if cachy_direct.exists() and str(cachy_direct) not in seen_paths:
            runners.append({"name": cachy_direct.name, "path": str(cachy_direct)})

        return runners