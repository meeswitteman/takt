from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication


def apply_font(app: QApplication, family: str, size: int) -> None:
    font = QFont(family, size)
    app.setFont(font)


def apply_dark(app: QApplication) -> None:
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
    p.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Base,            QColor(42, 42, 42))
    p.setColor(QPalette.ColorRole.AlternateBase,   QColor(50, 50, 50))
    p.setColor(QPalette.ColorRole.ToolTipBase,     QColor(60, 60, 60))
    p.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.Button,          QColor(50, 50, 50))
    p.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    p.setColor(QPalette.ColorRole.BrightText,      QColor(255, 80, 80))
    p.setColor(QPalette.ColorRole.Link,            QColor(42, 130, 218))
    p.setColor(QPalette.ColorRole.Highlight,       QColor(42, 130, 218))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(130, 130, 130))
    app.setPalette(p)
    app.setStyleSheet("""
        QTreeWidget { border: 1px solid #444; }
        QTreeWidget::item { padding: 3px 0; }
        QScrollBar:vertical { width: 10px; background: #2a2a2a; }
        QScrollBar::handle:vertical { background: #555; border-radius: 4px; }
        QFrame#todo-card {
            border: 1px solid #3a3a3a;
            border-radius: 6px;
            background: #2a2a2a;
            margin: 2px 4px;
        }
        QPushButton {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 12px;
            background: #3a3a3a;
        }
        QPushButton:hover { background: #4a4a4a; }
        QPushButton#done-btn {
            background: #1a5a1a;
            border-color: #2a8a2a;
            color: #aaffaa;
            font-weight: bold;
        }
        QPushButton#done-btn:hover { background: #2a7a2a; }
        QComboBox { border: 1px solid #555; border-radius: 4px; padding: 3px 8px; background: #3a3a3a; }
        QLineEdit { border: 1px solid #555; border-radius: 4px; padding: 3px 6px; background: #3a3a3a; }
    """)


def apply_light(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    app.setStyleSheet("""
        QTreeWidget::item { padding: 3px 0; }
        QFrame#todo-card {
            border: 1px solid #ddd;
            border-radius: 6px;
            background: #f8f8f8;
            margin: 2px 4px;
        }
        QPushButton#done-btn {
            background: #d4edda;
            border-color: #28a745;
            color: #155724;
            font-weight: bold;
        }
        QPushButton#done-btn:hover { background: #c3e6cb; }
    """)
