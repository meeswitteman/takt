from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
    QListWidgetItem, QComboBox, QDialogButtonBox, QColorDialog,
    QMessageBox, QSplitter, QWidget, QFrame, QFontComboBox, QSpinBox,
    QScrollArea,
)
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtCore import Qt

from app import client, config as cfg
from app.dialogs import show_error


# ---------------------------------------------------------------------------
# Hulpfunctie: kleur-knop
# ---------------------------------------------------------------------------

def _color_button(color: str) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(32, 24)
    _set_btn_color(btn, color)
    return btn


def _set_btn_color(btn: QPushButton, color: str) -> None:
    btn.setProperty("color", color)
    btn.setStyleSheet(f"background: {color}; border: 1px solid #666; border-radius: 3px;")


# ---------------------------------------------------------------------------
# Contexten
# ---------------------------------------------------------------------------

class ContextsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Context beheren")
        self.setMinimumSize(420, 380)
        self._contexts = []
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)

        # Lijst
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.currentItemChanged.connect(self._on_select)
        layout.addWidget(self._list)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Invoervelden (gedeeld voor toevoegen én wijzigen)
        form = QHBoxLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Naam")
        self._color_hex = "#888888"
        self._color_btn = _color_button(self._color_hex)
        self._color_btn.setToolTip("Kies kleur")
        self._color_btn.clicked.connect(self._pick_color)

        form.addWidget(QLabel("Naam:"))
        form.addWidget(self._name_edit, stretch=1)
        form.addWidget(QLabel("Kleur:"))
        form.addWidget(self._color_btn)
        layout.addLayout(form)

        # Knoppen
        btn_row = QHBoxLayout()
        btn_add = QPushButton("Toevoegen")
        btn_add.clicked.connect(self._add)
        self._name_edit.returnPressed.connect(self._add)
        btn_row.addWidget(btn_add)

        self._btn_update = QPushButton("Wijzigen")
        self._btn_update.clicked.connect(self._update)
        self._btn_update.setEnabled(False)
        btn_row.addWidget(self._btn_update)

        btn_del = QPushButton("Verwijderen")
        btn_del.clicked.connect(self._delete)
        btn_row.addWidget(btn_del)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.accept)
        layout.addWidget(btns)

    def _load(self):
        self._list.clear()
        try:
            self._contexts = client.get_contexts()
        except Exception as e:
            show_error(str(e), self)
            return
        for ctx in self._contexts:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, ctx["id"])
            pix = QPixmap(16, 16)
            pix.fill(QColor(ctx["color"]))
            item.setIcon(QIcon(pix))
            item.setText(f"  {ctx['name']}   {ctx['color']}")
            self._list.addItem(item)

    def _on_select(self, current: QListWidgetItem, _prev):
        if current is None:
            self._btn_update.setEnabled(False)
            return
        ctx_id = current.data(Qt.ItemDataRole.UserRole)
        ctx = next((c for c in self._contexts if c["id"] == ctx_id), None)
        if ctx:
            self._name_edit.setText(ctx["name"])
            self._color_hex = ctx["color"]
            _set_btn_color(self._color_btn, self._color_hex)
        self._btn_update.setEnabled(True)

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._color_hex), self, "Kies kleur")
        if color.isValid():
            self._color_hex = color.name()
            _set_btn_color(self._color_btn, self._color_hex)

    def _add(self):
        name = self._name_edit.text().strip()
        if not name:
            return
        try:
            client.create_context(name, self._color_hex)
            self._name_edit.clear()
            self._load()
        except Exception as e:
            show_error(str(e), self)

    def _update(self):
        item = self._list.currentItem()
        if not item:
            return
        name = self._name_edit.text().strip()
        if not name:
            return
        ctx_id = item.data(Qt.ItemDataRole.UserRole)
        try:
            client.update_context(ctx_id, name, self._color_hex)
            self._load()
        except Exception as e:
            show_error(str(e), self)

    def _delete(self):
        item = self._list.currentItem()
        if not item:
            return
        ctx_id = item.data(Qt.ItemDataRole.UserRole)
        name = item.text().strip().split()[0]
        if QMessageBox.question(self, "Verwijderen", f"Context '{name}' verwijderen?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) != QMessageBox.StandardButton.Yes:
            return
        try:
            client.delete_context(ctx_id)
            self._load()
        except Exception as e:
            show_error(str(e), self)


# ---------------------------------------------------------------------------
# Variatielijsten
# ---------------------------------------------------------------------------

class VariationsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Variatielijst beheren")
        self.setMinimumSize(520, 420)
        self._lists = []
        self._build()
        self._load_lists()

    def _build(self):
        layout = QVBoxLayout(self)

        # Keuze lijst + knoppen
        top = QHBoxLayout()
        top.addWidget(QLabel("Lijst:"))
        self._combo = QComboBox()
        self._combo.setMinimumWidth(200)
        self._combo.currentIndexChanged.connect(self._on_select)
        top.addWidget(self._combo, stretch=1)

        btn_new = QPushButton("Nieuw")
        btn_new.clicked.connect(self._new_list)
        top.addWidget(btn_new)

        btn_del = QPushButton("Verwijderen")
        btn_del.clicked.connect(self._delete_list)
        top.addWidget(btn_del)
        layout.addLayout(top)

        # Entries editor
        layout.addWidget(QLabel("Entries (één per regel):"))
        self._editor = QTextEdit()
        self._editor.setPlaceholderText("Elke regel is één variatie-waarde")
        self._editor.setFont(self._editor.font())
        layout.addWidget(self._editor)

        # Opslaan
        btn_save = QPushButton("Opslaan")
        btn_save.clicked.connect(self._save_entries)
        layout.addWidget(btn_save)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.accept)
        layout.addWidget(btns)

    def _load_lists(self):
        try:
            self._lists = client._get("/api/v1/variations")
        except Exception as e:
            show_error(str(e), self)
            return
        self._combo.blockSignals(True)
        self._combo.clear()
        for vl in self._lists:
            self._combo.addItem(vl["name"], vl["id"])
        self._combo.blockSignals(False)
        if self._lists:
            self._combo.setCurrentIndex(0)
            self._on_select(0)

    def _on_select(self, idx: int):
        if idx < 0 or idx >= len(self._lists):
            self._editor.clear()
            return
        entries = self._lists[idx].get("entries", [])
        self._editor.setPlainText("\n".join(e["value"] for e in entries))

    def _new_list(self):
        from app.dialogs import NewItemDialog
        dlg = NewItemDialog(parent_title=None, parent=self)
        dlg.setWindowTitle("Nieuwe variatielijst")
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            client._post("/api/v1/variations", {"name": dlg.title})
            self._load_lists()
            # Selecteer nieuwe lijst
            for i in range(self._combo.count()):
                if self._combo.itemText(i) == dlg.title:
                    self._combo.setCurrentIndex(i)
                    break
        except Exception as e:
            show_error(str(e), self)

    def _delete_list(self):
        idx = self._combo.currentIndex()
        if idx < 0:
            return
        name = self._combo.currentText()
        if QMessageBox.question(self, "Verwijderen", f"Lijst '{name}' verwijderen?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                ) != QMessageBox.StandardButton.Yes:
            return
        list_id = self._combo.currentData()
        try:
            client._delete(f"/api/v1/variations/{list_id}")
            self._load_lists()
        except Exception as e:
            show_error(str(e), self)

    def _save_entries(self):
        idx = self._combo.currentIndex()
        if idx < 0:
            return
        list_id = self._combo.currentData()
        values = [line for line in self._editor.toPlainText().splitlines() if line.strip()]
        try:
            client._put(f"/api/v1/variations/{list_id}/entries", {"values": values})
            self._load_lists()
            QMessageBox.information(self, "Opgeslagen", f"{len(values)} entries opgeslagen.")
        except Exception as e:
            show_error(str(e), self)


# ---------------------------------------------------------------------------
# Instellingen
# ---------------------------------------------------------------------------

class SettingsDialog(QDialog):
    def __init__(self, on_palette_change=None, on_font_change=None, on_spacing_change=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Instellingen")
        self.setMinimumWidth(400)
        self._on_palette_change = on_palette_change
        self._on_font_change = on_font_change
        self._on_spacing_change = on_spacing_change
        self._settings = cfg.load()
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Backend URL
        self._url_edit = QLineEdit(self._settings.get("api_url", "http://127.0.0.1:8080"))
        form.addRow("Backend URL:", self._url_edit)

        # Kleurenpalet
        from app import theme as theme_module
        self._palette_combo = QComboBox()
        for name in theme_module.PALETTE_NAMES:
            self._palette_combo.addItem(name, name)
        cur_palette = theme_module.palette_from_settings(self._settings)
        idx = self._palette_combo.findData(cur_palette)
        self._palette_combo.setCurrentIndex(idx if idx >= 0 else 0)
        form.addRow("Kleurenpalet:", self._palette_combo)

        # Standaard context
        self._ctx_combo = QComboBox()
        self._ctx_combo.addItem("Alle", None)
        try:
            for ctx in client.get_contexts():
                self._ctx_combo.addItem(ctx["name"], ctx["name"])
        except Exception:
            pass
        default_ctx = self._settings.get("default_context")
        for i in range(self._ctx_combo.count()):
            if self._ctx_combo.itemData(i) == default_ctx:
                self._ctx_combo.setCurrentIndex(i)
                break
        form.addRow("Standaard context (todo's):", self._ctx_combo)

        # Lettertype
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(self._font_combo.font())
        current_family = self._settings.get("font_family", "Segoe UI")
        self._font_combo.setCurrentText(current_family)
        form.addRow("Lettertype:", self._font_combo)

        self._font_size = QSpinBox()
        self._font_size.setRange(7, 24)
        self._font_size.setValue(self._settings.get("font_size", 10))
        self._font_size.setSuffix(" pt")
        form.addRow("Lettergrootte:", self._font_size)

        self._spacing = QSpinBox()
        self._spacing.setRange(2, 40)
        self._spacing.setValue(self._settings.get("item_spacing", 12))
        self._spacing.setSuffix(" px")
        form.addRow("Regelafstand (projecten):", self._spacing)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _save(self):
        new_settings = {
            **self._settings,
            "api_url": self._url_edit.text().strip().rstrip("/"),
            "palette": self._palette_combo.currentData(),
            "default_context": self._ctx_combo.currentData(),
            "font_family": self._font_combo.currentFont().family(),
            "font_size": self._font_size.value(),
            "item_spacing": self._spacing.value(),
        }
        cfg.save(new_settings)

        # Pas palet direct toe als het veranderd is
        if new_settings["palette"] != self._settings.get("palette") and self._on_palette_change:
            self._on_palette_change(new_settings["palette"])

        if self._on_font_change:
            self._on_font_change(new_settings["font_family"], new_settings["font_size"])
        if self._on_spacing_change:
            self._on_spacing_change(new_settings["item_spacing"])

        # Update backend URL in client module en reset verbinding
        import app.client as client_mod
        client_mod.BASE_URL = new_settings["api_url"]
        client_mod.reset()

        self.accept()


# ---------------------------------------------------------------------------
# Globaal filter
# ---------------------------------------------------------------------------

_FILTER_CHIP_STYLE = """
    QPushButton {
        border: 1px solid #555; border-radius: 10px;
        padding: 2px 10px; background: transparent; color: #aaa; text-align: left;
    }
    QPushButton:checked {
        background: #0e639c; border-color: #1e88e5; color: white;
    }
    QPushButton:hover:!checked { border-color: #888; color: #ccc; }
"""


class FilterDialog(QDialog):
    def __init__(self, contexts: list, roots: list,
                 active_ctx_ids: list, active_root_ids: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter instellen")
        self.setMinimumSize(480, 320)
        self._contexts = contexts
        self._roots = roots
        self._active_ctx = set(active_ctx_ids)
        self._active_roots = set(active_root_ids)
        self._ctx_chips: list[QPushButton] = []
        self._root_chips: list[QPushButton] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        cols = QHBoxLayout()
        cols.setSpacing(16)

        # Left: contexts
        left = QVBoxLayout()
        left.setSpacing(4)
        left.addWidget(QLabel("<b>Context</b>"))
        for ctx in self._contexts:
            chip = QPushButton(ctx["name"])
            chip.setCheckable(True)
            chip.setChecked(ctx["id"] in self._active_ctx)
            chip.setProperty("filter_id", ctx["id"])
            chip.setFixedHeight(26)
            chip.setStyleSheet(_FILTER_CHIP_STYLE)
            left.addWidget(chip)
            self._ctx_chips.append(chip)
        left.addStretch()

        vsep = QFrame()
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setStyleSheet("color: #444;")

        # Right: roots (scrollable if many)
        right_outer = QVBoxLayout()
        right_outer.setSpacing(4)
        right_outer.addWidget(QLabel("<b>Project</b>"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        root_widget = QWidget()
        right_inner = QVBoxLayout(root_widget)
        right_inner.setSpacing(4)
        right_inner.setContentsMargins(0, 0, 4, 0)
        for root in self._roots:
            title = root["title"]
            if len(title) > 40:
                title = title[:37] + "..."
            chip = QPushButton(title)
            chip.setCheckable(True)
            chip.setChecked(root["id"] in self._active_roots)
            chip.setProperty("filter_id", root["id"])
            chip.setFixedHeight(26)
            chip.setStyleSheet(_FILTER_CHIP_STYLE)
            right_inner.addWidget(chip)
            self._root_chips.append(chip)
        right_inner.addStretch()
        scroll.setWidget(root_widget)
        right_outer.addWidget(scroll, stretch=1)

        cols.addLayout(left)
        cols.addWidget(vsep)
        cols.addLayout(right_outer, stretch=1)
        layout.addLayout(cols, stretch=1)

        # Bottom row
        bottom = QHBoxLayout()
        btn_clear = QPushButton("Alles wissen")
        btn_clear.clicked.connect(self._clear_all)
        bottom.addWidget(btn_clear)
        bottom.addStretch()
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        bottom.addWidget(btns)
        layout.addLayout(bottom)

    def _clear_all(self):
        for chip in self._ctx_chips + self._root_chips:
            chip.setChecked(False)

    def result_filter(self) -> dict:
        return {
            "context_ids": [c.property("filter_id") for c in self._ctx_chips if c.isChecked()],
            "root_ids": [c.property("filter_id") for c in self._root_chips if c.isChecked()],
        }
