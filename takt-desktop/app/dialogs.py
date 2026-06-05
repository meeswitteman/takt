from datetime import datetime, timedelta, timezone
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QDialogButtonBox, QColorDialog,
    QCheckBox, QComboBox, QMessageBox, QFormLayout, QGroupBox,
    QDateTimeEdit,
)
from PyQt6.QtCore import Qt, QDateTime
from PyQt6.QtGui import QColor


class DoneDialog(QDialog):
    def __init__(self, item_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Afvinken")
        self.setMinimumWidth(360)
        self.note = ""

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{item_title}</b>"))
        layout.addWidget(QLabel("Optionele notitie:"))
        self._note_edit = QTextEdit()
        self._note_edit.setMaximumHeight(80)
        self._note_edit.setPlaceholderText("Wat heb je gedaan, opgemerkt, geleerd?")
        layout.addWidget(self._note_edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _accept(self):
        self.note = self._note_edit.toPlainText().strip() or None
        self.accept()


class NewItemDialog(QDialog):
    def __init__(self, parent_title: str | None = None, parent=None):
        super().__init__(parent)
        self.title = ""
        label = f"Kind van: {parent_title}" if parent_title else "Nieuw root item"
        self.setWindowTitle(label)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Titel:"))
        self._edit = QLineEdit()
        self._edit.returnPressed.connect(self._accept)
        layout.addWidget(self._edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self._edit.setFocus()

    def _accept(self):
        t = self._edit.text().strip()
        if not t:
            return
        self.title = t
        self.accept()


class RenameDialog(QDialog):
    def __init__(self, current_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hernoemen")
        self.setMinimumWidth(320)
        self.title = current_title

        layout = QVBoxLayout(self)
        self._edit = QLineEdit(current_title)
        self._edit.selectAll()
        self._edit.returnPressed.connect(self._accept)
        layout.addWidget(self._edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self._edit.setFocus()

    def _accept(self):
        t = self._edit.text().strip()
        if not t:
            return
        self.title = t
        self.accept()


class ContextAssignDialog(QDialog):
    def __init__(self, all_contexts: list, assigned_ids: list[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contexten toewijzen")
        self.selected_ids: list[int] = []

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Selecteer contexten:"))

        self._checks: list[tuple[QCheckBox, int]] = []
        for ctx in all_contexts:
            cb = QCheckBox(ctx["name"])
            cb.setChecked(ctx["id"] in assigned_ids)
            layout.addWidget(cb)
            self._checks.append((cb, ctx["id"]))

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _accept(self):
        self.selected_ids = [cid for cb, cid in self._checks if cb.isChecked()]
        self.accept()


class RecurringDialog(QDialog):
    INTERVALS = [
        ("direct",        "Direct (herstart meteen)"),
        ("daily",         "Dagelijks"),
        ("weekly",        "Wekelijks"),
        ("weekday:0",     "Elke maandag"),
        ("weekday:1",     "Elke dinsdag"),
        ("weekday:2",     "Elke woensdag"),
        ("weekday:3",     "Elke donderdag"),
        ("weekday:4",     "Elke vrijdag"),
        ("weekday:5",     "Elke zaterdag"),
        ("weekday:6",     "Elke zondag"),
        ("monthly_first", "Elke 1e van de maand"),
    ]

    def __init__(self, is_recurring: bool, current_interval: str | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recurring instellen")
        self.is_recurring = is_recurring
        self.interval = current_interval or "direct"

        layout = QVBoxLayout(self)
        self._check = QCheckBox("Recurring (herstart na afvinken)")
        self._check.setChecked(is_recurring)
        self._check.toggled.connect(self._on_toggle)
        layout.addWidget(self._check)

        self._combo = QComboBox()
        for val, label in self.INTERVALS:
            self._combo.addItem(label, val)
        if current_interval:
            idx = next((i for i, (v, _) in enumerate(self.INTERVALS) if v == current_interval), 0)
            self._combo.setCurrentIndex(idx)
        self._combo.setEnabled(is_recurring)
        layout.addWidget(self._combo)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_toggle(self, checked: bool):
        self._combo.setEnabled(checked)

    def _accept(self):
        self.is_recurring = self._check.isChecked()
        self.interval = self._combo.currentData() if self.is_recurring else None
        self.accept()


class VariationAssignDialog(QDialog):
    def __init__(self, variation_lists: list, current_list_id: int | None, current_mode: str | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Variatie instellen")
        self.setMinimumWidth(320)
        self.variation_list_id = current_list_id
        self.mode = current_mode or "linear"

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._list_combo = QComboBox()
        self._list_combo.addItem("Geen", None)
        for vl in variation_lists:
            self._list_combo.addItem(vl["name"], vl["id"])
        if current_list_id is not None:
            idx = next((i for i in range(self._list_combo.count())
                        if self._list_combo.itemData(i) == current_list_id), 0)
            self._list_combo.setCurrentIndex(idx)
        form.addRow("Variatielijst:", self._list_combo)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Lineair (volgorde)", "linear")
        self._mode_combo.addItem("Willekeurig (random)", "random")
        if current_mode == "random":
            self._mode_combo.setCurrentIndex(1)
        form.addRow("Keuzemethode:", self._mode_combo)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _accept(self):
        self.variation_list_id = self._list_combo.currentData()
        self.mode = self._mode_combo.currentData() if self.variation_list_id else None
        self.accept()


class ItemEditDialog(QDialog):
    INTERVALS = RecurringDialog.INTERVALS

    def __init__(self, data: dict, variation_lists: list, all_contexts: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Item bewerken")
        self.setMinimumWidth(400)

        assigned_ctx_ids = {c["id"] for c in data.get("contexts", [])}

        # Uitvoerwaarden
        self.title           = data["title"]
        self.description     = data.get("description") or ""
        self.start_note      = data.get("start_note") or ""
        self.src             = data.get("src") or ""
        self.is_done         = data.get("is_done", False)
        self.is_todo         = data.get("is_todo", False)
        self.is_recurring    = data.get("is_recurring", False)
        self.interval        = data.get("recurring_interval") or "direct"
        self.variation_list_id = data.get("variation_list_id")
        self.variation_mode  = data.get("variation_mode") or "linear"
        self.context_ids: list[int] = list(assigned_ctx_ids)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # Titel
        self._title_edit = QLineEdit(data["title"])
        self._title_edit.setMinimumWidth(280)
        form.addRow("Naam:", self._title_edit)

        # Omschrijving
        self._desc_edit = QTextEdit(data.get("description") or "")
        self._desc_edit.setPlaceholderText("Optionele omschrijving")
        self._desc_edit.setMaximumHeight(72)
        form.addRow("Omschrijving:", self._desc_edit)

        # Starttip
        self._start_note_edit = QLineEdit(data.get("start_note") or "")
        self._start_note_edit.setPlaceholderText("Korte instructie bij aanvang")
        form.addRow("Starttip:", self._start_note_edit)

        # Bron
        self._src_edit = QLineEdit(data.get("src") or "")
        self._src_edit.setPlaceholderText("URL of bestandspad")
        form.addRow("Bron:", self._src_edit)

        layout.addLayout(form)

        # Context
        grp_ctx = QGroupBox("Context")
        ctx_layout = QVBoxLayout(grp_ctx)
        self._ctx_checks: list[tuple[QCheckBox, int]] = []
        for ctx in all_contexts:
            cb = QCheckBox(ctx["name"])
            cb.setChecked(ctx["id"] in assigned_ctx_ids)
            ctx_layout.addWidget(cb)
            self._ctx_checks.append((cb, ctx["id"]))
        layout.addWidget(grp_ctx)

        # Status
        grp_status = QGroupBox("Status")
        grp_layout = QVBoxLayout(grp_status)
        self._done_cb = QCheckBox("Gedaan")
        self._done_cb.setChecked(self.is_done)
        self._todo_cb = QCheckBox("Todo")
        self._todo_cb.setChecked(self.is_todo)
        grp_layout.addWidget(self._done_cb)
        grp_layout.addWidget(self._todo_cb)
        layout.addWidget(grp_status)

        # Recurring
        grp_rec = QGroupBox("Recurring")
        rec_layout = QFormLayout(grp_rec)
        self._rec_cb = QCheckBox("Herhaalbaar  ↺")
        self._rec_cb.setChecked(self.is_recurring)
        self._rec_cb.toggled.connect(self._on_rec_toggle)
        self._interval_combo = QComboBox()
        for val, label in self.INTERVALS:
            self._interval_combo.addItem(label, val)
        cur_idx = next((i for i, (v, _) in enumerate(self.INTERVALS) if v == self.interval), 0)
        self._interval_combo.setCurrentIndex(cur_idx)
        self._interval_combo.setEnabled(self.is_recurring)
        rec_layout.addRow(self._rec_cb)
        rec_layout.addRow("Interval:", self._interval_combo)
        layout.addWidget(grp_rec)

        # Variatie
        grp_var = QGroupBox("Variatie")
        var_layout = QFormLayout(grp_var)
        self._var_combo = QComboBox()
        self._var_combo.addItem("Geen", None)
        for vl in variation_lists:
            self._var_combo.addItem(vl["name"], vl["id"])
        sel_idx = next((i for i in range(self._var_combo.count())
                        if self._var_combo.itemData(i) == self.variation_list_id), 0)
        self._var_combo.setCurrentIndex(sel_idx)
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Lineair", "linear")
        self._mode_combo.addItem("Willekeurig", "random")
        self._mode_combo.setCurrentIndex(0 if self.variation_mode != "random" else 1)
        var_layout.addRow("Lijst:", self._var_combo)
        var_layout.addRow("Methode:", self._mode_combo)
        layout.addWidget(grp_var)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._title_edit.setFocus()
        self._title_edit.selectAll()

    def _on_rec_toggle(self, checked: bool):
        self._interval_combo.setEnabled(checked)

    def _accept(self):
        t = self._title_edit.text().strip()
        if not t:
            return
        self.title          = t
        self.description    = self._desc_edit.toPlainText().strip() or None
        self.start_note     = self._start_note_edit.text().strip() or None
        self.src            = self._src_edit.text().strip() or None
        self.is_done        = self._done_cb.isChecked()
        self.is_todo        = self._todo_cb.isChecked()
        self.is_recurring   = self._rec_cb.isChecked()
        self.interval       = self._interval_combo.currentData() if self.is_recurring else None
        self.variation_list_id = self._var_combo.currentData()
        self.variation_mode = self._mode_combo.currentData() if self.variation_list_id else None
        self.context_ids    = [cid for cb, cid in self._ctx_checks if cb.isChecked()]
        self.accept()


class CleanupHistoryDialog(QDialog):
    """Kies een grens; geschiedenis-records ouder dan die grens worden verwijderd."""

    # (label, dagen) — None betekent custom datum, "all" betekent alles
    PRESETS = [
        ("Ouder dan 1 week", 7),
        ("Ouder dan 1 maand", 30),
        ("Ouder dan 3 maanden", 90),
        ("Ouder dan 6 maanden", 180),
        ("Ouder dan 1 jaar", 365),
        ("Aangepaste datum/tijd…", None),
        ("Alle geschiedenis", "all"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Geschiedenis opschonen")
        self.setMinimumWidth(360)
        # Resultaat: ISO-string van de grens (UTC), of None om alles te verwijderen.
        self.before: str | None = None
        # Leesbare omschrijving van de grens voor de bevestiging (lokale tijd).
        self.before_label: str = ""
        self.delete_all = False

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Verwijder afgevinkte records:"))

        self._combo = QComboBox()
        for label, val in self.PRESETS:
            self._combo.addItem(label, val)
        self._combo.currentIndexChanged.connect(self._on_change)
        layout.addWidget(self._combo)

        self._dt_edit = QDateTimeEdit()
        self._dt_edit.setCalendarPopup(True)
        self._dt_edit.setDisplayFormat("dd-MM-yyyy  HH:mm")
        self._dt_edit.setDateTime(QDateTime.currentDateTime().addMonths(-1))
        self._dt_edit.setEnabled(False)
        layout.addWidget(self._dt_edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Verwijderen")
        btns.accepted.connect(self._accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_change(self):
        self._dt_edit.setEnabled(self._combo.currentData() is None)

    def _accept(self):
        val = self._combo.currentData()
        if val == "all":
            self.delete_all = True
            self.before = None
        elif val is None:
            # Kiezer staat in lokale tijd; tijdstempels worden in UTC opgeslagen.
            # Converteer naar UTC zodat de grens overeenkomt met opslag en presets.
            local_dt = self._dt_edit.dateTime().toPyDateTime()
            self.before_label = local_dt.strftime("%d-%m-%Y  %H:%M")
            self.before = local_dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat()
        else:
            self.before_label = self._combo.currentText().lower()
            cutoff = datetime.utcnow() - timedelta(days=int(val))
            self.before = cutoff.isoformat()
        self.accept()


def confirm_delete(title: str, parent=None) -> bool:
    result = QMessageBox.question(
        parent,
        "Verwijderen",
        f"Verwijder '{title}' en alle subitems?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes,
    )
    return result == QMessageBox.StandardButton.Yes


def show_error(msg: str, parent=None) -> None:
    QMessageBox.critical(parent, "Fout", msg)
