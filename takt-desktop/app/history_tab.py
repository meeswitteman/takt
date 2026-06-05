from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QFrame, QSizePolicy, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize

from app import client
from app.dialogs import show_error, CleanupHistoryDialog


def _fmt_dt(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        # Tijdstempels worden naïef in UTC opgeslagen; toon ze in lokale tijd.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone().strftime("%d-%m-%Y  %H:%M")
    except Exception:
        return dt_str


class HistoryCard(QFrame):
    def __init__(self, entry: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("todo-card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._build(entry)

    def _build(self, entry: dict):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)

        info = QVBoxLayout()
        info.setSpacing(3)

        breadcrumb = entry.get("breadcrumb", [])
        if breadcrumb:
            bc_lbl = QLabel(" › ".join(breadcrumb))
            bc_lbl.setStyleSheet("color: #666; font-size: 10px;")
            info.addWidget(bc_lbl)

        title_lbl = QLabel(f"<b>{entry['item_title']}</b>")
        title_lbl.setWordWrap(True)
        info.addWidget(title_lbl)

        if entry.get("variation_value"):
            var_lbl = QLabel(entry["variation_value"])
            var_lbl.setStyleSheet("color: #4ec9b0;")
            info.addWidget(var_lbl)

        if entry.get("note"):
            note_lbl = QLabel(f"→ {entry['note']}")
            note_lbl.setStyleSheet("color: #dcdcaa;")
            note_lbl.setWordWrap(True)
            info.addWidget(note_lbl)

        outer.addLayout(info, stretch=1)

        dt_lbl = QLabel(_fmt_dt(entry.get("completed_at", "")))
        dt_lbl.setStyleSheet("color: #888; font-size: 10px;")
        dt_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(dt_lbl)


class HistoryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        top = QHBoxLayout()
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color: #888;")
        top.addWidget(self._count_lbl)
        top.addStretch()
        self._cleanup_btn = QPushButton("🗑 Opschonen…")
        self._cleanup_btn.clicked.connect(self._cleanup)
        top.addWidget(self._cleanup_btn)
        layout.addLayout(top)

        self._list = QListWidget()
        self._list.setSpacing(2)
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setStyleSheet(
            "QListWidget { background: transparent; }"
            "QListWidget::item { background: transparent; padding: 0; }"
            "QListWidget::item:selected { background: transparent; }"
        )
        layout.addWidget(self._list)

    def refresh(self):
        try:
            entries = client.get_all_history()
        except Exception as e:
            show_error(str(e), self)
            return

        self._list.clear()
        self._count_lbl.setText(f"{len(entries)} gedaan")

        for entry in entries:
            item = QListWidgetItem()
            card = HistoryCard(entry)
            card.adjustSize()
            item.setSizeHint(QSize(0, max(card.sizeHint().height(), 52) + 4))
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    def _cleanup(self):
        dlg = CleanupHistoryDialog(self)
        if dlg.exec() != CleanupHistoryDialog.DialogCode.Accepted:
            return

        if dlg.delete_all:
            msg = "Weet je zeker dat je ALLE geschiedenis wilt verwijderen?"
        else:
            msg = f"Alle records van vóór {dlg.before_label} verwijderen?"

        if QMessageBox.question(
            self, "Geschiedenis opschonen", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return

        try:
            deleted = client.delete_history(dlg.before)
        except Exception as e:
            show_error(str(e), self)
            return

        self.refresh()
        QMessageBox.information(self, "Opgeschoond", f"{deleted} record(s) verwijderd.")
