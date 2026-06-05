from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QMenu, QWidgetAction,
    QLineEdit, QListWidget, QListWidgetItem, QCheckBox, QLabel,
)
from PyQt6.QtCore import Qt, pyqtSignal

from app import client
from app.dialogs import show_error


_BAR_STYLE = """
    QPushButton#filter-drop {
        border: 1px solid #555; border-radius: 4px;
        padding: 3px 10px; background: transparent; color: #ccc;
        text-align: left;
    }
    QPushButton#filter-drop:hover { border-color: #888; }
    QPushButton#filter-drop[active="true"] {
        border-color: #1e88e5; color: white;
    }
    QPushButton#filter-clear {
        border: none; background: transparent; color: #888; padding: 3px 6px;
    }
    QPushButton#filter-clear:hover { color: #ccc; }
"""


class MultiSelectDropdown(QPushButton):
    """Compacte knop met teller die een zoekbaar checkbox-menu opent."""
    changed = pyqtSignal()

    def __init__(self, prefix: str, parent=None):
        super().__init__(parent)
        self._prefix = prefix
        self._suppress = False
        self.setObjectName("filter-drop")
        self.setMinimumWidth(130)

        self._menu = QMenu(self)
        self.setMenu(self._menu)

        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        self._search = QLineEdit()
        self._search.setPlaceholderText("zoek…")
        self._search.textChanged.connect(self._filter_list)
        lay.addWidget(self._search)

        self._list = QListWidget()
        self._list.setFixedWidth(200)
        self._list.setMaximumHeight(260)
        self._list.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self._list)

        clear = QPushButton("Alles wissen")
        clear.clicked.connect(self.clear)
        lay.addWidget(clear)

        action = QWidgetAction(self._menu)
        action.setDefaultWidget(panel)
        self._menu.addAction(action)
        self._menu.aboutToShow.connect(lambda: (self._search.clear(), self._search.setFocus()))

        self._update_label()

    # -- data -----------------------------------------------------------
    def set_items(self, items: list[tuple[int, str]]):
        """items = [(id, label), ...]; behoud bestaande selectie."""
        checked = self.selected_ids
        self._suppress = True
        self._list.clear()
        for _id, label in items:
            it = QListWidgetItem(label)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setData(Qt.ItemDataRole.UserRole, _id)
            it.setCheckState(
                Qt.CheckState.Checked if _id in checked else Qt.CheckState.Unchecked
            )
            self._list.addItem(it)
        self._suppress = False
        self._update_label()

    def set_selection(self, ids: list[int]):
        wanted = set(ids)
        self._suppress = True
        for i in range(self._list.count()):
            it = self._list.item(i)
            it.setCheckState(
                Qt.CheckState.Checked
                if it.data(Qt.ItemDataRole.UserRole) in wanted
                else Qt.CheckState.Unchecked
            )
        self._suppress = False
        self._update_label()

    @property
    def selected_ids(self) -> list[int]:
        return [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
            if self._list.item(i).checkState() == Qt.CheckState.Checked
        ]

    def clear(self):
        if not self.selected_ids:
            return
        self.set_selection([])
        self.changed.emit()

    # -- intern ---------------------------------------------------------
    def _filter_list(self, text: str):
        text = text.lower()
        for i in range(self._list.count()):
            it = self._list.item(i)
            it.setHidden(text not in it.text().lower())

    def _on_item_changed(self, _item):
        if self._suppress:
            return
        self._update_label()
        self.changed.emit()

    def _update_label(self):
        n = len(self.selected_ids)
        self.setText(f"{self._prefix}: {'alle' if n == 0 else n}")
        self.setProperty("active", "true" if n else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class FilterBar(QWidget):
    # context_ids, root_ids, hide_done
    filter_changed = pyqtSignal(list, list, bool)

    def __init__(self, initial_ctx_ids: list[int] | None = None,
                 initial_root_ids: list[int] | None = None,
                 initial_hide_done: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(_BAR_STYLE)
        self._initial_ctx = list(initial_ctx_ids or [])
        self._initial_roots = list(initial_root_ids or [])

        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        self._ctx = MultiSelectDropdown("Context")
        self._proj = MultiSelectDropdown("Project")
        self._ctx.changed.connect(self._emit)
        self._proj.changed.connect(self._emit)
        lay.addWidget(self._ctx)
        lay.addWidget(self._proj)

        self._hide_done = QCheckBox("verberg gedaan")
        self._hide_done.setChecked(initial_hide_done)
        self._hide_done.toggled.connect(lambda _: self._emit())
        lay.addWidget(self._hide_done)

        lay.addStretch()

        clear = QPushButton("Filter wissen")
        clear.setObjectName("filter-clear")
        clear.clicked.connect(self.clear_filter)
        lay.addWidget(clear)

        self.reload()

    def reload(self):
        try:
            contexts = client.get_contexts()
            roots = client.get_roots()
        except Exception as e:
            show_error(str(e), self)
            return
        self._ctx.set_items([(c["id"], c["name"]) for c in contexts])
        self._proj.set_items([(r["id"], r["title"]) for r in roots])
        if self._initial_ctx or self._initial_roots:
            self._ctx.set_selection(self._initial_ctx)
            self._proj.set_selection(self._initial_roots)
            self._initial_ctx = []
            self._initial_roots = []

    def set_hide_done_enabled(self, enabled: bool):
        self._hide_done.setEnabled(enabled)

    def clear_filter(self):
        self._ctx.set_selection([])
        self._proj.set_selection([])
        self._emit()

    def _emit(self):
        self.filter_changed.emit(self.context_ids, self.root_ids, self.hide_done)

    @property
    def context_ids(self) -> list[int]:
        return self._ctx.selected_ids

    @property
    def root_ids(self) -> list[int]:
        return self._proj.selected_ids

    @property
    def hide_done(self) -> bool:
        return self._hide_done.isChecked()
