# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parent
cli_src = str(root / "takt-cli")

a = Analysis(
    [str(Path(SPECPATH) / "main.py")],
    pathex=[cli_src],
    binaries=[],
    datas=[],
    hiddenimports=[
        "takt",
        "takt.main",
        "takt.client",
        "takt.output",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt6"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="takt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,        # CLI: console venster nodig
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)