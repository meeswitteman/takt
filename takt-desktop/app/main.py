import sys
from PyQt6.QtWidgets import QApplication
from app import config as cfg
from app import theme as theme_module
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Takt")

    settings = cfg.load()
    if settings.get("theme", "dark") == "dark":
        theme_module.apply_dark(app)
    else:
        theme_module.apply_light(app)
    theme_module.apply_font(app, settings.get("font_family", "Segoe UI"), settings.get("font_size", 10))

    window = MainWindow(app)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
