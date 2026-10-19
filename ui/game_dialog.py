import subprocess
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QWidget,
    QFileDialog,
    QStackedWidget,
    QMessageBox,
)
from config import ConfigManager, PREFIXES_DIR
from runner import GameRunner


class GameDialog(QDialog):
    def __init__(self, parent=None, game_data: dict = None):
        super().__init__(parent)
        self.game_data = game_data or {}
        name = self.game_data.get("name", "Новая игра")
        self.setWindowTitle(f"Редактировать {name}")
        self.setFixedSize(620, 680)
        self.setStyleSheet("""
            QDialog { background-color: #1f2229; color: #e5e7eb; font-family: 'Segoe UI', 'Noto Sans'; }
            QLabel { color: #9ca3af; font-size: 13px; }
            QLineEdit { background-color: #2b2f38; border: 1px solid #374151; border-radius: 6px; padding: 6px 10px; color: #f3f4f6; }
            QLineEdit:focus { border: 1px solid #68d391; }
            QComboBox { background-color: #2b2f38; border: 1px solid #374151; border-radius: 6px; padding: 6px 10px; color: #f3f4f6; }
            QPushButton.iconBtn { background-color: #2b2f38; border: 1px solid #374151; border-radius: 6px; color: #e5e7eb; }
            QPushButton.iconBtn:hover { background-color: #374151; }
            QPushButton.toolBtn { background-color: #374151; border-radius: 6px; padding: 8px 12px; color: #f3f4f6; font-weight: bold; }
            QPushButton.toolBtn:hover { background-color: #4b5563; }
            QPushButton.bottomBtn { background-color: #374151; border-radius: 6px; padding: 10px 24px; color: #f3f4f6; font-weight: bold; font-size: 14px; }
            QPushButton.bottomBtn:hover { background-color: #4b5563; }
            QCheckBox { color: #d1d5db; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #4b5563; background-color: #2b2f38; }
            QCheckBox::indicator:checked { background-color: #68d391; border: 1px solid #68d391; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        self.banner_label = QLabel()
        self.banner_label.setFixedHeight(140)
        self.banner_label.setScaledContents(True)
        self.banner_label.setStyleSheet(
            "border-radius: 8px; background-color: #2b2f38;"
        )
        self._update_banner()
        layout.addWidget(self.banner_label)

        tab_bar = QWidget()
        tab_bar.setStyleSheet(
            "background-color: #2b2f38; border-radius: 8px; padding: 2px;"
        )
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)

        self.btn_tab_app = QPushButton("Игра/Приложение")
        self.btn_tab_tools = QPushButton("Инструменты")
        for b in [self.btn_tab_app, self.btn_tab_tools]:
            b.setFixedHeight(32)
            b.setCheckable(True)

        self.btn_tab_app.setChecked(True)
        self._apply_tab_styles()
        self.btn_tab_app.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_tools.clicked.connect(lambda: self._switch_tab(1))

        tab_layout.addWidget(self.btn_tab_app)
        tab_layout.addWidget(self.btn_tab_tools)
        layout.addWidget(tab_bar)

        center_row = QHBoxLayout()
        center_row.setSpacing(14)

        self.stack = QStackedWidget()
        self._init_app_tab()
        self._init_tools_tab()
        center_row.addWidget(self.stack, 1)

        self.cover_label = QLabel()
        self.cover_label.setFixedSize(180, 270)
        self.cover_label.setScaledContents(True)
        self.cover_label.setStyleSheet(
            "border-radius: 8px; border: 1px solid #374151; background-color:"
            " #2b2f38;"
        )
        self.cover_label.mousePressEvent = lambda e: self.change_cover_manual()
        self.cover_label.setToolTip("Нажмите для выбора обложки вручную")
        self._update_cover()
        center_row.addWidget(self.cover_label)

        layout.addLayout(center_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setProperty("class", "bottomBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Ок")
        btn_ok.setProperty("class", "bottomBtn")
        btn_ok.clicked.connect(self.accept)

        bottom_row.addWidget(btn_cancel)
        bottom_row.addWidget(btn_ok)
        layout.addLayout(bottom_row)

        self._load_data()

    def _apply_tab_styles(self):
        active = "background-color: #4b5563; color: #f3f4f6; font-weight: bold; border-radius: 6px; border: none;"
        inactive = "background-color: transparent; color: #9ca3af; font-weight: normal; border: none;"
        self.btn_tab_app.setStyleSheet(
            active if self.btn_tab_app.isChecked() else inactive
        )
        self.btn_tab_tools.setStyleSheet(
            active if self.btn_tab_tools.isChecked() else inactive
        )

    def _switch_tab(self, idx: int):
        self.btn_tab_app.setChecked(idx == 0)
        self.btn_tab_tools.setChecked(idx == 1)
        self._apply_tab_styles()
        self.stack.setCurrentIndex(idx)

    def _init_app_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Название"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        layout.addWidget(QLabel("Путь"))
        path_row = QHBoxLayout()
        self.exe_edit = QLineEdit()
        btn_exe_find = QPushButton("🔍")
        btn_exe_find.setFixedSize(36, 32)
        btn_exe_find.setProperty("class", "iconBtn")
        btn_exe_find.clicked.connect(self.browse_exe)
        path_row.addWidget(self.exe_edit)
        path_row.addWidget(btn_exe_find)
        layout.addLayout(path_row)

        layout.addWidget(QLabel("Префикс"))
        pfx_row = QHBoxLayout()
        self.prefix_edit = QLineEdit()
        btn_pfx_find = QPushButton("🔍")
        btn_pfx_find.setFixedSize(36, 32)
        btn_pfx_find.setProperty("class", "iconBtn")
        btn_pfx_find.clicked.connect(self.browse_prefix)
        pfx_row.addWidget(self.prefix_edit)
        pfx_row.addWidget(btn_pfx_find)
        layout.addLayout(pfx_row)

        self.cb_specific_proton = QCheckBox("Specific Proton")
        self.cb_specific_proton.setChecked(True)
        layout.addWidget(self.cb_specific_proton)

        self.runner_combo = QComboBox()
        for r in ConfigManager.get_installed_runners():
            self.runner_combo.addItem(r["name"], r["path"])
        layout.addWidget(self.runner_combo)

        layout.addWidget(QLabel("Ярлык"))
        lbl_shortcuts = QHBoxLayout()
        self.cb_desktop = QCheckBox("Рабочий стол")
        self.cb_menu = QCheckBox("Меню приложений")
        lbl_shortcuts.addWidget(self.cb_desktop)
        lbl_shortcuts.addWidget(self.cb_menu)
        layout.addLayout(lbl_shortcuts)

        layout.addStretch()
        self.stack.addWidget(page)

    def _init_tools_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Параметры игры"))
        self.args_edit = QLineEdit()
        layout.addWidget(self.args_edit)

        self.cb_lsfg = QCheckBox("Генерация кадров Lossless Scaling (lsfg-vk)")
        layout.addWidget(self.cb_lsfg)

        toggles_grid = QHBoxLayout()
        v_toggles = QVBoxLayout()
        self.cb_mangohud = QCheckBox("MangoHud")
        self.cb_gamemode = QCheckBox("GameMode")
        self.cb_wayland = QCheckBox("Wayland драйвер")
        self.cb_umu = QCheckBox("Запуск через umu-run")
        v_toggles.addWidget(self.cb_mangohud)
        v_toggles.addWidget(self.cb_gamemode)
        v_toggles.addWidget(self.cb_wayland)
        v_toggles.addWidget(self.cb_umu)
        toggles_grid.addLayout(v_toggles)

        v_tools = QVBoxLayout()
        btn_winetricks = QPushButton("Winetricks")
        btn_winetricks.setProperty("class", "toolBtn")
        btn_winetricks.clicked.connect(lambda: self.launch_tool("winetricks"))

        btn_winecfg = QPushButton("Winecfg")
        btn_winecfg.setProperty("class", "toolBtn")
        btn_winecfg.clicked.connect(lambda: self.launch_tool("winecfg"))

        btn_run_file = QPushButton("Запустить exe")
        btn_run_file.setProperty("class", "toolBtn")
        btn_run_file.clicked.connect(self.run_custom_exe_in_prefix)

        v_tools.addWidget(btn_winetricks)
        v_tools.addWidget(btn_winecfg)
        v_tools.addWidget(btn_run_file)
        toggles_grid.addLayout(v_tools)

        layout.addLayout(toggles_grid)
        layout.addStretch()
        self.stack.addWidget(page)

    def _update_banner(self):
        cover = self.game_data.get("cover")
        if cover and Path(cover).exists():
            pix = QPixmap(cover).scaled(
                600, 140, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.banner_label.setPixmap(pix)

    def _update_cover(self):
        cover = self.game_data.get("cover")
        if cover and Path(cover).exists():
            pix = QPixmap(cover).scaled(
                180, 270, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.cover_label.setPixmap(pix)
        else:
            pix = QPixmap(180, 270)
            pix.fill(QColor("#2b2f38"))
            p = QPainter(pix)
            p.setPen(QColor("#9ca3af"))
            p.drawText(
                pix.rect(), Qt.AlignCenter, "Нет постера\n(Кликните для выбора)"
            )
            p.end()
            self.cover_label.setPixmap(pix)

    def change_cover_manual(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите обложку",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp)",
        )
        if f:
            self.game_data["cover"] = f
            self._update_cover()
            self._update_banner()

    def browse_exe(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            str(Path.home()),
            "Executable (*.exe);;All Files (*)",
        )
        if f:
            self.exe_edit.setText(f)
            if not self.name_edit.text():
                self.name_edit.setText(Path(f).stem)
            if not self.prefix_edit.text():
                safe_name = Path(f).stem.lower().replace(" ", "_")
                self.prefix_edit.setText(str(PREFIXES_DIR / f"{safe_name}_0"))

    def browse_prefix(self):
        f = QFileDialog.getExistingDirectory(
            self, "Папка префикса", str(PREFIXES_DIR)
        )
        if f:
            self.prefix_edit.setText(f)

    def launch_tool(self, tool_name: str):
        prefix = self.prefix_edit.text().strip() or str(
            PREFIXES_DIR / "default_0"
        )
        runner = self.runner_combo.currentData() or "System Wine"
        try:
            GameRunner.run_prefix_tool(runner, prefix, tool_name)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def run_custom_exe_in_prefix(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            str(Path.home()),
            "Executables (*.exe *.bat *.msi)",
        )
        if not f:
            return
        dummy = {
            "exe": f,
            "prefix": self.prefix_edit.text().strip(),
            "runner": self.runner_combo.currentData() or "System Wine",
            "toggles": {"use_umu": self.cb_umu.isChecked()},
        }
        cmd, env, work_dir = GameRunner.build_command_and_env(dummy)
        subprocess.Popen(cmd, env=env, cwd=work_dir)

    def _load_data(self):
        if not self.game_data:
            return
        self.name_edit.setText(self.game_data.get("name", ""))
        self.exe_edit.setText(self.game_data.get("exe", ""))
        self.prefix_edit.setText(self.game_data.get("prefix", ""))
        self.args_edit.setText(self.game_data.get("args", ""))

        saved_path = self.game_data.get("runner", "System Wine")
        idx = self.runner_combo.findData(saved_path)
        if idx >= 0:
            self.runner_combo.setCurrentIndex(idx)

        toggles = self.game_data.get("toggles", {})
        self.cb_mangohud.setChecked(toggles.get("mangohud", False))
        self.cb_gamemode.setChecked(toggles.get("gamemode", False))
        self.cb_wayland.setChecked(toggles.get("wayland", False))
        self.cb_umu.setChecked(toggles.get("use_umu", False))
        self.cb_lsfg.setChecked(toggles.get("lsfg", False))

    def get_data(self) -> dict:
        name = self.name_edit.text().strip() or "Без названия"
        prefix = self.prefix_edit.text().strip()
        if not prefix:
            prefix = str(PREFIXES_DIR / f"{name.lower().replace(' ', '_')}_0")

        return {
            "name": name,
            "exe": self.exe_edit.text().strip(),
            "runner": self.runner_combo.currentData() or "System Wine",
            "prefix": prefix,
            "args": self.args_edit.text().strip(),
            "cover": self.game_data.get("cover"),
            "toggles": {
                "mangohud": self.cb_mangohud.isChecked(),
                "gamemode": self.cb_gamemode.isChecked(),
                "wayland": self.cb_wayland.isChecked(),
                "use_umu": self.cb_umu.isChecked(),
                "lsfg": self.cb_lsfg.isChecked(),
            },
            "gamescope": self.game_data.get("gamescope", {"enabled": False}),
            "env_vars": self.game_data.get("env_vars", {}),
        }