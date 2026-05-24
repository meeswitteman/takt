from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QMessageBox, QFileDialog
from PyQt6.QtGui import QAction

from app.projects_tab import ProjectsTab
from app.todos_tab import TodosTab
from app.filter_tab import FilterTab
from app import client, config as cfg
from app import theme as theme_module


class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self._app = app
        self.setWindowTitle("Takt")
        self.setMinimumSize(960, 640)
        self.resize(1100, 720)

        self._settings = cfg.load()
        client.BASE_URL = self._settings.get("api_url", "http://127.0.0.1:8080")

        self._projects = ProjectsTab()
        self._todos = TodosTab()
        self._filter_tab = FilterTab(
            initial_ctx_ids=self._settings.get("filter_context_ids", []),
            initial_root_ids=self._settings.get("filter_root_ids", []),
        )

        self._stack = QStackedWidget()
        self._stack.addWidget(self._projects)   # 0
        self._stack.addWidget(self._todos)      # 1
        self._stack.addWidget(self._filter_tab) # 2
        self.setCentralWidget(self._stack)

        self._filter_tab.filter_changed.connect(self._apply_global_filter)

        self._build_menu()
        self._projects._delegate.spacing = self._settings.get("item_spacing", 12)
        self._update_title()

        # Opgeslagen filter toepassen (signal werd al gefired vóór de verbinding)
        ctx   = self._filter_tab.context_ids
        roots = self._filter_tab.root_ids
        if ctx or roots:
            self._projects.apply_filter(roots)
            self._todos.apply_filter(ctx, roots)

    def _build_menu(self):
        mb = self.menuBar()

        # Bestand
        bestand = mb.addMenu("Bestand")
        act_db = QAction("Database kiezen...", self)
        act_db.triggered.connect(self._choose_database)
        bestand.addAction(act_db)

        # Navigatie — top-level items
        self._act_project = QAction("Project", self)
        self._act_project.setCheckable(True)
        self._act_project.setChecked(True)
        self._act_project.triggered.connect(lambda: self._show_view(0))
        mb.addAction(self._act_project)

        self._act_todo = QAction("Todo", self)
        self._act_todo.setCheckable(True)
        self._act_todo.triggered.connect(lambda: self._show_view(1))
        mb.addAction(self._act_todo)

        self._act_filter = QAction("Filter", self)
        self._act_filter.setCheckable(True)
        self._act_filter.triggered.connect(lambda: self._show_view(2))
        mb.addAction(self._act_filter)

        # Beheer
        beheer = mb.addMenu("Beheer")
        act_ctx = QAction("Context...", self)
        act_ctx.triggered.connect(self._open_contexts)
        beheer.addAction(act_ctx)

        act_var = QAction("Variatielijst...", self)
        act_var.triggered.connect(self._open_variations)
        beheer.addAction(act_var)

        beheer.addSeparator()
        self._act_theme = QAction("Licht thema", self)
        self._act_theme.triggered.connect(self._toggle_theme)
        beheer.addAction(self._act_theme)

        beheer.addSeparator()
        act_settings = QAction("Instellingen...", self)
        act_settings.triggered.connect(self._open_settings)
        beheer.addAction(act_settings)

        # Help
        help_menu = mb.addMenu("Help")
        act_about = QAction("Over Takt", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------
    # Bestand
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
    # Navigatie
    # ------------------------------------------------------------------

    def _show_view(self, index: int):
        self._stack.setCurrentIndex(index)
        self._act_project.setChecked(index == 0)
        self._act_todo.setChecked(index == 1)
        self._act_filter.setChecked(index == 2)
        if index == 1:
            self._todos.refresh()

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _apply_global_filter(self, context_ids: list, root_ids: list):
        self._projects.apply_filter(root_ids)
        self._todos.apply_filter(context_ids, root_ids)
        self._settings["filter_context_ids"] = context_ids
        self._settings["filter_root_ids"] = root_ids
        cfg.save(self._settings)

    # ------------------------------------------------------------------
    # Beheer
    # ------------------------------------------------------------------

    def _open_contexts(self):
        from app.management import ContextsDialog
        dlg = ContextsDialog(self)
        dlg.exec()
        self._projects._load_roots()
        self._todos.refresh()
        self._filter_tab.reload()

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

    def _open_settings(self):
        from app.management import SettingsDialog
        dlg = SettingsDialog(on_theme_change=self._apply_theme, on_font_change=self._apply_font,
                             on_spacing_change=self._apply_spacing, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self._settings = cfg.load()

    # ------------------------------------------------------------------
    # Thema
    # ------------------------------------------------------------------

    def _toggle_theme(self):
        current = self._settings.get("theme", "dark")
        new = "light" if current == "dark" else "dark"
        self._apply_theme(new)
        self._settings["theme"] = new
        cfg.save(self._settings)

    def _apply_theme(self, theme: str):
        if theme == "dark":
            theme_module.apply_dark(self._app)
            self._act_theme.setText("Licht thema")
        else:
            theme_module.apply_light(self._app)
            self._act_theme.setText("Donker thema")
        self._settings["theme"] = theme

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
