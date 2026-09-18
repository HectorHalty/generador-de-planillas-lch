from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = (
    Path(sys._MEIPASS)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")
    else Path(__file__).resolve().parent
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
VENV = ROOT / ".lch-venv"
REQUIREMENTS = ROOT / "requirements.txt"
PORT = int(os.environ.get("LCH_PORT", "43147"))
URL = f"http://127.0.0.1:{PORT}"


def main() -> int:
    if not getattr(sys, "frozen", False):
        python = _ensure_venv()
        if Path(sys.executable).resolve() != python.resolve():
            return subprocess.call([str(python), str(ROOT / "lanzar.py"), *sys.argv[1:]])
        _ensure_imports()

    print()
    print("  Generador de Planillas LCH")
    print("  La Chacra Fútbol")
    print()
    print(f"  Abriendo {URL}")
    print("  Dejá esta ventana abierta mientras usás la app.")
    print("  Cerrala para apagar el programa.")
    print()

    threading.Thread(target=_open_browser, daemon=True).start()
    from lch_app.server import run

    run(host="127.0.0.1", port=PORT)
    return 0


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def _ensure_venv() -> Path:
    python = _venv_python()
    if not python.exists():
        print("Preparando el entorno la primera vez. Puede tardar un minuto…")
        subprocess.check_call([sys.executable, "-m", "venv", str(VENV)])
    return python


def _ensure_imports() -> None:
    try:
        import fastapi  # noqa: F401
        import pymupdf  # noqa: F401
        import uvicorn  # noqa: F401
        from rapidfuzz import fuzz  # noqa: F401
    except Exception:
        print("Instalando dependencias…")
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
        ])
        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(REQUIREMENTS),
        ])


def _open_browser() -> None:
    time.sleep(1.2)
    try:
        webbrowser.open(URL)
    except Exception:
        print(f"Abrí el navegador en {URL}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nListo, apagué el generador.")
        raise SystemExit(0)
