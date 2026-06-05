from PyQt6.QtWidgets import (
    QStyledItemDelegate, QAbstractItemDelegate, QApplication, QStyle, QStyleOptionViewItem,
)
from PyQt6.QtGui import QPainter, QColor, QBrush, QPalette, QPen, QFont, QPolygonF, QFontMetrics
from PyQt6.QtCore import Qt, QRect, QRectF, QSize, QPointF, QTimer

from app import theme as theme_module

ITEM_DATA_ROLE = Qt.ItemDataRole.UserRole
ITEM_ID_ROLE   = Qt.ItemDataRole.UserRole + 1
ITEM_LOADED    = Qt.ItemDataRole.UserRole + 2
ITEM_PENDING   = Qt.ItemDataRole.UserRole + 3   # net aangemaakt, nog leeg

CHIP_H       = 16
CHIP_PADDING = 5
CHIP_RADIUS  = 3
CHIP_GAP     = 4

CHEVRON_W = 16       # zone links voor het uitklap-driehoekje
BULLET_W  = 18       # zone voor de bullet (na de chevron)
LEFT_PAD  = CHEVRON_W + BULLET_W   # waar de tekst begint
BULLET_R  = 3        # straal van het gevulde bolletje
RING_R    = 9        # diameter van de ring bij ingeklapte kinderen

_INTERVAL_LABELS = {
    "direct": "direct", "daily": "dagelijks", "weekly": "wekelijks",
    "weekday:0": "maandag", "weekday:1": "dinsdag", "weekday:2": "woensdag",
    "weekday:3": "donderdag", "weekday:4": "vrijdag", "weekday:5": "zaterdag",
    "weekday:6": "zondag", "monthly_first": "1e van de maand",
}


def _interval_label(interval) -> str:
    return _INTERVAL_LABELS.get(interval or "", interval or "")


