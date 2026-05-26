"""
Takt combined entry point.

When frozen as takt.exe:
  - Normal launch  → starts backend subprocess + Qt frontend
  - With --backend  → runs uvicorn only (called by the main process)
"""
import sys
import os

_BACKEND_FLAG = "--backend"


def _run_backend():
    import uvicorn
    uvicorn.run("takt_backend.main:app", host="127.0.0.1", port=8080, log_level="error")


def _wait_for_backend(timeout: float = 10.0):
    import time
    import httpx
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get("http://127.0.0.1:8080/api/v1/health", timeout=0.5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.15)
    return False


def _run_frontend():
    import subprocess
    from app import config as cfg

    settings = cfg.load()
    db_path = settings.get("db_path", "")

    env = os.environ.copy()
    if db_path:
        env["TAKT_DB_PATH"] = db_path

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    backend_proc = subprocess.Popen(
        [sys.executable, _BACKEND_FLAG],
        env=env,
        creationflags=creation_flags,
    )

    if not _wait_for_backend():
        from PyQt6.QtWidgets import QApplication, QMessageBox
        _app = QApplication(sys.argv)
        QMessageBox.critical(None, "Takt", "Backend kon niet starten.\nSluit de applicatie en probeer opnieuw.")
        backend_proc.terminate()
        sys.exit(1)

    from PyQt6.QtWidgets import QApplication
    from app import theme as theme_module
    from app.main_window import MainWindow

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("Takt")

    if settings.get("theme", "dark") == "dark":
        theme_module.apply_dark(qt_app)
    else:
        theme_module.apply_light(qt_app)
    theme_module.apply_font(
        qt_app,
        settings.get("font_family", "Segoe UI"),
        settings.get("font_size", 10),
    )

    window = MainWindow(qt_app)
    window.show()
    exit_code = qt_app.exec()

    backend_proc.terminate()
    sys.exit(exit_code)


if __name__ == "__main__":
    # Needed for PyInstaller multiprocessing support on Windows
    import multiprocessing
    multiprocessing.freeze_support()

    if _BACKEND_FLAG in sys.argv:
        _run_backend()
    else:
        _run_frontend()
