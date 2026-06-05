import os
import webbrowser
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView, QMenu, QLabel,
    QPlainTextEdit, QFrame, QLineEdit,
)
from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut

from app import client
from app.delegates import (
    TitleChipsDelegate, ITEM_DATA_ROLE, ITEM_ID_ROLE, ITEM_LOADED,
    ITEM_PENDING, CHEVRON_W, BULLET_W, LEFT_PAD,
)
from app.dialogs import (
    DoneDialog, ContextAssignDialog, RecurringDialog, VariationAssignDialog,
    ItemEditDialog, confirm_delete, show_error,
)

INDENT = 28   # pixels per niveau


class NoteEditor(QPlainTextEdit):
    """Zwevende meerregelige editor voor de omschrijving, onder een item."""
    committed = pyqtSignal()
    cancelled = pyqtSignal()
    lostFocus = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Omschrijving…  (Ctrl/Cmd+Enter = opslaan, Esc = annuleren)")
        self.setFrameShape(QFrame.Shape.StyledPanel)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if e.modifiers() & (Qt.KeyboardModifier.ControlModifier
                                | Qt.KeyboardModifier.MetaModifier):
                self.committed.emit()
                return
            # gewone Enter = nieuwe regel (meerregelig)
        elif e.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            return
        super().keyPressEvent(e)

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.lostFocus.emit()


class OutlineTree(QTreeWidget):
    """QTreeWidget met Workflowy-gedrag: klik op de bullet, Enter = nieuwe regel.

    Klik-zones per rij: chevron (uitklappen), bullet (inzoomen), naam (1 klik =
    bewerken, dubbelklik = volledig dialoog) en — als de omschrijving zichtbaar
    is — de omschrijvingsregel (1 klik = omschrijving bewerken).
    """
    bulletClicked     = pyqtSignal(object)
    enterPressed      = pyqtSignal()
    emptyClicked      = pyqtSignal()
    nameClicked       = pyqtSignal(object)
    nameDoubleClicked = pyqtSignal(object)
    descClicked       = pyqtSignal(object)
    descEditRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_item = None
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._fire_name_click)

    def _fire_name_click(self):
        if self._pending_item is not None:
            item, self._pending_item = self._pending_item, None
            self.nameClicked.emit(item)

    def _zone(self, item, pos) -> str:
        rect = self.visualItemRect(item)
        left = rect.left()
        x, y = pos.x(), pos.y()
        if left <= x < left + CHEVRON_W:
            return "chevron"
        if left + CHEVRON_W <= x < left + CHEVRON_W + BULLET_W:
            return "bullet"
        if x >= left + CHEVRON_W + BULLET_W:
            deleg = self.itemDelegate()
            data = item.data(0, ITEM_DATA_ROLE) or {}
            has_desc = (getattr(deleg, "show_descriptions", False)
                        and bool((data.get("description") or "").strip()))
            if has_desc and y >= rect.top() + deleg.line_height():
                return "desc"
            return "name"
        return "other"

    def mousePressEvent(self, e):
        self._click_timer.stop()
        item = self.itemAt(e.pos())
        if item is None:
            super().mousePressEvent(e)
            self.emptyClicked.emit()
            return
        zone = self._zone(item, e.pos())
        if zone == "chevron":
            data = item.data(0, ITEM_DATA_ROLE)
            if (data and data.get("has_children")) or item.childCount() > 0:
                item.setExpanded(not item.isExpanded())
            return
        if zone == "bullet":
            self.setCurrentItem(item)
            self.bulletClicked.emit(item)
            return
        if zone == "desc":
            self.setCurrentItem(item)
            self.descClicked.emit(item)
            return
        if zone == "name" and e.button() == Qt.MouseButton.LeftButton:
            # Uitstellen zodat een dubbelklik (volledig dialoog) voorrang krijgt.
            self.setCurrentItem(item)
            self._pending_item = item
            self._click_timer.start(QApplication.doubleClickInterval())
            return
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        item = self.itemAt(e.pos())
        if item is not None and self._zone(item, e.pos()) == "name":
            self._click_timer.stop()
            self._pending_item = None
            self.nameDoubleClicked.emit(item)
            return
        super().mouseDoubleClickEvent(e)

    def keyPressEvent(self, e):
        if (e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and self.state() != QAbstractItemView.State.EditingState):
            if e.modifiers() & (Qt.KeyboardModifier.ControlModifier
                                | Qt.KeyboardModifier.MetaModifier):
                self.descEditRequested.emit()   # Ctrl/Cmd+Enter = omschrijving bewerken
            else:
                self.enterPressed.emit()        # Enter = nieuwe regel
            return

        # Beginnen met typen op een geselecteerd item opent de naam-editor en
        # plaatst de getypte tekst achter de bestaande naam (zonder te wissen).
        if (self.state() != QAbstractItemView.State.EditingState
                and e.text() and e.text().isprintable()
                and not (e.modifiers() & (Qt.KeyboardModifier.ControlModifier
                                          | Qt.KeyboardModifier.AltModifier
                                          | Qt.KeyboardModifier.MetaModifier))):
            node = self.currentItem()
            if node is not None:
                self.editItem(node, 0)
                editor = self.findChild(QLineEdit)
                if editor is not None:
                    editor.deselect()
                    editor.setCursorPosition(len(editor.text()))
                    editor.insert(e.text())
                    editor.textEdited.emit(editor.text())  # markeer als wijziging
                return

        super().keyPressEvent(e)


class ProjectsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_root_ids: set[int] = set()
        self._active_ctx_ids: list[int] = []
        self._hide_done: bool = False
        self._zoom_path: list[tuple[int, str]] = []
        self._suppress = False        # onderdruk itemChanged tijdens programmatische updates
        self._pending_node: QTreeWidgetItem | None = None
        self._note_editor: NoteEditor | None = None
        self._note_node: QTreeWidgetItem | None = None
        self._note_idle: QTimer | None = None
        self._idle_timeout_ms = 3000

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Breadcrumb-balk (alleen zichtbaar bij inzoomen)
        self._crumb_bar = QWidget()
        self._crumb_layout = QHBoxLayout(self._crumb_bar)
        self._crumb_layout.setContentsMargins(6, 2, 6, 2)
        self._crumb_layout.setSpacing(2)
        self._crumb_bar.hide()
        layout.addWidget(self._crumb_bar)

        # Boom
        self.tree = OutlineTree()
        self.tree.setColumnCount(1)
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(INDENT)
        self._delegate = TitleChipsDelegate(self.tree)
        self.tree.setItemDelegate(self._delegate)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.setUniformRowHeights(False)   # rijen kunnen een omschrijvingsregel hebben
        self.tree.setAnimated(False)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.tree)

        # Signalen
        self.tree.itemExpanded.connect(self._on_expanded)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.bulletClicked.connect(self._zoom_into)
        self.tree.enterPressed.connect(self._new_sibling)
        self.tree.emptyClicked.connect(self._new_at_current_level)
        self.tree.nameClicked.connect(self._edit_name_node)
        self.tree.nameDoubleClicked.connect(self._open_edit_dialog)
        self.tree.descClicked.connect(self._edit_description)
        self.tree.descEditRequested.connect(self._edit_description_selected)
        self._delegate.closeEditor.connect(self._on_close_editor)

        # Sneltoetsen
        QShortcut(QKeySequence("F2"),        self.tree, self._edit_selected)
        QShortcut(QKeySequence("Ctrl+N"),    self.tree, self._add_child)
        QShortcut(QKeySequence("Delete"),    self.tree, self._delete_selected)
        QShortcut(QKeySequence("Alt+Up"),    self.tree, self._move_up)
        QShortcut(QKeySequence("Alt+Down"),  self.tree, self._move_down)
        QShortcut(QKeySequence("Tab"),       self.tree, self._indent)
        QShortcut(QKeySequence("Shift+Tab"), self.tree, self._outdent)

        self._load()

    # ------------------------------------------------------------------
    # Laden / inzoomen
    # ------------------------------------------------------------------

    @property
    def _current_parent_id(self) -> int | None:
        return self._zoom_path[-1][0] if self._zoom_path else None

    def apply_filter(self, context_ids: list[int], root_ids: list[int], hide_done: bool):
        self._active_ctx_ids = list(context_ids)
        self._active_root_ids = set(root_ids)
        self._hide_done = hide_done
        self._zoom_path = []
        self._load()

    @property
    def _filtered(self) -> bool:
        """Gefilterde boom-modus: context-filter actief of gedane items verborgen."""
        return bool(self._active_ctx_ids) or self._hide_done

    def _load(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        self.tree.blockSignals(False)

        # Binnen een zoom: gewone (lazy) weergave van de kinderen.
        if self._zoom_path:
            try:
                items = client.get_children(self._zoom_path[-1][0])
            except Exception as e:
                show_error(str(e), self)
                items = []
            for data in items:
                self.tree.addTopLevelItem(self._make_node(data))
            self._build_breadcrumb()
            return

        # Gefilterde modus: hele (gesnoeide) boom in één keer ophalen.
        if self._filtered:
            try:
                roots = list(self._active_root_ids) or None
                items = client.get_tree(self._active_ctx_ids or None, roots, self._hide_done)
            except Exception as e:
                show_error(str(e), self)
                items = []
            for data in items:
                self.tree.addTopLevelItem(self._make_tree_node(data))
            self._build_breadcrumb()
            if self._active_ctx_ids:
                self.tree.expandAll()   # auto-uitklappen naar treffers
            return

        # Geen filter: gewone lazy weergave van de roots.
        try:
            items = client.get_roots()
            if self._active_root_ids:
                items = [r for r in items if r["id"] in self._active_root_ids]
        except Exception as e:
            show_error(str(e), self)
            items = []
        for data in items:
            self.tree.addTopLevelItem(self._make_node(data))
        self._build_breadcrumb()
        if self.tree.topLevelItemCount() == 1:
            self.tree.expandItem(self.tree.topLevelItem(0))

    def _make_tree_node(self, data: dict) -> QTreeWidgetItem:
        """Bouw een node met al ingeladen (gefilterde) kinderen."""
        node = self._make_node(data)
        node.setData(0, ITEM_LOADED, True)
        children = data.get("children") or []
        for child in children:
            node.addChild(self._make_tree_node(child))
        policy = (QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                  if children
                  else QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)
        node.setChildIndicatorPolicy(policy)
        return node

    def _zoom_into(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
        if not data:
            return
        self._zoom_path.append((data["id"], data["title"]))
        self._load()

    def _zoom_to(self, depth: int):
        """Navigeer naar een niveau in de breadcrumb (0 = Home)."""
        self._zoom_path = self._zoom_path[:depth]
        self._load()

    def _build_breadcrumb(self):
        while self._crumb_layout.count():
            item = self._crumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self._zoom_path:
            self._crumb_bar.hide()
            return

        def crumb(text: str, depth: int, active: bool):
            if active:
                lbl = QLabel(text)
                lbl.setStyleSheet("font-weight: bold; padding: 2px 4px;")
                return lbl
            btn = QPushButton(text)
            btn.setObjectName("crumb")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda: self._zoom_to(depth))
            return btn

        self._crumb_layout.addWidget(crumb("Home", 0, False))
        for i, (_id, title) in enumerate(self._zoom_path):
            sep = QLabel("›")
            sep.setStyleSheet("color: #888; padding: 0 2px;")
            self._crumb_layout.addWidget(sep)
            self._crumb_layout.addWidget(crumb(title, i + 1, i == len(self._zoom_path) - 1))
        self._crumb_layout.addStretch()
        self._crumb_bar.show()

    # ------------------------------------------------------------------
    # Node-opbouw
    # ------------------------------------------------------------------

    def _make_node(self, data: dict) -> QTreeWidgetItem:
        node = QTreeWidgetItem()
        node.setData(0, ITEM_LOADED, False)
        node.setData(0, ITEM_PENDING, False)
        self._apply_data(node, data)
        policy = (QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                  if data.get("has_children")
                  else QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator)
        node.setChildIndicatorPolicy(policy)
        return node

    def _apply_data(self, node: QTreeWidgetItem, data: dict) -> None:
        self._suppress = True
        node.setText(0, data["title"])
        node.setData(0, ITEM_DATA_ROLE, data)
        node.setData(0, ITEM_ID_ROLE, data["id"])
        node.setFlags(node.flags() | Qt.ItemFlag.ItemIsEditable)
        self._suppress = False

    def _on_expanded(self, node: QTreeWidgetItem):
        if node.data(0, ITEM_LOADED):
            return
        node.setData(0, ITEM_LOADED, True)
        node.takeChildren()
        try:
            children = client.get_children(node.data(0, ITEM_ID_ROLE))
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
    # Inline bewerken
    # ------------------------------------------------------------------

    def _edit_selected(self):
        node = self._selected_node()
        if node:
            self.tree.editItem(node, 0)

    def _edit_name_node(self, node: QTreeWidgetItem):
        if node is not None:
            self.tree.editItem(node, 0)

    # ------------------------------------------------------------------
    # Omschrijving inline bewerken (zwevende editor onder het item)
    # ------------------------------------------------------------------

    def set_show_descriptions(self, show: bool):
        self._delegate.show_descriptions = show
        self._close_note_editor(commit=False)
        self.tree.scheduleDelayedItemsLayout()
        self.tree.viewport().update()

    def set_idle_timeout(self, seconds: float):
        """Tijd zonder wijziging waarna een editor automatisch sluit."""
        self._idle_timeout_ms = max(1, int(seconds)) * 1000
        self._delegate.idle_timeout_ms = self._idle_timeout_ms

    def _note_idle_close(self):
        self._close_note_editor(commit=False)
        self.tree.setFocus()   # zodat Ctrl/Cmd+Enter daarna blijft werken

    def _edit_description_selected(self):
        node = self._selected_node()
        if node is not None:
            self._edit_description(node)

    def _edit_description(self, node: QTreeWidgetItem):
        self._close_note_editor(commit=False)
        data = node.data(0, ITEM_DATA_ROLE) or {}
        rect = self.tree.visualItemRect(node)
        if not rect.isValid():
            return
        ed = NoteEditor(self.tree.viewport())
        ed.setPlainText(data.get("description") or "")
        dx = rect.left() + LEFT_PAD
        top = rect.top() + self._delegate.line_height()
        width = max(160, self.tree.viewport().width() - dx - 8)
        ed.setGeometry(dx, top, width, 84)
        ed.committed.connect(lambda: self._close_note_editor(commit=True))
        ed.cancelled.connect(lambda: self._close_note_editor(commit=False))
        ed.lostFocus.connect(lambda: self._close_note_editor(commit=True))
        # Sluit na 3s zonder wijziging weer af.
        self._note_idle = QTimer(self)
        self._note_idle.setSingleShot(True)
        self._note_idle.timeout.connect(self._note_idle_close)
        ed.textChanged.connect(self._note_idle.stop)   # wijziging → niet meer sluiten
        self._note_editor = ed
        self._note_node = node
        ed.show()
        ed.setFocus()
        ed.moveCursor(ed.textCursor().MoveOperation.End)
        self._note_idle.start(self._idle_timeout_ms)

    def _close_note_editor(self, commit: bool):
        if self._note_idle is not None:
            self._note_idle.stop()
            self._note_idle = None
        ed, node = self._note_editor, self._note_node
        if ed is None:
            return
        self._note_editor = None
        self._note_node = None
        text = ed.toPlainText().strip()
        ed.deleteLater()
        if not commit or node is None:
            return
        old = ((node.data(0, ITEM_DATA_ROLE) or {}).get("description") or "").strip()
        if text == old:
            return
        try:
            updated = client.update_item(node.data(0, ITEM_ID_ROLE), description=text or None)
            self._apply_data(node, updated)
            self.tree.scheduleDelayedItemsLayout()
            self.tree.viewport().update()
        except Exception as e:
            show_error(str(e), self)

    def _on_item_changed(self, node: QTreeWidgetItem, _col: int):
        if self._suppress:
            return
        new_title = node.text(0).strip()
        pending = node.data(0, ITEM_PENDING)
        item_id = node.data(0, ITEM_ID_ROLE)

        if pending:
            node.setData(0, ITEM_PENDING, False)
            self._pending_node = None
            if not new_title:
                self._discard_node(node, item_id)
                return
        elif not new_title:
            self._refresh_node(node)   # lege titel niet toegestaan → herstel
            return
        else:
            old = node.data(0, ITEM_DATA_ROLE) or {}
            if new_title == old.get("title"):
                return
        try:
            data = client.update_item(item_id, title=new_title)
            self._apply_data(node, data)
        except Exception as e:
            show_error(str(e), self)

    def _on_close_editor(self, _editor, _hint):
        # Esc op een net aangemaakt (leeg) item → weer opruimen.
        node = self._pending_node
        if node is not None and node.data(0, ITEM_PENDING):
            node.setData(0, ITEM_PENDING, False)
            self._pending_node = None
            if not node.text(0).strip():
                self._discard_node(node, node.data(0, ITEM_ID_ROLE))

    def _discard_node(self, node: QTreeWidgetItem, item_id):
        try:
            client.delete_item(item_id)
        except Exception:
            pass
        self._take_node(node)

    def _clear_todo_local(self, node: QTreeWidgetItem) -> None:
        """Werk de cache bij: een ouder is geen todo meer (backend doet dit ook)."""
        data = node.data(0, ITEM_DATA_ROLE)
        if data and data.get("is_todo"):
            updated = dict(data)
            updated["is_todo"] = False
            self._apply_data(node, updated)
            self.tree.viewport().update()

    def _begin_new(self, parent_id, parent_node: QTreeWidgetItem | None, idx: int):
        try:
            data = client.create_item(parent_id, "")
        except Exception as e:
            show_error(str(e), self)
            return
        node = self._make_node(data)
        node.setData(0, ITEM_PENDING, True)
        if parent_node is not None:
            parent_node.insertChild(idx, node)
            parent_node.setExpanded(True)
            parent_node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            self._clear_todo_local(parent_node)
        else:
            self.tree.insertTopLevelItem(idx, node)
        # Zet de backend-volgorde gelijk aan de UI-positie
        try:
            client.move_item(data["id"], parent_id, idx)
        except Exception:
            pass
        self._pending_node = node
        self.tree.setCurrentItem(node)
        self.tree.editItem(node, 0)

    def _new_sibling(self):
        node = self._selected_node()
        if node is None:
            self._new_at_current_level()
            return
        parent = node.parent()
        parent_id = self._node_parent_id(node)
        idx = self._node_index(node) + 1
        self._begin_new(parent_id, parent, idx)

    def _new_at_current_level(self):
        count = self.tree.topLevelItemCount()
        self._begin_new(self._current_parent_id, None, count)

    def _add_child(self):
        node = self._selected_node()
        if node is None:
            self._new_at_current_level()
            return
        self._begin_new(node.data(0, ITEM_ID_ROLE), node, node.childCount())

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
        if parent:
            return parent.data(0, ITEM_ID_ROLE)
        return self._current_parent_id

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
        prev = parent.child(idx - 1) if parent else self.tree.topLevelItem(idx - 1)
        if not prev:
            return
        new_parent_id = prev.data(0, ITEM_ID_ROLE)
        new_idx = prev.childCount()
        try:
            client.move_item(node.data(0, ITEM_ID_ROLE), new_parent_id, new_idx)
            self._take_node(node)
            self._insert_node(node, prev, new_idx)
            node.setData(0, ITEM_LOADED, True)
            self._clear_todo_local(prev)
        except Exception as e:
            show_error(str(e), self)

    def _outdent(self):
        """Zet item na zijn ouder (Shift+Tab = uitspringen)."""
        node = self._selected_node()
        if not node:
            return
        parent = node.parent()
        if not parent:
            return   # top-level binnen de huidige weergave: niet verder uit te springen
        grandparent = parent.parent()
        grandparent_id = grandparent.data(0, ITEM_ID_ROLE) if grandparent else self._current_parent_id
        new_idx = self._node_index(parent) + 1
        try:
            client.move_item(node.data(0, ITEM_ID_ROLE), grandparent_id, new_idx)
            self._take_node(node)
            self._insert_node(node, grandparent, new_idx)
        except Exception as e:
            show_error(str(e), self)

    # ------------------------------------------------------------------
    # CRUD / status
    # ------------------------------------------------------------------

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

    def _open_edit_dialog(self, node: QTreeWidgetItem):
        data = node.data(0, ITEM_DATA_ROLE)
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
                lists, data.get("variation_list_id"), data.get("variation_mode"), parent=self,
            )
            if dlg.exec() != dlg.DialogCode.Accepted:
                return
            updated = client.set_variation(
                node.data(0, ITEM_ID_ROLE), dlg.variation_list_id, dlg.mode,
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

        menu.addAction("Inzoomen").triggered.connect(lambda: self._zoom_into(node))
        menu.addSeparator()

        done_label = "Markeren als gedaan" if not data.get("is_done") else "Niet gedaan markeren"
        menu.addAction(done_label).triggered.connect(lambda: self._toggle_done(node))

        act = menu.addAction("Als todo markeren" if not data.get("is_todo") else "Todo verwijderen")
        act.triggered.connect(lambda: self._toggle_todo(node))

        if data.get("is_todo"):
            menu.addAction("Afvinken...").triggered.connect(lambda: self._mark_done(node))

        menu.addSeparator()
        menu.addAction("Context...").triggered.connect(lambda: self._assign_contexts(node))
        menu.addAction("Recurring...").triggered.connect(lambda: self._set_recurring(node))
        menu.addAction("Variatie...").triggered.connect(lambda: self._assign_variation(node))
        menu.addAction("Bewerken...").triggered.connect(lambda: self._open_edit_dialog(node))
        menu.addSeparator()
        menu.addAction("Nieuw sub-item  Ctrl+N").triggered.connect(self._add_child)
        menu.addAction("Hernoemen  F2").triggered.connect(self._edit_selected)
        menu.addAction("Verwijderen  Del").triggered.connect(self._delete_selected)

        if data.get("src"):
            menu.addSeparator()
            menu.addAction("Open bron").triggered.connect(lambda: self._open_src(node))

        menu.exec(self.tree.viewport().mapToGlobal(pos))