class TitleChipsDelegate(QStyledItemDelegate):
    IDLE_TIMEOUT_MS = 3000   # sluit de editor na zoveel ms zonder wijziging

    def __init__(self, tree, spacing: int = 12):
        super().__init__(tree)
        self._tree = tree
        self.spacing = spacing
        self.show_descriptions = False
        self._idle_timer: QTimer | None = None
        self._idle_editor = None

    # ------------------------------------------------------------------
    # Auto-sluiten bij inactiviteit (na single-click in edit, niets gewijzigd)
    # ------------------------------------------------------------------

    def createEditor(self, parent, option, index):
        editor = super().createEditor(parent, option, index)
        # Niet voor net aangemaakte (lege) items: die mogen rustig blijven staan.
        if not index.data(ITEM_PENDING):
            self._arm_idle(editor)
        return editor

    def _arm_idle(self, editor):
        if self._idle_timer is None:
            self._idle_timer = QTimer(self)
            self._idle_timer.setSingleShot(True)
            self._idle_timer.setInterval(self.IDLE_TIMEOUT_MS)
            self._idle_timer.timeout.connect(self._on_idle_timeout)
        self._idle_editor = editor
        if hasattr(editor, "textEdited"):
            editor.textEdited.connect(self._disarm_idle)   # wijziging → niet meer sluiten
        editor.destroyed.connect(lambda *_: self._disarm_idle())
        self._idle_timer.start()

    def _disarm_idle(self, *args):
        if self._idle_timer is not None:
            self._idle_timer.stop()

    def _on_idle_timeout(self):
        editor, self._idle_editor = self._idle_editor, None
        if editor is not None:
            self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.RevertModelCache)

    def line_height(self) -> int:
        """Hoogte van de titelregel (zonder eventuele omschrijvingsregel)."""
        fm = QFontMetrics(self._tree.font())
        return max(fm.height() + self.spacing, CHIP_H + 10)

    def _description(self, index) -> str:
        if not self.show_descriptions:
            return ""
        data = index.data(ITEM_DATA_ROLE) or {}
        return (data.get("description") or "").strip()

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)

        title = opt.text
        opt.text = ""   # laat Qt achtergrond/selectie tekenen, niet de tekst

        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)

        data = index.data(ITEM_DATA_ROLE) or {}
        contexts = data.get("contexts", [])
        is_done = data.get("is_done", False)
        is_todo = data.get("is_todo", False)

        pal = theme_module.CURRENT
        selected = bool(opt.state & QStyle.StateFlag.State_Selected)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        left = opt.rect.left()
        y = opt.rect.top()
        h = opt.rect.height()
        lh = self.line_height()           # hoogte van de titelregel
        cy = y + lh // 2                  # bullet/titel uitlijnen op de titelregel

        has_children = bool(opt.state & QStyle.StateFlag.State_Children)
        expanded = bool(opt.state & QStyle.StateFlag.State_Open)
        collapsed = has_children and not expanded

        cx = left + CHEVRON_W + BULLET_W // 2   # x van de bullet (ook voor gidslijnen)

        # ----- Workflowy-gidslijnen -----
        # Dunne verticale lijn die de bullet van een ouder met die van zijn
        # subitems verbindt. Per rij tekenen we een segment in de kolom van
        # elke voorouder; opeenvolgende rijen vormen zo een doorlopende lijn.
        indent = self._tree.indentation()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        painter.setPen(QPen(QColor(pal["border"]), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Verbinding van deze (uitgeklapte) ouder omlaag naar zijn eerste kind.
        if has_children and expanded:
            painter.drawLine(cx, cy, cx, y + h)

        # Segmenten voor elke voorouder, met nette terminatie bij het laatste kind.
        child = index
        anc = index.parent()
        level = 1
        while anc.isValid():
            x_anc = left - level * indent + CHEVRON_W + BULLET_W // 2
            siblings = anc.model().rowCount(anc)
            is_last = child.row() == siblings - 1
            if not is_last:
                painter.drawLine(x_anc, y, x_anc, y + h)
            elif child == index:
                # Directe laatste kind-rij: stop bij de bullet i.p.v. doorlopen.
                painter.drawLine(x_anc, y, x_anc, cy)
            # else: diepere afstammeling onder het laatste kind → geen lijn
            child = anc
            anc = anc.parent()
            level += 1

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # ----- Chevron (uitklap-driehoekje, draait mee) -----
        if has_children:
            chx = left + CHEVRON_W // 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(pal["text_dim"])))
            if expanded:
                pts = [QPointF(chx - 4, cy - 2), QPointF(chx + 4, cy - 2), QPointF(chx, cy + 3)]
            else:
                pts = [QPointF(chx - 2, cy - 4), QPointF(chx - 2, cy + 4), QPointF(chx + 3, cy)]
            painter.drawPolygon(QPolygonF(pts))

        # ----- Bullet (+ ring bij ingeklapte kinderen) -----
        if collapsed:
            ring = QColor(pal["bullet"])
            ring.setAlpha(80)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(ring))
            painter.drawEllipse(QRectF(cx - RING_R / 2, cy - RING_R / 2, RING_R, RING_R))

        if is_done:
            bullet_color = QColor(pal["done"])
        elif is_todo:
            bullet_color = QColor(pal["todo"])
        else:
            bullet_color = QColor(pal["bullet"])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bullet_color))
        painter.drawEllipse(QRectF(cx - BULLET_R, cy - BULLET_R, BULLET_R * 2, BULLET_R * 2))

        # ----- Titel -----
        x = left + LEFT_PAD
        font = QFont(opt.font)
        if is_done:
            font.setStrikeOut(True)
        painter.setFont(font)
        fm = painter.fontMetrics()

        if selected:
            text_color = opt.palette.color(QPalette.ColorRole.HighlightedText)
        elif is_done:
            text_color = QColor(pal["done"])
        else:
            text_color = QColor(pal["text"])
        painter.setPen(QPen(text_color))

        tw = fm.horizontalAdvance(title)
        painter.drawText(QRect(x, y, tw + 4, lh), Qt.AlignmentFlag.AlignVCenter, title)
        x += tw + 8

        # ----- Recurring-suffix -----
        if data.get("is_recurring"):
            suffix = "↺ " + _interval_label(data.get("recurring_interval"))
            painter.setFont(QFont(opt.font))
            painter.setPen(QPen(QColor(pal["text_dim"])))
            sw = painter.fontMetrics().horizontalAdvance(suffix)
            painter.drawText(QRect(x, y, sw + 4, lh), Qt.AlignmentFlag.AlignVCenter, suffix)
            x += sw + 8

        # ----- Context-chips -----
        painter.setFont(QFont(opt.font))
        fm = painter.fontMetrics()
        chip_y = cy - CHIP_H // 2
        for ctx in contexts:
            name = ctx["name"]
            cw = fm.horizontalAdvance(name) + CHIP_PADDING * 2
            painter.setBrush(QBrush(QColor(ctx.get("color", "#888888"))))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, chip_y, cw, CHIP_H), CHIP_RADIUS, CHIP_RADIUS)
            painter.setPen(QColor("white"))
            painter.drawText(QRect(x, chip_y, cw, CHIP_H), Qt.AlignmentFlag.AlignCenter, name)
            x += cw + CHIP_GAP

        # ----- Omschrijving (tweede regel) -----
        desc = self._description(index)
        if desc:
            desc = desc.splitlines()[0]
            painter.setFont(QFont(opt.font))
            painter.setPen(QPen(QColor(pal["text_dim"])))
            dfm = painter.fontMetrics()
            dx = left + LEFT_PAD
            dw = max(0, opt.rect.right() - dx - 6)
            drect = QRect(dx, y + lh, dw, h - lh)
            elided = dfm.elidedText(desc, Qt.TextElideMode.ElideRight, dw)
            painter.drawText(drect, Qt.AlignmentFlag.AlignVCenter, elided)

        painter.restore()

    def updateEditorGeometry(self, editor, option, index):
        # Schuif de inline-editor voorbij chevron + bullet, beperkt tot de titelregel.
        rect = QRect(option.rect)
        rect.setLeft(option.rect.left() + LEFT_PAD)
        rect.setHeight(self.line_height())
        editor.setGeometry(rect)

    def sizeHint(self, option, index):
        h = self.line_height()
        if self._description(index):
            h += QFontMetrics(self._tree.font()).height() + 4
        return QSize(option.rect.width(), h)
