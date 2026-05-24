from PyQt6.QtWidgets import QStyledItemDelegate, QApplication, QStyle, QStyleOptionViewItem
from PyQt6.QtGui import QPainter, QColor, QBrush, QPalette
from PyQt6.QtCore import Qt, QRect, QRectF, QSize

ITEM_DATA_ROLE = Qt.ItemDataRole.UserRole
ITEM_ID_ROLE   = Qt.ItemDataRole.UserRole + 1
ITEM_LOADED    = Qt.ItemDataRole.UserRole + 2

CHIP_H       = 16
CHIP_PADDING = 5
CHIP_RADIUS  = 3
CHIP_GAP     = 4


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

        # Data direct uit index — sneller dan itemFromIndex()
        data = index.data(ITEM_DATA_ROLE)
        contexts = data.get("contexts", []) if data else []

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if opt.state & QStyle.StateFlag.State_Selected:
            painter.setPen(opt.palette.color(QPalette.ColorRole.HighlightedText))
        else:
            painter.setPen(opt.palette.color(QPalette.ColorRole.Text))

        fm = painter.fontMetrics()
        text_rect = style.subElementRect(
            QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget
        )
        x = text_rect.left() + 2
        y = opt.rect.top()
        h = opt.rect.height()

        # Titel
        tw = fm.horizontalAdvance(title)
        painter.drawText(QRect(x, y, tw + 4, h), Qt.AlignmentFlag.AlignVCenter, title)
        x += tw + 10

        # Chips
        chip_y = y + (h - CHIP_H) // 2
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

    def sizeHint(self, option, index):
        row_h = max(option.fontMetrics.height() + self.spacing, CHIP_H + 10)
        return QSize(option.rect.width(), row_h)
