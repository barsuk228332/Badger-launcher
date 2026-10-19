import shutil
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QProgressBar,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QGroupBox,
)
from config import ConfigManager, RUNNERS_DIR
from proton_manager import (
    PROTON_SOURCES,
    FetchReleasesWorker,
    DownloadProtonWorker,
)


class ProtonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Менеджер Proton — Badger Launcher")
        self.resize(620, 480)
        self.releases_data = []

        self.fetch_worker = None
        self.dl_worker = None

        layout = QVBoxLayout(self)

        dl_group = QGroupBox("Загрузка новых версий (макс. 15 последних релизов)")
        dl_layout = QVBoxLayout(dl_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Ветка Proton:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(list(PROTON_SOURCES.keys()))
        self.source_combo.currentTextChanged.connect(self.fetch_releases)
        row1.addWidget(self.source_combo, 1)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(
            lambda: self.fetch_releases(self.source_combo.currentText())
        )
        row1.addWidget(self.refresh_btn)
        dl_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Версия:"))
        self.version_combo = QComboBox()
        row2.addWidget(self.version_combo, 1)

        self.download_btn = QPushButton("Скачать и установить")
        self.download_btn.clicked.connect(self.start_download)
        row2.addWidget(self.download_btn)
        dl_layout.addLayout(row2)

        self.status_label = QLabel("Готов к работе")
        dl_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        dl_layout.addWidget(self.progress_bar)

        layout.addWidget(dl_group)

        inst_group = QGroupBox("Установленные сборки Proton / Wine")
        inst_layout = QVBoxLayout(inst_group)

        self.installed_list = QListWidget()
        inst_layout.addWidget(self.installed_list)

        btn_row = QHBoxLayout()
        self.delete_btn = QPushButton("Удалить выбранную сборку")
        self.delete_btn.clicked.connect(self.delete_selected_runner)
        btn_row.addStretch()
        btn_row.addWidget(self.delete_btn)
        inst_layout.addLayout(btn_row)

        layout.addWidget(inst_group)

        self.refresh_installed_list()
        self.fetch_releases(self.source_combo.currentText())

    def refresh_installed_list(self):
        self.installed_list.clear()
        for r in ConfigManager.get_installed_runners():
            item = QListWidgetItem(r["name"])
            item.setData(Qt.UserRole, r["path"])
            self.installed_list.addItem(item)

    def fetch_releases(self, source_name: str):
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait(500)

        self.version_combo.clear()
        self.download_btn.setEnabled(False)
        self.status_label.setText(f"Получение списка релизов {source_name}...")

        self.fetch_worker = FetchReleasesWorker(source_name)
        self.fetch_worker.setParent(self)
        self.fetch_worker.finished.connect(self.on_releases_fetched)
        self.fetch_worker.error.connect(self.on_fetch_error)
        self.fetch_worker.start()

    def on_releases_fetched(self, releases: list):
        self.releases_data = releases
        self.version_combo.clear()
        for rel in releases:
            size_str = f" ({rel['size_mb']} МБ)" if rel["size_mb"] else ""
            self.version_combo.addItem(
                f"{rel['tag']} — {rel['asset_name']}{size_str}"
            )

        self.download_btn.setEnabled(len(releases) > 0)
        self.status_label.setText(f"Найдено релизов: {len(releases)}")

    def on_fetch_error(self, err_msg: str):
        self.status_label.setText("Ошибка загрузки списка")
        QMessageBox.warning(self, "Ошибка API", err_msg)

    def start_download(self):
        idx = self.version_combo.currentIndex()
        if idx < 0 or idx >= len(self.releases_data):
            return

        if self.dl_worker and self.dl_worker.isRunning():
            QMessageBox.warning(self, "Внимание", "Загрузка уже выполняется!")
            return

        rel = self.releases_data[idx]
        self.download_btn.setEnabled(False)
        self.source_combo.setEnabled(False)
        self.progress_bar.setValue(0)

        self.dl_worker = DownloadProtonWorker(rel["url"], rel["asset_name"])
        self.dl_worker.setParent(self)
        self.dl_worker.progress.connect(self.progress_bar.setValue)
        self.dl_worker.status.connect(self.status_label.setText)
        self.dl_worker.finished.connect(self.on_download_finished)
        self.dl_worker.error.connect(self.on_download_error)
        self.dl_worker.start()

    def on_download_finished(self, asset_name: str):
        self.download_btn.setEnabled(True)
        self.source_combo.setEnabled(True)
        self.progress_bar.setValue(100)
        self.refresh_installed_list()
        QMessageBox.information(
            self,
            "Успех",
            f"{asset_name} успешно установлен в:\n{RUNNERS_DIR}",
        )

    def on_download_error(self, err_msg: str):
        self.download_btn.setEnabled(True)
        self.source_combo.setEnabled(True)
        self.status_label.setText("Ошибка при установке")
        QMessageBox.critical(self, "Ошибка", err_msg)

    def delete_selected_runner(self):
        item = self.installed_list.currentItem()
        if not item:
            return
        path_str = item.data(Qt.UserRole)
        if path_str == "System Wine":
            QMessageBox.warning(self, "Отказ", "Системный Wine удалить нельзя.")
            return

        path = Path(path_str)
        if not str(path).startswith(str(RUNNERS_DIR)):
            QMessageBox.warning(
                self,
                "Внимание",
                "Можно удалять только сборки, скачанные внутри этого лаунчера.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить сборку?\n{item.text()}",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            shutil.rmtree(path, ignore_errors=True)
            self.refresh_installed_list()

    def closeEvent(self, event):
        if self.fetch_worker and self.fetch_worker.isRunning():
            self.fetch_worker.terminate()
            self.fetch_worker.wait(500)
        if self.dl_worker and self.dl_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Загрузка не завершена",
                "Сейчас идёт скачивание Proton. Прервать и выйти?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.dl_worker.terminate()
            self.dl_worker.wait(1000)
        event.accept()