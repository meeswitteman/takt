import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QAbstractItemView, QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QKeySequence, QShortcut

from app import client
from app.dialogs import DoneDialog, show_error


_INTERVAL_LABELS = {
    "direct":        "direct",
    "daily":         "dagelijks",
    "weekly":        "wekelijks",
    "weekday:0":     "maandag",
    "weekday:1":     "dinsdag",
    "weekday:2":     "woensdag",
    "weekday:3":     "donderdag",
    "weekday:4":     "vrijdag",
    "weekday:5":     "zaterdag",
    "weekday:6":     "zondag",
    "monthly_first": "1e van de maand",
}

def _interval_label(interval: str | None) -> str:
    return _INTERVAL_LABELS.get(interval or "", interval or "")


class ContextChip(QLabel):
    def __init__(self, name: str, color: str, parent=None):
        super().__init__(f" {name} ", parent)
        self.setStyleSheet(
            f"background: {color}; color: white; border-radius: 3px; padding: 1px 4px;"
        )


class TodoCard(QFrame):
    done_requested = pyqtSignal(dict)

    def __init__(self, item_data: dict, parent=None):
        super().__init__(parent)
        self.item_data = item_data
        self._done = bool(item_data.get("is_done"))
        self.setObjectName("todo-card")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        if self._done:
            self.setProperty("done", "true")
            self.setStyleSheet("#todo-card[done=\"true\"] { color: #777; }")
        self._build()

    def _build(self):
        data = self.item_data
        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)

        info = QVBoxLayout()
        info.setSpacing(3)

        breadcrumb = data.get("breadcrumb", [])
        if breadcrumb:
            bc_lbl = QLabel(" › ".join(breadcrumb))
            bc_lbl.setStyleSheet("color: #666; font-size: 10px;")
            info.addWidget(bc_lbl)

        title = data["title"]
        if data.get("is_recurring"):
            title += "  - " + _interval_label(data.get("recurring_interval"))
        if self._done:
            title_lbl = QLabel(f'<s style="color:#777;">{title}</s>')
        else:
            title_lbl = QLabel(f"<b>{title}</b>")
        title_lbl.setWordWrap(True)
        info.addWidget(title_lbl)

        if data.get("current_variation"):
            var_lbl = QLabel(data["current_variation"])
            var_lbl.setStyleSheet("color: #4ec9b0;")
            info.addWidget(var_lbl)

        if data.get("start_note"):
            note_lbl = QLabel(f"→ {data['start_note']}")
            note_lbl.setStyleSheet("color: #dcdcaa;")
            note_lbl.setWordWrap(True)
            info.addWidget(note_lbl)

        if data.get("src"):
            src = data["src"]
            display = src if len(src) < 60 else src[:57] + "..."
            src_lbl = QLabel(f'<a href="{src}" style="color:#569cd6;">{display}</a>')
            src_lbl.setOpenExternalLinks(False)
            src_lbl.linkActivated.connect(lambda url: webbrowser.open(url))
            info.addWidget(src_lbl)

        contexts = data.get("contexts", [])
        if contexts:
            chip_row = QHBoxLayout()
            chip_row.setSpacing(4)
            for ctx in contexts:
                chip_row.addWidget(ContextChip(ctx["name"], ctx.get("color", "#888")))
            chip_row.addStretch()
            info.addLayout(chip_row)

        outer.addLayout(info, stretch=1)

        if self._done:
            done_lbl = QLabel("✓ gedaan")
            done_lbl.setStyleSheet("color: #6a9955;")
            outer.addWidget(done_lbl, alignment=Qt.AlignmentFlag.AlignVCenter)
        else:
            btn = QPushButton("Klaar")
            btn.setObjectName("done-btn")
            btn.setFixedWidth(70)
            btn.clicked.connect(lambda: self.done_requested.emit(self.item_data))
            outer.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)


class TodosTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._context_ids: list[int] = []
        self._root_ids: list[int] = []
        self._hide_done: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        top = QHBoxLayout()
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet("color: #888;")
        top.addWidget(self._count_lbl)
        top.addStretch()
        layout.addLayout(top)

        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setSpacing(2)
        self._list.setFrameShape(QFrame.Shape.NoFrame)
        self._list.setStyleSheet(
            "QListWidget { background: transparent; }"
            "QListWidget::item { background: transparent; padding: 0; }"
            "QListWidget::item:selected { background: transparent; }"
        )
        layout.addWidget(self._list)

        QShortcut(QKeySequence("Alt+Up"),   self, self._move_up)
        QShortcut(QKeySequence("Alt+Down"), self, self._move_down)

        self.refresh()

    # ------------------------------------------------------------------

    def _make_item(self, data: dict) -> tuple[QListWidgetItem, TodoCard]:
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, data)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if not data.get("is_done"):
            flags |= Qt.ItemFlag.ItemIsDragEnabled   # gedane todo's niet versleepbaar
        item.setFlags(flags)
        card = TodoCard(data)
        card.done_requested.connect(self._on_done)
        card.adjustSize()
        item.setSizeHint(QSize(0, max(card.sizeHint().height(), 60) + 4))
        return item, card

    def _rebuild_widget(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        card = TodoCard(data)
        card.done_requested.connect(self._on_done)
        self._list.setItemWidget(item, card)

    # ------------------------------------------------------------------

    def apply_filter(self, context_ids: list[int], root_ids: list[int], hide_done: bool):
        self._context_ids = context_ids
        self._root_ids = root_ids
        self._hide_done = hide_done
        self.refresh()

    def refresh(self):
        try:
            todos = client.get_todos(
                self._context_ids or None, self._root_ids or None,
                include_done=not self._hide_done,
            )
        except Exception as e:
            show_error(str(e), self)
            return

        self._list.clear()
        open_n = sum(1 for t in todos if not t.get("is_done"))
        done_n = len(todos) - open_n
        self._count_lbl.setText(
            f"{open_n} todo's" + (f"  ·  {done_n} gedaan" if done_n else "")
        )

        for data in todos:
            item, card = self._make_item(data)
            self._list.addItem(item)
            self._list.setItemWidget(item, card)

    # ------------------------------------------------------------------

    def _move_up(self):
        row = self._list.currentRow()
        if row <= 0:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row - 1, item)
        self._rebuild_widget(item)
        self._list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self._list.currentRow()
        if row < 0 or row >= self._list.count() - 1:
            return
        item = self._list.takeItem(row)
        self._list.insertItem(row + 1, item)
        self._rebuild_widget(item)
        self._list.setCurrentRow(row + 1)

    def _on_done(self, item_data: dict):
        dlg = DoneDialog(item_data["title"], parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            client.mark_done(item_data["id"], dlg.note)
            self.refresh()
        except Exception as e:
            show_error(str(e), self)
