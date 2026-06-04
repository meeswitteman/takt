from PyQt6.QtWidgets import QStyledItemDelegate, QApplication, QStyle, QStyleOptionViewItem
from PyQt6.QtGui import QPainter, QColor, QBrush, QPalette, QPen, QFont, QPolygonF
from PyQt6.QtCore import Qt, QRect, QRectF, QSize, QPointF

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
    def __init__(self, tree, spacing: int = 12):
        super().__init__(tree)
        self._tree = tree
        self.spacing = spacing

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
        cy = y + h // 2

        has_children = bool(opt.state & QStyle.StateFlag.State_Children)
        expanded = bool(opt.state & QStyle.StateFlag.State_Open)
        collapsed = has_children and not expanded

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
        cx = left + CHEVRON_W + BULLET_W // 2

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
        painter.drawText(QRect(x, y, tw + 4, h), Qt.AlignmentFlag.AlignVCenter, title)
        x += tw + 8

        # ----- Recurring-suffix -----
        if data.get("is_recurring"):
            suffix = "↺ " + _interval_label(data.get("recurring_interval"))
            painter.setFont(QFont(opt.font))
            painter.setPen(QPen(QColor(pal["text_dim"])))
            sw = painter.fontMetrics().horizontalAdvance(suffix)
            painter.drawText(QRect(x, y, sw + 4, h), Qt.AlignmentFlag.AlignVCenter, suffix)
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

        painter.restore()

    def updateEditorGeometry(self, editor, option, index):
        # Schuif de inline-editor voorbij chevron + bullet zodat tekst niet overlapt.
        rect = QRect(option.rect)
        rect.setLeft(option.rect.left() + LEFT_PAD)
        editor.setGeometry(rect)

    def sizeHint(self, option, index):
        row_h = max(option.fontMetrics.height() + self.spacing, CHIP_H + 10)
        return QSize(option.rect.width(), row_h)
