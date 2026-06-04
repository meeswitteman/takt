from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Kleurenpaletten (Workflowy-stijl)
#
# Elk palet definieert dezelfde set rollen. De GUI en de item-delegate lezen
# de actieve set uit ``CURRENT`` zodat een paletwissel alles meekleurt.
# ---------------------------------------------------------------------------

PALETTES: dict[str, dict] = {
    "Licht": {
        "dark": False,
        "window": "#ffffff", "base": "#ffffff", "alt": "#f3f3f3",
        "text": "#2b2b2b", "text_dim": "#999999", "border": "#d4d4d4",
        "accent": "#2a82da", "accent_text": "#ffffff",
        "bullet": "#b3b3b3", "todo": "#2e8b57", "done": "#aaaaaa",
        "hover": "#eef3f8",
    },
    "Donker": {
        "dark": True,
        "window": "#1e1e1e", "base": "#2a2a2a", "alt": "#323232",
        "text": "#dcdcdc", "text_dim": "#888888", "border": "#444444",
        "accent": "#2a82da", "accent_text": "#ffffff",
        "bullet": "#888888", "todo": "#7ec88a", "done": "#888888",
        "hover": "#2a3a4a",
    },
    "Solarized": {
        "dark": False,
        "window": "#fdf6e3", "base": "#fdf6e3", "alt": "#eee8d5",
        "text": "#586e75", "text_dim": "#93a1a1", "border": "#ddd6c1",
        "accent": "#268bd2", "accent_text": "#ffffff",
        "bullet": "#93a1a1", "todo": "#859900", "done": "#93a1a1",
        "hover": "#eee8d5",
    },
    "Oceaan": {
        "dark": True,
        "window": "#0f2233", "base": "#12293d", "alt": "#173247",
        "text": "#cfe3f0", "text_dim": "#6f8ba0", "border": "#244a63",
        "accent": "#2b9fd6", "accent_text": "#ffffff",
        "bullet": "#6f8ba0", "todo": "#4fc3a1", "done": "#5f7a8c",
        "hover": "#163a52",
    },
    "Bos": {
        "dark": True,
        "window": "#14241a", "base": "#1a2e22", "alt": "#21392b",
        "text": "#d6e6d8", "text_dim": "#7a9483", "border": "#2f4a39",
        "accent": "#4caf6a", "accent_text": "#ffffff",
        "bullet": "#7a9483", "todo": "#9ccc65", "done": "#6d8574",
        "hover": "#21392b",
    },
    "Zonsondergang": {
        "dark": True,
        "window": "#241a20", "base": "#2e2128", "alt": "#392a32",
        "text": "#f0dfe0", "text_dim": "#a08b92", "border": "#4a2f3a",
        "accent": "#e0704f", "accent_text": "#ffffff",
        "bullet": "#a08b92", "todo": "#f0a35e", "done": "#8c6d76",
        "hover": "#392a32",
    },
}

PALETTE_NAMES = list(PALETTES.keys())
DEFAULT_PALETTE = "Donker"

# Actief palet — gelezen door de delegate tijdens het tekenen.
CURRENT: dict = PALETTES[DEFAULT_PALETTE]


def palette_from_settings(settings: dict) -> str:
    """Bepaal de paletnaam uit settings, met terugval op het oude thema-veld."""
    name = settings.get("palette")
    if name in PALETTES:
        return name
    # Migratie van het oude licht/donker-veld
    legacy = settings.get("theme")
    if legacy == "light":
        return "Licht"
    if legacy == "dark":
        return "Donker"
    return DEFAULT_PALETTE


def apply_font(app: QApplication, family: str, size: int) -> None:
    app.setFont(QFont(family, size))


def _build_palette(p: dict) -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(p["window"]))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(p["text"]))
    pal.setColor(QPalette.ColorRole.Base,            QColor(p["base"]))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(p["alt"]))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(p["alt"]))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(p["text"]))
    pal.setColor(QPalette.ColorRole.Text,            QColor(p["text"]))
    pal.setColor(QPalette.ColorRole.Button,          QColor(p["alt"]))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(p["text"]))
    pal.setColor(QPalette.ColorRole.BrightText,      QColor("#ff5050"))
    pal.setColor(QPalette.ColorRole.Link,            QColor(p["accent"]))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(p["accent"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(p["accent_text"]))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(p["text_dim"]))
    return pal


def _stylesheet(p: dict) -> str:
    if p["dark"]:
        done_bg, done_border, done_text = "#1a5a1a", "#2a8a2a", "#aaffaa"
    else:
        done_bg, done_border, done_text = "#d4edda", "#28a745", "#155724"
    return f"""
        QTreeWidget, QTreeView {{ border: 1px solid {p['border']}; background: {p['base']}; }}
        QTreeWidget::item {{ padding: 2px 0; }}
        QTreeWidget::item:selected {{ background: {p['accent']}; color: {p['accent_text']}; }}
        QTreeWidget::item:hover:!selected {{ background: {p['hover']}; }}
        QTreeWidget::branch {{ background: transparent; }}

        QScrollBar:vertical {{ width: 10px; background: {p['alt']}; }}
        QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 4px; min-height: 24px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

        QTabWidget::pane {{ border: 1px solid {p['border']}; top: -1px; }}
        QTabBar::tab {{
            background: {p['alt']}; color: {p['text_dim']};
            padding: 6px 18px; margin-right: 2px;
            border: 1px solid {p['border']}; border-bottom: none;
            border-top-left-radius: 5px; border-top-right-radius: 5px;
        }}
        QTabBar::tab:selected {{ background: {p['base']}; color: {p['text']}; }}
        QTabBar::tab:hover:!selected {{ color: {p['text']}; }}

        QFrame#todo-card {{
            border: 1px solid {p['border']}; border-radius: 6px;
            background: {p['alt']}; margin: 2px 4px;
        }}

        QPushButton {{
            border: 1px solid {p['border']}; border-radius: 4px;
            padding: 4px 12px; background: {p['alt']}; color: {p['text']};
        }}
        QPushButton:hover {{ background: {p['hover']}; }}
        QPushButton#done-btn {{
            background: {done_bg}; border-color: {done_border};
            color: {done_text}; font-weight: bold;
        }}
        QPushButton#menu-btn {{
            border: none; background: transparent; font-size: 16px;
            padding: 2px 10px; color: {p['text']};
        }}
        QPushButton#menu-btn:hover {{ background: {p['hover']}; border-radius: 4px; }}
        QPushButton#crumb {{
            border: none; background: transparent; padding: 2px 4px;
            color: {p['text_dim']};
        }}
        QPushButton#crumb:hover {{ color: {p['accent']}; text-decoration: underline; }}

        QComboBox {{ border: 1px solid {p['border']}; border-radius: 4px; padding: 3px 8px; background: {p['alt']}; color: {p['text']}; }}
        QLineEdit {{ border: 1px solid {p['border']}; border-radius: 4px; padding: 3px 6px; background: {p['base']}; color: {p['text']}; }}
    """


def apply_palette(app: QApplication, name: str) -> None:
    """Pas een palet (op naam) toe op de hele applicatie."""
    global CURRENT
    p = PALETTES.get(name) or PALETTES[DEFAULT_PALETTE]
    CURRENT = p
    app.setStyle("Fusion")
    app.setPalette(_build_palette(p))
    app.setStyleSheet(_stylesheet(p))
