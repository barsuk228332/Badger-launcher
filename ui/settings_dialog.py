from pathlib import Path
from PySide6.QtCore import Qt
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
    QTextEdit,
)
from config import ConfigManager, PREFIXES_DIR
from ui.proton_dialog import ProtonDialog


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setFixedSize(980, 560)
        self.settings = ConfigManager.load_settings()

        self.setStyleSheet("""
            QDialog { background-color: #21242b; color: #e5e7eb; font-family: 'Segoe UI', 'Noto Sans'; }
            QLabel { color: #9ca3af; font-size: 13px; }
            QLineEdit, QTextEdit { background-color: #2b2f38; border: 1px solid #374151; border-radius: 6px; padding: 6px 10px; color: #f3f4f6; }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #68d391; }
            QComboBox { background-color: #2b2f38; border: 1px solid #374151; border-radius: 6px; padding: 6px 10px; color: #f3f4f6; }
            QPushButton.iconBtn { background-color: #2b2f38; border: 1px solid #374151; border-radius: 6px; color: #e5e7eb; }
            QPushButton.iconBtn:hover { background-color: #374151; }
            QPushButton.toolBtn { background-color: #374151; border-radius: 6px; padding: 7px 12px; color: #f3f4f6; font-weight: bold; }
            QPushButton.toolBtn:hover { background-color: #4b5563; }
            QPushButton.bottomBtn { background-color: #374151; border-radius: 6px; padding: 8px 24px; color: #f3f4f6; font-weight: bold; font-size: 14px; }
            QPushButton.bottomBtn:hover { background-color: #4b5563; }
            QCheckBox { color: #d1d5db; font-size: 13px; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #4b5563; background-color: #2b2f38; }
            QCheckBox::indicator:checked { background-color: #68d391; border: 1px solid #68d391; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        tab_bar = QWidget()
        tab_bar.setStyleSheet(
            "background-color: #2b2f38; border-radius: 8px; padding: 2px;"
        )
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)

        self.btn_tab_main = QPushButton("Основные")
        self.btn_tab_ui = QPushButton("Интерфейс")
        for b in [self.btn_tab_main, self.btn_tab_ui]:
            b.setFixedHeight(34)
            b.setCheckable(True)

        self.btn_tab_main.setChecked(True)
        self._apply_tab_styles()
        self.btn_tab_main.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_ui.clicked.connect(lambda: self._switch_tab(1))

        tab_layout.addWidget(self.btn_tab_main)
        tab_layout.addWidget(self.btn_tab_ui)
        layout.addWidget(tab_bar)

        self.stack = QStackedWidget()
        self._init_main_tab()
        self._init_ui_tab()
        layout.addWidget(self.stack, 1)

        footer_row = QHBoxLayout()
        lang_col = QVBoxLayout()
        lang_col.addWidget(QLabel("Язык"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Russian", "English"])
        self.lang_combo.setFixedWidth(200)
        lang_col.addWidget(self.lang_combo)
        footer_row.addLayout(lang_col)
        footer_row.addStretch()

        backup_col = QVBoxLayout()
        backup_col.addWidget(QLabel("Резервная копия / Восстановление"))
        b_btns = QHBoxLayout()
        btn_backup = QPushButton("Создать резервную копию")
        btn_backup.setProperty("class", "toolBtn")
        btn_restore = QPushButton("Восстановить")
        btn_restore.setProperty("class", "toolBtn")
        b_btns.addWidget(btn_backup)
        b_btns.addWidget(btn_restore)
        backup_col.addLayout(b_btns)
        footer_row.addLayout(backup_col)
        layout.addLayout(footer_row)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setProperty("class", "bottomBtn")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Ок")
        btn_ok.setProperty("class", "bottomBtn")
        btn_ok.clicked.connect(self.save_and_close)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        self._load_values()

    def _apply_tab_styles(self):
        active = "background-color: #4b5563; color: #f3f4f6; font-weight: bold; border-radius: 6px; border: none;"
        inactive = "background-color: transparent; color: #9ca3af; font-weight: normal; border: none;"
        self.btn_tab_main.setStyleSheet(
            active if self.btn_tab_main.isChecked() else inactive
        )
        self.btn_tab_ui.setStyleSheet(
            active if self.btn_tab_ui.isChecked() else inactive
        )

    def _switch_tab(self, idx: int):
        self.btn_tab_main.setChecked(idx == 0)
        self.btn_tab_ui.setChecked(idx == 1)
        self._apply_tab_styles()
        self.stack.setCurrentIndex(idx)

    def _init_main_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(20)

        col1 = QVBoxLayout()
        col1.setSpacing(8)
        col1.addWidget(QLabel("Расположение префиксов по умолчанию"))
        pfx_row = QHBoxLayout()
        self.pfx_edit = QLineEdit()
        btn_pfx = QPushButton("🔍")
        btn_pfx.setFixedSize(36, 32)
        btn_pfx.setProperty("class", "iconBtn")
        btn_pfx.clicked.connect(self._browse_default_prefix)
        pfx_row.addWidget(self.pfx_edit)
        pfx_row.addWidget(btn_pfx)
        col1.addLayout(pfx_row)

        col1.addWidget(QLabel("Proton по умолчанию"))
        self.runner_combo = QComboBox()
        for r in ConfigManager.get_installed_runners():
            self.runner_combo.addItem(r["name"], r["path"])
        col1.addWidget(self.runner_combo)

        btn_open_pm = QPushButton("Менеджер Proton")
        btn_open_pm.setProperty("class", "toolBtn")
        btn_open_pm.clicked.connect(self._open_proton_manager)
        col1.addWidget(btn_open_pm)

        col1.addWidget(QLabel("Инструменты префикса по умолчанию"))
        t_row = QHBoxLayout()
        v_check = QVBoxLayout()
        self.cb_mango_def = QCheckBox("MangoHud")
        self.cb_game_def = QCheckBox("GameMode")
        v_check.addWidget(self.cb_mango_def)
        v_check.addWidget(self.cb_game_def)
        t_row.addLayout(v_check)

        v_btns = QVBoxLayout()
        b_wtr = QPushButton("Winetricks")
        b_wtr.setProperty("class", "toolBtn")
        b_wcfg = QPushButton("Winecfg")
        b_wcfg.setProperty("class", "toolBtn")
        v_btns.addWidget(b_wtr)
        v_btns.addWidget(b_wcfg)
        t_row.addLayout(v_btns)
        col1.addLayout(t_row)
        col1.addStretch()
        layout.addLayout(col1, 1)

        col2 = QVBoxLayout()
        col2.setSpacing(8)
        col2.addWidget(QLabel("Разное"))
        self.cb_discrete_gpu = QCheckBox("Использовать дискретную GPU")
        self.cb_close_on_run = QCheckBox("Закрывать после запуска игры")
        self.cb_wayland_driver = QCheckBox("Драйвер Wayland (экспериментально)")
        self.cb_autoupdate = QCheckBox("Автообновление")
        col2.addWidget(self.cb_discrete_gpu)
        col2.addWidget(self.cb_close_on_run)
        col2.addWidget(self.cb_wayland_driver)
        col2.addWidget(self.cb_autoupdate)
        col2.addStretch()
        layout.addLayout(col2, 1)

        col3 = QVBoxLayout()
        col3.setSpacing(8)
        col3.addWidget(QLabel("Глобальные переменные окружения"))
        self.env_edit = QTextEdit()
        self.env_edit.setPlaceholderText("KEY=VALUE\nPROTON_ENABLE_NVAPI=1")
        col3.addWidget(self.env_edit)

        btn_clear_log = QPushButton("Очистить журнал")
        btn_clear_log.setProperty("class", "toolBtn")
        btn_clear_log.clicked.connect(self.env_edit.clear)
        col3.addWidget(btn_clear_log)
        layout.addLayout(col3, 1)

        self.stack.addWidget(page)

    def _init_ui_tab(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(20)

        col1 = QVBoxLayout()
        col1.setSpacing(8)
        col1.addWidget(QLabel("Режим интерфейса"))
        self.ui_mode_combo = QComboBox()
        self.ui_mode_combo.addItems(["Карусель", "Сетка"])
        col1.addWidget(self.ui_mode_combo)

        col1.addWidget(QLabel("Размер окна при запуске"))
        self.win_size_combo = QComboBox()
        self.win_size_combo.addItems(["Стандартный размер", "Во весь экран"])
        col1.addWidget(self.win_size_combo)

        col1.addWidget(QLabel("SteamGridDB API-ключ"))
        self.sgdb_key_edit = QLineEdit()
        col1.addWidget(self.sgdb_key_edit)
        col1.addStretch()
        layout.addLayout(col1, 1)

        col2 = QVBoxLayout()
        col2.setSpacing(8)
        col2.addWidget(QLabel("Тема"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(
            ["Adwaita Dark (По умолчанию)", "Gruvbox Dark", "OLED Black"]
        )
        col2.addWidget(self.theme_combo)

        col2.addWidget(QLabel("Цветовая схема"))
        self.accent_combo = QComboBox()
        self.accent_combo.addItems(
            ["Изумрудный (По умолчанию)", "Синий", "Оранжевый"]
        )
        col2.addWidget(self.accent_combo)
        col2.addStretch()
        layout.addLayout(col2, 1)

        col3 = QVBoxLayout()
        col3.setSpacing(8)
        col3.addWidget(QLabel("Показать"))
        self.cb_show_names = QCheckBox("Названия")
        self.cb_show_banners = QCheckBox("Баннеры")
        self.cb_show_banners.setChecked(True)
        self.cb_show_details = QCheckBox("Краткие сведения")
        col3.addWidget(self.cb_show_names)
        col3.addWidget(self.cb_show_banners)
        col3.addWidget(self.cb_show_details)
        col3.addStretch()
        layout.addLayout(col3, 1)

        self.stack.addWidget(page)

    def _browse_default_prefix(self):
        f = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку",
            self.pfx_edit.text() or str(PREFIXES_DIR),
        )
        if f:
            self.pfx_edit.setText(f)

    def _open_proton_manager(self):
        dlg = ProtonDialog(self)
        dlg.exec()
        self.runner_combo.clear()
        for r in ConfigManager.get_installed_runners():
            self.runner_combo.addItem(r["name"], r["path"])

    def _load_values(self):
        self.pfx_edit.setText(
            self.settings.get("default_prefix_dir", str(PREFIXES_DIR))
        )
        runner_path = self.settings.get("default_runner", "System Wine")
        idx = self.runner_combo.findData(runner_path)
        if idx >= 0:
            self.runner_combo.setCurrentIndex(idx)

        self.cb_discrete_gpu.setChecked(
            self.settings.get("use_discrete_gpu", True)
        )
        self.cb_close_on_run.setChecked(
            self.settings.get("close_on_launch", False)
        )
        self.cb_wayland_driver.setChecked(
            self.settings.get("wayland_driver", False)
        )
        self.env_edit.setPlainText(self.settings.get("global_env", ""))
        self.sgdb_key_edit.setText(
            self.settings.get("steamgriddb_key", ConfigManager.get_api_key())
        )

    def save_and_close(self):
        self.settings["default_prefix_dir"] = self.pfx_edit.text().strip()
        self.settings["default_runner"] = (
            self.runner_combo.currentData() or "System Wine"
        )
        self.settings["use_discrete_gpu"] = self.cb_discrete_gpu.isChecked()
        self.settings["close_on_launch"] = self.cb_close_on_run.isChecked()
        self.settings["wayland_driver"] = self.cb_wayland_driver.isChecked()
        self.settings["global_env"] = self.env_edit.toPlainText().strip()

        key = self.sgdb_key_edit.text().strip()
        self.settings["steamgriddb_key"] = key
        ConfigManager.set_api_key(key)

        ConfigManager.save_settings(self.settings)
        self.accept()