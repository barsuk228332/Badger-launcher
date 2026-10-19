import requests
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from config import COVERS_DIR, ConfigManager

BASE_URL = "https://www.steamgriddb.com/api/v2"


class CoverDownloadWorker(QThread):
    finished = Signal(str, str)
    error = Signal(str)

    def __init__(self, game_name: str, api_key: str = None):
        super().__init__()
        self.game_name = game_name
        self.api_key = api_key or ConfigManager.get_api_key()

    def run(self):
        if not self.api_key:
            self.error.emit("API-ключ SteamGridDB не задан.")
            return

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            search_url = f"{BASE_URL}/search/autocomplete/{self.game_name}"
            resp = requests.get(search_url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if not data.get("success") or not data.get("data"):
                self.error.emit(f"Игра «{self.game_name}» не найдена на SteamGridDB")
                return

            game_id = data["data"][0]["id"]

            grids_url = f"{BASE_URL}/grids/game/{game_id}?dimensions=600x900"
            resp = requests.get(grids_url, headers=headers, timeout=10)
            resp.raise_for_status()
            grids_data = resp.json()

            if not grids_data.get("success") or not grids_data.get("data"):
                self.error.emit("Для игры нет подходящих постеров")
                return

            cover_url = grids_data["data"][0]["url"]
            ext = cover_url.split(".")[-1].split("?")[0]
            if ext not in ["jpg", "jpeg", "png", "webp"]:
                ext = "jpg"

            safe_name = "".join(
                c for c in self.game_name if c.isalnum() or c in " _-"
            ).rstrip()
            target_path = COVERS_DIR / f"{safe_name}.{ext}"

            img_resp = requests.get(cover_url, timeout=15)
            img_resp.raise_for_status()

            with open(target_path, "wb") as f:
                f.write(img_resp.content)

            self.finished.emit(self.game_name, str(target_path))
        except Exception as e:
            self.error.emit(f"Ошибка загрузки обложки: {e}")