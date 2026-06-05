from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QPushButton, QMenu, QMessageBox, QFileDialog,
    QWidget, QVBoxLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from app.projects_tab import ProjectsTab
from app.todos_tab import TodosTab
from app.filter_bar import FilterBar
from app.history_tab import HistoryTab
from app import client, config as cfg
from app import theme as theme_module


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)

        self._settings = cfg.load()
        client.BASE_URL = self._settings.get("api_url", "http://127.0.0.1:8080")

        self._projects = ProjectsTab()
        self._todos = TodosTab()
        self._history = HistoryTab()

        self._filter_bar = FilterBar(
            initial_ctx_ids=self._settings.get("filter_context_ids", []),
            initial_root_ids=self._settings.get("filter_root_ids", []),
            initial_hide_done=self._settings.get("filter_hide_done", False),
        )

        self._tabs = QTabWidget()
        self._tabs.addTab(self._projects, "Project")
        self._tabs.addTab(self._todos, "Todo")
        self._tabs.addTab(self._history, "Geschiedenis")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        central = QWidget()
        col = QVBoxLayout(central)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self._filter_bar)
        col.addWidget(self._tabs)
        self.setCentralWidget(central)

        self._build_menu_button()
        self._filter_bar.filter_changed.connect(self._apply_global_filter)

        self._projects._delegate.spacing = self._settings.get("item_spacing", 12)
        self._update_title()

        # Opgeslagen filter direct toepassen op alle schermen.
        self._apply_global_filter(
            self._filter_bar.context_ids,
            self._filter_bar.root_ids,
            self._filter_bar.hide_done,
            persist=False,
        )

    # ------------------------------------------------------------------
    # Menu-knop (hamburger, rechtsboven naast de tabs)
    # ------------------------------------------------------------------

    def _build_menu_button(self):
        btn = QPushButton("☰")
        btn.setObjectName("menu-btn")
        menu = QMenu(btn)

        act_db = QAction("Database kiezen...", self)
        act_db.triggered.connect(self._choose_database)
        menu.addAction(act_db)

        menu.addSeparator()
        act_ctx = QAction("Context...", self)
        act_ctx.triggered.connect(self._open_contexts)
        menu.addAction(act_ctx)

        act_var = QAction("Variatielijst...", self)
        act_var.triggered.connect(self._open_variations)
        menu.addAction(act_var)

        menu.addSeparator()
        act_settings = QAction("Instellingen...", self)
        act_settings.triggered.connect(self._open_settings)
        menu.addAction(act_settings)

        menu.addSeparator()
        act_about = QAction("Over Takt", self)
        act_about.triggered.connect(self._about)
        menu.addAction(act_about)

        btn.setMenu(menu)
        self._tabs.setCornerWidget(btn, Qt.Corner.TopRightCorner)

    # ------------------------------------------------------------------
    # Navigatie
    # ------------------------------------------------------------------

    def _on_tab_changed(self, index: int):
        # 'verberg gedaan' heeft geen zin op Geschiedenis (alles is gedaan).
        self._filter_bar.set_hide_done_enabled(index != 2)
        if index == 1:
            self._todos.refresh()
        elif index == 2:
            self._history.refresh()

    # ------------------------------------------------------------------
    # Bestand / database
    # ------------------------------------------------------------------

    def _update_title(self):
        db = self._settings.get("db_path", "")
        suffix = f" - {Path(db).name}" if db else ""
        self.setWindowTitle(f"Takt{suffix}")

    def _choose_database(self):
        start = self._settings.get("db_path") or str(Path.home() / "AppData" / "Roaming" / "takt")
        path, _ = QFileDialog.getSaveFileName(
            self, "Database kiezen of aanmaken", start,
            "SQLite database (*.db)",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not path:
            return
        if not path.endswith(".db"):
            path += ".db"
        self._settings["db_path"] = path
        cfg.save(self._settings)
        self._update_title()
        QMessageBox.information(
            self, "Database gewijzigd",
            f"Database ingesteld op:\n{path}\n\n"
            "Herstart de applicatie om de nieuwe database te activeren.",
        )

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _apply_global_filter(self, context_ids: list, root_ids: list,
                             hide_done: bool, persist: bool = True):
        self._projects.apply_filter(context_ids, root_ids, hide_done)
        self._todos.apply_filter(context_ids, root_ids, hide_done)
        self._history.apply_filter(context_ids, root_ids)
        if persist:
            self._settings["filter_context_ids"] = context_ids
            self._settings["filter_root_ids"] = root_ids
            self._settings["filter_hide_done"] = hide_done
            cfg.save(self._settings)

    # ------------------------------------------------------------------
    # Beheer
    # ------------------------------------------------------------------

    def _open_contexts(self):
        from app.management import ContextsDialog
        ContextsDialog(self).exec()
        self._filter_bar.reload()
        self._projects._load()
        self._todos.refresh()

    def _open_variations(self):
        from app.management import VariationsDialog
        VariationsDialog(self).exec()

    def _apply_font(self, family: str, size: int):
        theme_module.apply_font(self._app, family, size)
        self._projects.tree.scheduleDelayedItemsLayout()
        self._todos.refresh()

    def _apply_spacing(self, spacing: int):
        self._projects._delegate.spacing = spacing
        self._projects.tree.scheduleDelayedItemsLayout()

    def _apply_palette(self, name: str):
        theme_module.apply_palette(self._app, name)
        self._settings["palette"] = name
        theme_module.apply_font(
            self._app,
            self._settings.get("font_family", "Segoe UI"),
            self._settings.get("font_size", 10),
        )
        self._projects.tree.viewport().update()
        self._todos.refresh()
        self._history.refresh()

    def _open_settings(self):
        from app.management import SettingsDialog
        dlg = SettingsDialog(on_palette_change=self._apply_palette, on_font_change=self._apply_font,
                             on_spacing_change=self._apply_spacing, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._settings = cfg.load()

    # ------------------------------------------------------------------
    # Over
    # ------------------------------------------------------------------

    def _about(self):
        QMessageBox.about(
            self, "Takt",
            "<b>Takt</b> — persoonlijke taakmanager<br><br>"
            "Backend: FastAPI + SQLite<br>"
            "Frontend: PyQt6<br><br>"
            f"API: {client.BASE_URL}"
        )
