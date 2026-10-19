import subprocess
from pathlib import Path
from PySide6.QtCore import (
    Qt,
    QRectF,
    QPropertyAnimation,
    Property,
    QEasingCurve,
    QProcess,
    QProcessEnvironment,
)
from PySide6.QtGui import (
    QPainter,
    QPixmap,
    QColor,
    QFont,
    QKeyEvent,
    QWheelEvent,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLineEdit,
    QMessageBox,
    QInputDialog,
    QGraphicsBlurEffect,
    QMenu,
    QLabel,
    QFileDialog,
)
from config import ConfigManager
from runner import GameRunner
from steamgrid import CoverDownloadWorker
from ui.game_dialog import GameDialog
from ui.proton_dialog import ProtonDialog
from ui.settings_dialog import SettingsDialog


class CarouselWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.games = []
        self._current_index = 0
        self._offset = 0.0
        self._cached_pixmaps = {}

        self.anim = QPropertyAnimation(self, b"offset", self)
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

    def get_offset(self):
        return self._offset

    def set_offset(self, val):
        self._offset = val
        self.update()

    offset = Property(float, get_offset, set_offset)

    def set_games(self, games: list):
        self.games = games
        self._cached_pixmaps.clear()
        if self._current_index >= len(games):
            self._current_index = max(0, len(games) - 1)
        self._offset = float(self._current_index)
        self.update()

    def get_current_index(self) -> int:
        return self._current_index

    def scroll_to(self, index: int):
        if not self.games:
            return
        index = max(0, min(len(self.games) - 1, index))
        if index != self._current_index or self._offset != float(index):
            self._current_index = index
            self.anim.stop()
            self.anim.setStartValue(self._offset)
            self.anim.setEndValue(float(index))
            self.anim.start()
            self.window().on_game_focused(index)

    def next_game(self):
        self.scroll_to(self._current_index + 1)

    def prev_game(self):
        self.scroll_to(self._current_index - 1)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y() or event.angleDelta().x()
        if delta < 0:
            self.next_game()
        elif delta > 0:
            self.prev_game()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Left, Qt.Key_A):
            self.prev_game()
        elif event.key() in (Qt.Key_Right, Qt.Key_D):
            self.next_game()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.window().launch_or_stop_game()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        cx = self.width() / 2.0
        card_w = 260
        click_x = event.position().x()

        if event.button() == Qt.RightButton:
            if abs(click_x - cx) <= card_w / 2:
                self.window().show_game_context_menu(
                    event.globalPosition().toPoint()
                )
            return

        if click_x < cx - card_w / 2:
            self.prev_game()
        elif click_x > cx + card_w / 2:
            self.next_game()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            cx = self.width() / 2.0
            if abs(event.position().x() - cx) <= 130:
                self.window().launch_or_stop_game()

    def _get_pixmap(self, game: dict) -> QPixmap:
        cover_path = game.get("cover")
        if cover_path in self._cached_pixmaps:
            return self._cached_pixmaps[cover_path]

        if cover_path and Path(cover_path).exists():
            pix = QPixmap(cover_path)
            if not pix.isNull():
                self._cached_pixmaps[cover_path] = pix
                return pix

        pix = QPixmap(300, 450)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#2d3139"))
        p.setPen(QColor("#454b56"))
        p.drawRoundedRect(0, 0, 299, 449, 14, 14)
        p.setPen(QColor("#f3f4f6"))
        p.setFont(QFont("Segoe UI", 16, QFont.Bold))
        p.drawText(
            pix.rect().adjusted(16, 16, -16, -16),
            Qt.AlignCenter | Qt.TextWordWrap,
            game.get("name", "Game"),
        )
        p.end()
        self._cached_pixmaps[cover_path] = pix
        return pix

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if not self.games:
            painter.setPen(QColor("#9ca3af"))
            painter.setFont(QFont("Segoe UI", 16))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Библиотека пуста\nНажмите «+» внизу для добавления игры",
            )
            return

        cx = self.width() / 2.0
        cy = self.height() / 2.0 - 10.0
        base_w = 260.0
        base_h = 390.0
        spacing = 310.0

        indices = list(range(len(self.games)))
        indices.sort(key=lambda i: -abs(i - self._offset))

        for i in indices:
            diff = i - self._offset
            if abs(diff) > 3.2:
                continue

            scale = max(0.68, 1.0 - abs(diff) * 0.18)
            alpha = max(0.25, 1.0 - abs(diff) * 0.35)

            card_w = base_w * scale
            card_h = base_h * scale
            x = cx + diff * spacing - card_w / 2.0
            y = cy - card_h / 2.0
            rect = QRectF(x, y, card_w, card_h)

            if abs(diff) < 0.6:
                glow_opacity = 1.0 - abs(diff) / 0.6
                glow_color = QColor(104, 211, 145, int(150 * glow_opacity))
                for g_expand, g_alpha in [(6, 80), (12, 45), (18, 20)]:
                    glow_rect = rect.adjusted(
                        -g_expand, -g_expand, g_expand, g_expand
                    )
                    g_col = QColor(
                        glow_color.red(),
                        glow_color.green(),
                        glow_color.blue(),
                        int(g_alpha * glow_opacity),
                    )
                    painter.setPen(QPen(g_col, 2.0))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawRoundedRect(glow_rect, 14, 14)

            path = QPainterPath()
            path.addRoundedRect(rect, 12, 12)

            painter.save()
            painter.setOpacity(alpha)
            painter.setClipPath(path)
            pix = self._get_pixmap(self.games[i])
            painter.drawPixmap(rect.toRect(), pix)

            if abs(diff) > 0.05:
                shade_val = min(140, int(abs(diff) * 90))
                painter.fillPath(path, QColor(15, 18, 23, shade_val))

            painter.restore()

            painter.save()
            painter.setOpacity(alpha)
            border_col = (
                QColor(120, 230, 160, 200)
                if abs(diff) < 0.5
                else QColor(255, 255, 255, 30)
            )
            painter.setPen(QPen(border_col, 1.5 if abs(diff) < 0.5 else 1.0))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 12, 12)
            painter.restore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Badger Launcher")
        self.resize(1120, 720)
        self.setMinimumSize(850, 560)
        self.setStyleSheet("QMainWindow { background-color: #1a1c23; }")

        self.all_games = ConfigManager.load_games()
        self.filtered_games = list(self.all_games)
        self.process = None

        self.init_ui()

        if self.filtered_games:
            self.carousel.set_games(self.filtered_games)
            self.on_game_focused(0)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Полноэкранная подложка
        self.bg_label = QLabel(central)
        self.bg_label.setScaledContents(True)
        blur = QGraphicsBlurEffect(self)
        blur.setBlurRadius(46)
        self.bg_label.setGraphicsEffect(blur)

        self.bg_overlay = QWidget(central)
        self.bg_overlay.setStyleSheet(
            "background-color: rgba(22, 24, 30, 0.85);"
        )

        # 2. Слой содержимого поверх фона
        content_layer = QWidget(central)
        content_layout = QVBoxLayout(content_layer)
        content_layout.setContentsMargins(0, 0, 0, 20)
        content_layout.setSpacing(0)

        self.carousel = CarouselWidget(content_layer)
        content_layout.addWidget(self.carousel, 1)

        # 3. Нижний плавающий док
        dock_container = QWidget(content_layer)
        dock_layout = QHBoxLayout(dock_container)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setAlignment(Qt.AlignCenter)

        self.dock_bar = QWidget()
        self.dock_bar.setStyleSheet("""
            QWidget#dockBar {
                background-color: rgba(30, 34, 43, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 8px;
                color: #e5e7eb;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
            }
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 6px 12px;
                color: #f3f4f6;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #68d391;
            }
        """)
        self.dock_bar.setObjectName("dockBar")

        bar_layout = QHBoxLayout(self.dock_bar)
        bar_layout.setContentsMargins(10, 8, 10, 8)
        bar_layout.setSpacing(10)

        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(40, 40)
        self.btn_add.clicked.connect(self.add_game)

        self.btn_global_settings = QPushButton("⚙")
        self.btn_global_settings.setToolTip("Настройки")
        self.btn_global_settings.setFixedSize(40, 40)
        self.btn_global_settings.clicked.connect(self.open_global_settings)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск...")
        self.search_edit.setFixedWidth(200)
        self.search_edit.setFixedHeight(40)
        self.search_edit.textChanged.connect(self.filter_games)

        self.btn_proton = QPushButton("☕")
        self.btn_proton.setToolTip("Менеджер Proton")
        self.btn_proton.setFixedSize(40, 40)
        self.btn_proton.clicked.connect(self.open_proton_manager)

        self.btn_cover = QPushButton("🖼")
        self.btn_cover.setToolTip("Загрузить обложку SteamGridDB")
        self.btn_cover.setFixedSize(40, 40)
        self.btn_cover.clicked.connect(self.download_steamgriddb_cover)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(40, 40)
        self.btn_play.setStyleSheet(
            "background-color: #68d391; color: #1a1c23; border-radius: 8px;"
        )
        self.btn_play.clicked.connect(self.launch_or_stop_game)

        bar_layout.addWidget(self.btn_add)
        bar_layout.addWidget(self.btn_global_settings)
        bar_layout.addWidget(self.search_edit)
        bar_layout.addWidget(self.btn_proton)
        bar_layout.addWidget(self.btn_cover)
        bar_layout.addWidget(self.btn_play)

        dock_layout.addWidget(self.dock_bar)
        content_layout.addWidget(dock_container)

        self.content_layer = content_layer

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Гарантируем покрытие фона и оверлея на весь размер центрального окна
        r = self.centralWidget().rect()
        self.bg_label.setGeometry(r)
        self.bg_overlay.setGeometry(r)
        self.content_layer.setGeometry(r)

    def on_game_focused(self, idx: int):
        if 0 <= idx < len(self.filtered_games):
            g = self.filtered_games[idx]
            cover = g.get("cover")
            if cover and Path(cover).exists():
                pix = QPixmap(cover)
                self.bg_label.setPixmap(pix)
            else:
                self.bg_label.setPixmap(QPixmap())

    def show_game_context_menu(self, global_pos):
        idx = self.carousel.get_current_index()
        if idx < 0 or idx >= len(self.filtered_games):
            return

        game = self.filtered_games[idx]
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2b2f38;
                color: #e5e7eb;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 6px;
                font-family: 'Segoe UI', 'Noto Sans';
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #374151;
                color: #68d391;
            }
            QMenu::separator {
                height: 1px;
                background-color: #374151;
                margin: 4px 0px;
            }
        """)

        title_act = menu.addAction(f"🎮 {game.get('name')}")
        title_act.setEnabled(False)
        menu.addSeparator()

        act_play = menu.addAction("Играть")
        act_play.triggered.connect(self.launch_or_stop_game)

        act_edit = menu.addAction("Редактировать")
        act_edit.triggered.connect(self.edit_game)

        act_delete = menu.addAction("Удалить")
        act_delete.triggered.connect(self.delete_game)

        menu.addSeparator()

        act_open_game = menu.addAction("Открыть папку игры")
        act_open_game.triggered.connect(
            lambda: self.open_folder(Path(game.get("exe", "")).parent)
        )

        act_open_pfx = menu.addAction("Открыть папку префикса")
        act_open_pfx.triggered.connect(
            lambda: self.open_folder(Path(game.get("prefix", "")))
        )

        act_run_in_pfx = menu.addAction("Запустить файл внутри префикса")
        act_run_in_pfx.triggered.connect(lambda: self.run_file_in_prefix(game))

        menu.exec(global_pos)

    def open_folder(self, folder_path: Path):
        if folder_path and folder_path.exists():
            subprocess.Popen(["xdg-open", str(folder_path)])
        else:
            QMessageBox.warning(
                self, "Ошибка", f"Папка не найдена:\n{folder_path}"
            )

    def run_file_in_prefix(self, game: dict):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            str(Path.home()),
            "Executables (*.exe *.bat *.msi)",
        )
        if f:
            dummy = dict(game)
            dummy["exe"] = f
            cmd, env, work_dir = GameRunner.build_command_and_env(dummy)
            subprocess.Popen(cmd, env=env, cwd=work_dir)

    def filter_games(self, query: str):
        query = query.strip().lower()
        if not query:
            self.filtered_games = list(self.all_games)
        else:
            self.filtered_games = [
                g
                for g in self.all_games
                if query in g.get("name", "").lower()
            ]
        self.carousel.set_games(self.filtered_games)
        if self.filtered_games:
            self.on_game_focused(0)

    def add_game(self):
        dlg = GameDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            self.all_games.append(data)
            ConfigManager.save_games(self.all_games)
            self.filter_games(self.search_edit.text())
            self.carousel.scroll_to(len(self.filtered_games) - 1)

    def edit_game(self):
        idx = self.carousel.get_current_index()
        if idx < 0 or idx >= len(self.filtered_games):
            return
        orig_game = self.filtered_games[idx]
        dlg = GameDialog(self, orig_game)
        if dlg.exec():
            new_data = dlg.get_data()
            real_idx = self.all_games.index(orig_game)
            self.all_games[real_idx] = new_data
            ConfigManager.save_games(self.all_games)
            self.filter_games(self.search_edit.text())

    def delete_game(self):
        idx = self.carousel.get_current_index()
        if idx < 0 or idx >= len(self.filtered_games):
            return
        game = self.filtered_games[idx]
        reply = QMessageBox.question(
            self,
            "Удаление",
            f"Удалить «{game.get('name')}» из библиотеки?\n(Префикс и файлы"
            " игры не удалятся)",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.all_games.remove(game)
            ConfigManager.save_games(self.all_games)
            self.filter_games(self.search_edit.text())

    def open_proton_manager(self):
        dlg = ProtonDialog(self)
        dlg.exec()

    def open_global_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def download_steamgriddb_cover(self):
        idx = self.carousel.get_current_index()
        if idx < 0 or idx >= len(self.filtered_games):
            return
        game = self.filtered_games[idx]
        api_key = ConfigManager.get_api_key()

        if not api_key:
            key, ok = QInputDialog.getText(
                self, "SteamGridDB", "Введите ваш API-ключ SteamGridDB:"
            )
            if not ok or not key.strip():
                return
            ConfigManager.set_api_key(key.strip())
            api_key = key.strip()

        self.dl_worker = CoverDownloadWorker(game["name"], api_key)
        self.dl_worker.finished.connect(self._on_cover_done)
        self.dl_worker.error.connect(
            lambda err: QMessageBox.warning(self, "Ошибка", err)
        )
        self.dl_worker.start()

    def _on_cover_done(self, name: str, path: str):
        for g in self.all_games:
            if g.get("name") == name:
                g["cover"] = path
                break
        ConfigManager.save_games(self.all_games)
        self.carousel.set_games(self.filtered_games)
        self.on_game_focused(self.carousel.get_current_index())

    def launch_or_stop_game(self):
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            self.process.waitForFinished(2000)
            if self.process.state() != QProcess.NotRunning:
                self.process.kill()
            self.btn_play.setText("▶")
            self.btn_play.setStyleSheet(
                "background-color: #68d391; color: #1a1c23; border-radius: 8px;"
            )
            return

        idx = self.carousel.get_current_index()
        if idx < 0 or idx >= len(self.filtered_games):
            return
        game = self.filtered_games[idx]
        cmd, env_dict, work_dir = GameRunner.build_command_and_env(game)

        self.process = QProcess(self)
        self.process.setWorkingDirectory(work_dir)
        qenv = QProcessEnvironment()
        for k, v in env_dict.items():
            qenv.insert(k, v)
        self.process.setProcessEnvironment(qenv)
        self.process.finished.connect(
            lambda: (
                self.btn_play.setText("▶"),
                self.btn_play.setStyleSheet(
                    "background-color: #68d391; color: #1a1c23; border-radius:"
                    " 8px;"
                ),
            )
        )

        self.btn_play.setText("⏹")
        self.btn_play.setStyleSheet(
            "background-color: #e53e3e; color: #ffffff; border-radius: 8px;"
        )
        self.process.start(cmd[0], cmd[1:])