from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import pyqtSignal

from app import client
from app.dialogs import show_error

_CHIP_STYLE = """
    QPushButton {
        border: 1px solid #555; border-radius: 10px;
        padding: 2px 10px; background: transparent; color: #aaa;
    }
    QPushButton:checked {
        background: #0e639c; border-color: #1e88e5; color: white;
    }
    QPushButton:hover:!checked { border-color: #888; color: #ccc; }
"""


class _Chip(QPushButton):
    def __init__(self, label: str, data, on_change, parent=None):
        super().__init__(label, parent)
        self._data = data
        self.setCheckable(True)
        self.setFixedHeight(26)
        self.setStyleSheet(_CHIP_STYLE)
        self.toggled.connect(lambda _: on_change())

    @property
    def item_data(self):
        return self._data


def _hsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color: #333;")
    return f


class FilterTab(QWidget):
    filter_changed = pyqtSignal(list, list)  # context_ids, root_ids

    def __init__(self, initial_ctx_ids: list[int] | None = None,
                 initial_root_ids: list[int] | None = None, parent=None):
        super().__init__(parent)
        self._ctx_chips: list[_Chip] = []
        self._root_chips: list[_Chip] = []
        self._initial_ctx = set(initial_ctx_ids or [])
        self._initial_roots = set(initial_root_ids or [])
        self._build()
        self.reload()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        # Context
        outer.addWidget(QLabel("<b>Context</b>"))
        self._ctx_row = QHBoxLayout()
        self._ctx_row.setSpacing(6)
        outer.addLayout(self._ctx_row)

        outer.addWidget(_hsep())

        # Project
        outer.addWidget(QLabel("<b>Project</b>"))
        self._root_flow = QHBoxLayout()
        self._root_flow.setSpacing(6)
        outer.addLayout(self._root_flow)

        outer.addWidget(_hsep())

        # Clear button
        btn_clear = QPushButton("Filter wissen")
        btn_clear.setFixedWidth(140)
        btn_clear.clicked.connect(self.clear_filter)
        outer.addWidget(btn_clear)

        outer.addStretch()

    def _fill(self, layout: QHBoxLayout, chips: list, items: list,
              id_key: str, label_key: str, initial: set):
        checked = {c.item_data for c in chips if c.isChecked()} if chips else initial
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        chips.clear()
        for item in items:
            chip = _Chip(item[label_key], item[id_key], self._emit)
            chip.setChecked(item[id_key] in checked)
            layout.addWidget(chip)
            chips.append(chip)
        layout.addStretch()

    def reload(self):
        try:
            self._fill(self._ctx_row, self._ctx_chips, client.get_contexts(),
                       "id", "name", self._initial_ctx)
            self._fill(self._root_flow, self._root_chips, client.get_roots(),
                       "id", "title", self._initial_roots)
        except Exception as e:
            show_error(str(e), self)
        self._initial_ctx = set()
        self._initial_roots = set()
        self._emit()

    def clear_filter(self):
        for chip in self._ctx_chips + self._root_chips:
            chip.setChecked(False)

    def _emit(self):
        self.filter_changed.emit(self.context_ids, self.root_ids)

    @property
    def context_ids(self) -> list[int]:
        return [c.item_data for c in self._ctx_chips if c.isChecked()]

    @property
    def root_ids(self) -> list[int]:
        return [c.item_data for c in self._root_chips if c.isChecked()]