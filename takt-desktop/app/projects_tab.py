import os
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QMenu, QLabel,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QKeySequence, QShortcut, QColor, QFont

from app import client
from app.delegates import TitleChipsDelegate, ITEM_DATA_ROLE, ITEM_ID_ROLE, ITEM_LOADED
from app.dialogs import (
    NewItemDialog, RenameDialog, DoneDialog,
    ContextAssignDialog, RecurringDialog, VariationAssignDialog,
    ItemEditDialog, confirm_delete, show_error,
)

INDENT = 28   # pixels per niveau

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


class ProjectsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        bar = QHBoxLayout()
        btn_new = QPushButton("+ Root item")
        btn_new.clicked.connect(self._add_root)
        bar.addWidget(btn_new)

        hint = QLabel("  Alt+↑↓ verplaatsen  |  Tab indenteren  |  Shift+Tab uitdenten  |  F2 hernoemen  |  Ctrl+N sub-item  |  Del verwijderen")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        bar.addWidget(hint)
        bar.addStretch()

        btn_refresh = QPushButton("Vernieuwen")
        btn_refresh.clicked.connect(self._load_roots)
        bar.addWidget(btn_refresh)
        layout.addLayout(bar)

        # Boom
        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(INDENT)
        self._delegate = TitleChipsDelegate(self.tree)
        self.tree.setItemDelegate(self._delegate)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(False)
        self.tree.setStyleSheet("""
            QTreeWidget { border: 1px solid #3a3a3a; }
            QTreeWidget::item { padding: 2px 0; }
            QTreeWidget::item:selected { background: #2a5a8a; }
            QTreeWidget::item:hover:!selected { background: #2a3a4a; }
            QTreeWidget::branch { background: transparent; }
        """)
        layout.addWidget(self.tree)

        # Signalen
        self.tree.itemExpanded.connect(self._on_expanded)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.customContextMenuRequested.connect(self._context_menu)

        # Sneltoetsen
        QShortcut(QKeySequence("F2"),          self, self._rename_selected)
        QShortcut(QKeySequence("Ctrl+N"),      self, self._add_child)
        QShortcut(QKeySequence("Delete"),      self, self._delete_selected)
        QShortcut(QKeySequence("Alt+Up"),      self, self._move_up)
        QShortcut(QKeySequence("Alt+Down"),    self, self._move_down)
        QShortcut(QKeySequence("Tab"),         self, self._indent)
        QShortcut(QKeySequence("Shift+Tab"),   self, self._outdent)

        self._active_root_ids: set[int] = set()
        self._load_roots()

    # ------------------------------------------------------------------
    # Laden
    # ------------------------------------------------------------------

    def apply_filter(self, root_ids: list[int]):
        self._active_root_ids = set(root_ids)
        self._load_roots()

    def _load_roots(self):
        self.tree.clear()
        try:
            roots = client.get_roots()
            if self._active_root_ids:
                roots = [r for r in roots if r["id"] in self._active_root_ids]
            for data in roots:
                self.tree.addTopLevelItem(self._make_node(data))
        except Exception as e:
            show_error(str(e), self)
        if self.tree.topLevelItemCount() == 1:
            self.tree.expandItem(self.tree.topLevelItem(0))

    def _make_node(self, data: dict) -> QTreeWidgetItem:
        node = QTreeWidgetItem()
        self._apply_data(node, data)
        node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        return node

    def _apply_data(self, node: QTreeWidgetItem, data: dict) -> None:
        title = data["title"]
        markers = []
        if data.get("is_todo"):
            markers.append("●")
        if markers:
            title = " ".join(markers) + "  " + title
        if data.get("is_recurring"):
            title += "  - " + _interval_label(data.get("recurring_interval"))
        if data.get("is_done"):
            title = title + "  [v]"
        node.setText(0, title)
        node.setData(0, ITEM_DATA_ROLE, data)
        node.setData(0, ITEM_ID_ROLE, data["id"])
        node.setData(0, ITEM_LOADED, False)
        if data.get("is_done"):
            node.setForeground(0, QColor("#888888"))
        elif data.get("is_todo"):
            node.setForeground(0, QColor("#7ec88a"))
        else:
            node.setForeground(0, QColor("#dcdcdc"))

    def _on_expanded(self, node: QTreeWidgetItem):
        if node.data(0, ITEM_LOADED):
            return
        node.setData(0, ITEM_LOADED, True)
        node.takeChildren()
        item_id = node.data(0, ITEM_ID_ROLE)
        try:
            children = client.get_children(item_id)
        except Exception as e:
            show_error(str(e), self)
            return
        if not children:
            node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)
        else:
            for child_data in children:
                node.addChild(self._make_node(child_data))

    def _refresh_node(self, node: QTreeWidgetItem) -> None:
        try:
            data = client.get_item(node.data(0, ITEM_ID_ROLE))
            self._apply_data(node, data)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_node(self) -> QTreeWidgetItem | None:
        items = self.tree.selectedItems()
        return items[0] if items else None

    def _node_index(self, node: QTreeWidgetItem) -> int:
        parent = node.parent()
        if parent:
            return parent.indexOfChild(node)
        return self.tree.indexOfTopLevelItem(node)

    def _node_parent_id(self, node: QTreeWidgetItem) -> int | None:
        parent = node.parent()
        return parent.data(0, ITEM_ID_ROLE) if parent else None

    def _take_node(self, node: QTreeWidgetItem) -> QTreeWidgetItem:
        parent = node.parent()
        if parent:
            parent.removeChild(node)
        else:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(node))
        return node

    def _insert_node(self, node: QTreeWidgetItem, parent_node: QTreeWidgetItem | None, idx: int):
        if parent_node:
            parent_node.insertChild(idx, node)
            parent_node.setExpanded(True)
            parent_node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        else:
            self.tree.insertTopLevelItem(idx, node)
        self.tree.setCurrentItem(node)

    # ------------------------------------------------------------------
    # Bewegen
    # ------------------------------------------------------------------

    def _move_up(self):
        node = self._selected_node()
        if not node:
            return
        idx = self._node_index(node)
        if idx <= 0:
            return
        parent = node.parent()
        parent_id = self._node_parent_id(node)
        new_idx = idx - 1
        try:
            client.move_item(node.data(0, ITEM_ID_ROLE), parent_id, new_idx)
            self._take_node(node)
            self._insert_node(node, parent, new_idx)
        except Exception as e:
            show_error(str(e), self)

    def _move_down(self):
        node = self._selected_node()
        if not node:
            return
        parent = node.parent()
        parent_id = self._node_parent_id(node)
        idx = self._node_index(node)
        sibling_count = parent.childCount() if parent else self.tree.topLevelItemCount()
        if idx >= sibling_count - 1:
            return
        new_idx = idx + 1
        try:
            client.move_item(node.data(0, ITEM_ID_ROLE), parent_id, new_idx)
            self._take_node(node)
            self._insert_node(node, parent, new_idx)
        except Exception as e:
            show_error(str(e), self)

    def _indent(self):
        """Maak item kind van de vorige sibling (Tab = inspringen)."""
        node = self._selected_node()
        if not node:
            return
        parent = node.parent()
        idx = self._node_index(node)
        if idx <= 0:
            return
        # Vorige sibling
        if parent:
            prev = parent.child(idx - 1)
        else:
            prev = self.tree.topLevelItem(idx - 1)
        if not prev:
            return
        new_parent_id = prev.data(0, ITEM_ID_ROLE)
        new_idx = prev.childCount()
        try:
            client.move_item(node.data(0, ITEM_ID_ROLE), new_parent_id, new_idx)
            self._take_node(node)
            self._insert_node(node, prev, new_idx)
            node.setData(0, ITEM_LOADED, True)
        except Exception as e:
            show_error(str(e), self)

    def _outdent(self):
        """Zet item na zijn ouder (Shift+Tab = uitspringen)."""
        node = self._selected_node()
        if not node:
            return
        parent = node.parent()
        if not parent:
            return
        grandparent = parent.parent()
        grandparent_id = grandparent.data(0, ITEM_ID_ROLE) if grandparent else None
        new_idx = self._node_index(parent) + 1
        try:
            client.move_item(node.data(0, ITEM_ID_ROLE), grandparent_id, new_idx)
            self._take_node(node)
            self._insert_node(node, grandparent, new_idx)
        except Exception as e:
            show_error(str(e), self)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _add_root(self):
        dlg = NewItemDialog(parent_title=None, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            data = client.create_item(None, dlg.title)
            self.tree.addTopLevelItem(self._make_node(data))
        except Exception as e:
            show_error(str(e), self)

    def _add_child(self):
        node = self._selected_node()
        if node is None:
            self._add_root()
            return
        parent_title = node.data(0, ITEM_DATA_ROLE)["title"]
        dlg = NewItemDialog(parent_title=parent_title, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        parent_id = node.data(0, ITEM_ID_ROLE)
        try:
            data = client.create_item(parent_id, dlg.title)
            child = self._make_node(data)
            node.addChild(child)
            node.setExpanded(True)
            node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        except Exception as e:
            show_error(str(e), self)

    def _rename_selected(self):
        node = self._selected_node()
        if not node:
            return
        dlg = RenameDialog(node.data(0, ITEM_DATA_ROLE)["title"], parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            data = client.update_item(node.data(0, ITEM_ID_ROLE), title=dlg.title)
            self._apply_data(node, data)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _delete_selected(self):
        node = self._selected_node()
        if not node:
            return
        if not confirm_delete(node.data(0, ITEM_DATA_ROLE)["title"], self):
            return
        try:
            client.delete_item(node.data(0, ITEM_ID_ROLE))
            self._take_node(node)
        except Exception as e:
            show_error(str(e), self)

    def _toggle_todo(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
        try:
            updated = client.set_todo(node.data(0, ITEM_ID_ROLE), not data.get("is_todo", False))
            self._apply_data(node, updated)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _mark_done(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
        dlg = DoneDialog(data["title"], parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            updated = client.mark_done(data["id"], dlg.note)
            self._apply_data(node, updated)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _assign_contexts(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
        try:
            all_ctx = client.get_contexts()
            assigned = [c["id"] for c in data.get("contexts", [])]
            dlg = ContextAssignDialog(all_ctx, assigned, parent=self)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            updated = client.set_contexts(node.data(0, ITEM_ID_ROLE), dlg.selected_ids)
            self._apply_data(node, updated)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _set_recurring(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
        dlg = RecurringDialog(data.get("is_recurring", False), data.get("recurring_interval"), parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return
        try:
            updated = client.set_recurring(node.data(0, ITEM_ID_ROLE), dlg.is_recurring, dlg.interval)
            self._apply_data(node, updated)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _on_double_click(self, node: QTreeWidgetItem, _col: int):
        data = node.data(0, ITEM_DATA_ROLE)
        if data and data.get("has_children", True):
            return  # Qt verzorgt expand/collapse
        try:
            lists = client.get_variations()
            all_contexts = client.get_contexts()
        except Exception as e:
            show_error(str(e), self)
            return

        dlg = ItemEditDialog(data, lists, all_contexts, parent=self)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return

        try:
            item_id = node.data(0, ITEM_ID_ROLE)
            changed = False
            if (dlg.title != data["title"]
                    or (dlg.description or None) != data.get("description")
                    or (dlg.start_note or None) != data.get("start_note")
                    or (dlg.src or None) != data.get("src")):
                client.update_item(item_id, title=dlg.title,
                                   description=dlg.description or None,
                                   start_note=dlg.start_note or None,
                                   src=dlg.src or None)
                changed = True
            if dlg.is_done != data.get("is_done", False):
                client.set_done(item_id, dlg.is_done)
                for i in range(node.childCount()):
                    self._apply_done_recursive(node.child(i), dlg.is_done)
                changed = True
            if dlg.is_todo != data.get("is_todo", False):
                client.set_todo(item_id, dlg.is_todo)
                changed = True
            if dlg.is_recurring != data.get("is_recurring", False) or dlg.interval != data.get("recurring_interval"):
                client.set_recurring(item_id, dlg.is_recurring, dlg.interval)
                changed = True
            if dlg.variation_list_id != data.get("variation_list_id") or dlg.variation_mode != data.get("variation_mode"):
                client.set_variation(item_id, dlg.variation_list_id, dlg.variation_mode)
                changed = True
            assigned_ids = {c["id"] for c in data.get("contexts", [])}
            if set(dlg.context_ids) != assigned_ids:
                client.set_contexts(item_id, dlg.context_ids)
                changed = True
            if changed:
                updated = client.get_item(item_id)
                self._apply_data(node, updated)
                self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _apply_done_recursive(self, node: QTreeWidgetItem, is_done: bool):
        data = node.data(0, ITEM_DATA_ROLE)
        if data:
            updated = dict(data)
            updated["is_done"] = is_done
            self._apply_data(node, updated)
        for i in range(node.childCount()):
            self._apply_done_recursive(node.child(i), is_done)

    def _toggle_done(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
        new_done = not data.get("is_done", False)
        try:
            updated = client.set_done(node.data(0, ITEM_ID_ROLE), new_done)
            self._apply_data(node, updated)
            for i in range(node.childCount()):
                self._apply_done_recursive(node.child(i), new_done)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _assign_variation(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
        try:
            lists = client.get_variations()
            dlg = VariationAssignDialog(
                lists,
                data.get("variation_list_id"),
                data.get("variation_mode"),
                parent=self,
            )
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            updated = client.set_variation(
                node.data(0, ITEM_ID_ROLE),
                dlg.variation_list_id,
                dlg.mode,
            )
            self._apply_data(node, updated)
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _open_src(self, node: QTreeWidgetItem):
        src = node.data(0, ITEM_DATA_ROLE).get("src")
        if not src:
            return
        if src.startswith("http"):
            webbrowser.open(src)
        else:
            path = Path(src.strip('"'))
            if path.exists():
                os.startfile(str(path))
            else:
                show_error(f"Bestand niet gevonden:\n{src}", self)

    # ------------------------------------------------------------------
    # Contextmenu
    # ------------------------------------------------------------------

    def _context_menu(self, pos: QPoint):
        node = self.tree.itemAt(pos)
        if not node:
            return
        data = node.data(0, ITEM_DATA_ROLE)
        menu = QMenu(self)

        done_label = "Markeren als gedaan  [v]" if not data.get("is_done") else "Niet gedaan markeren"
        menu.addAction(done_label).triggered.connect(lambda: self._toggle_done(node))

        menu.addSeparator()
        act = menu.addAction("Als todo markeren" if not data.get("is_todo") else "Todo verwijderen")
        act.triggered.connect(lambda: self._toggle_todo(node))

        if data.get("is_todo"):
            act2 = menu.addAction("Afvinken...")
            act2.triggered.connect(lambda: self._mark_done(node))

        menu.addSeparator()
        menu.addAction("Context...").triggered.connect(lambda: self._assign_contexts(node))
        menu.addAction("Recurring...").triggered.connect(lambda: self._set_recurring(node))
        menu.addAction("Variatie...").triggered.connect(lambda: self._assign_variation(node))
        menu.addSeparator()
        menu.addAction("Nieuw sub-item  Ctrl+N").triggered.connect(self._add_child)
        menu.addAction("Hernoemen  F2").triggered.connect(self._rename_selected)
        menu.addAction("Verwijderen  Del").triggered.connect(self._delete_selected)

        if data.get("src"):
            menu.addSeparator()
            menu.addAction("Open bron").triggered.connect(lambda: self._open_src(node))

        menu.exec(self.tree.viewport().mapToGlobal(pos))
