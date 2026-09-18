# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(root / "lanzar.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "lch_app" / "static"), "lch_app/static"),
        (str(root / "public"), "public"),
        (str(root / "processor"), "processor"),
    ],
    hiddenimports=[
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "fastapi",
        "pymupdf",
        "rapidfuzz",
        "pypdf",
        "lch_app",
        "lch_app.server",
        "processor",
        "processor.pipeline",
        "processor.stamp",
        "processor.dates",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GeneradorPlanillasLCH",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
