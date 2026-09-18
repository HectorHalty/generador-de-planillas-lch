from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def static_dir() -> Path:
    bundled = Path(__file__).resolve().parent / "static"
    if bundled.exists():
        return bundled
    return app_root() / "lch_app" / "static"


def public_dir() -> Path:
    return app_root() / "public"


def output_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = app_root()
    path = base / ".lch-output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_pdf_path() -> Path:
    return output_dir() / "planillas-cancha.pdf"
