import os
import shutil
import subprocess
import tempfile
import requests
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from config import RUNNERS_DIR

PROTON_SOURCES = {
    "Proton-CachyOS": {
        "api_url": "https://api.github.com/repos/CachyOS/proton-cachyos/releases?per_page=15"
    },
    "GE-Proton": {
        "api_url": "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases?per_page=15"
    },
    "Proton-Wineland (Salkim)": {
        "api_url": "https://api.github.com/repos/nanomatters/proton-salkim/releases?per_page=15"
    },
    "DW-Proton": {
        "api_url": "https://dawn.wine/api/v1/repos/dawn-winery/dwproton/releases?limit=15"
    },
}


class FetchReleasesWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, source_name: str):
        super().__init__()
        self.source_name = source_name

    def run(self):
        source = PROTON_SOURCES.get(self.source_name)
        if not source:
            self.error.emit("Неизвестный источник Proton")
            return

        try:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "BadgerLauncher/1.0",
            }
            resp = requests.get(source["api_url"], headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            releases = []
            for rel in data[:15]:
                tag = rel.get("tag_name") or rel.get("name", "Unknown")
                assets = rel.get("assets", [])
                download_url = None
                asset_name = None
                asset_size = 0

                for asset in assets:
                    name = asset.get("name", "")
                    if any(
                        name.endswith(ext)
                        for ext in [".tar.gz", ".tar.xz", ".tar.zst"]
                    ) and not name.endswith(".sha512sum"):
                        download_url = asset.get("browser_download_url")
                        asset_name = name
                        asset_size = asset.get("size", 0)
                        break

                if download_url:
                    releases.append({
                        "tag": tag,
                        "name": rel.get("name") or tag,
                        "asset_name": asset_name,
                        "url": download_url,
                        "size_mb": round(asset_size / (1024 * 1024), 1)
                        if asset_size
                        else 0,
                    })

            self.finished.emit(releases)
        except Exception as e:
            self.error.emit(f"Ошибка получения релизов: {e}")


class DownloadProtonWorker(QThread):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, url: str, asset_name: str):
        super().__init__()
        self.url = url
        self.asset_name = asset_name

    def run(self):
        tmp_dir = Path(tempfile.mkdtemp(prefix="proton_dl_"))
        archive_path = tmp_dir / self.asset_name

        try:
            self.status.emit(f"Скачивание {self.asset_name}...")
            with requests.get(self.url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0

                with open(archive_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                self.progress.emit(int(downloaded * 100 / total))

            self.status.emit("Распаковка архива...")
            res = subprocess.run(
                ["tar", "-xf", str(archive_path), "-C", str(RUNNERS_DIR)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                raise RuntimeError(f"Ошибка tar: {res.stderr}")

            self.status.emit("Готово!")
            self.finished.emit(self.asset_name)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)