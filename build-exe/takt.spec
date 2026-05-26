# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

root = Path(SPECPATH).parent
desktop_src = str(root / "takt-desktop")
backend_src  = str(root / "takt-backend")

a = Analysis(
    [str(Path(SPECPATH) / "main.py")],
    pathex=[desktop_src, backend_src],
    binaries=[],
    datas=[],
    hiddenimports=[
        # uvicorn internals not auto-detected
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.off",
        "uvicorn.lifespan.on",
        # SQLAlchemy dialect
        "sqlalchemy.dialects.sqlite",
        # pydantic-settings
        "pydantic_settings",
        # backend modules
        "takt_backend",
        "takt_backend.main",
        "takt_backend.config",
        "takt_backend.database",
        "takt_backend.models",
        "takt_backend.models.item",
        "takt_backend.models.context",
        "takt_backend.models.variation",
        "takt_backend.routers.items",
        "takt_backend.routers.contexts",
        "takt_backend.routers.todos",
        "takt_backend.routers.variations",
        "takt_backend.services.item_service",
        "takt_backend.services.context_service",
        "takt_backend.services.todo_service",
        "takt_backend.services.variation_service",
        "takt_backend.schemas.item",
        "takt_backend.schemas.context",
        "takt_backend.schemas.variation",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["alembic", "tkinter"],
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
    name="Takt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # geen console venster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
