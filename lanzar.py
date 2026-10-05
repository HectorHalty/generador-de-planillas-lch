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
HOST = os.environ.get("LCH_HOST", "127.0.0.1")


def main() -> int:
    if not getattr(sys, "frozen", False):
        python = _ensure_venv()
        if Path(sys.prefix).resolve() != VENV.resolve():
            return subprocess.call([str(python), str(ROOT / "lanzar.py"), *sys.argv[1:]])
        _ensure_imports()

    port = _pick_port(PORT)
    url = f"http://127.0.0.1:{port}"
    print()
    print("  Generador de Planillas LCH")
    print("  La Chacra Fútbol")
    print()
    if port == PORT and _already_running(PORT):
        print("  El programa ya estaba abierto. Lo abro en el navegador.")
        _open_browser(url, delay=0)
        return 0
    print(f"  Abriendo {url}")
    print("  Dejá esta ventana abierta mientras usás la app.")
    print("  Cerrala para apagar el programa.")
    print()

    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    from lch_app.server import run

    run(host=HOST, port=port)
    return 0


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def _ensure_venv() -> Path:
    python = _venv_python()
    pip = python.parent / ("pip.exe" if os.name == "nt" else "pip")
    if not python.exists() or not pip.exists():
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


def _already_running(port: int) -> bool:
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1.5) as reply:
            return reply.status == 200
    except Exception:
        return False


def _pick_port(preferred: int) -> int:
    """El puerto de siempre; si lo usa otro programa, el primero libre más arriba."""
    import socket

    if _already_running(preferred):
        return preferred
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred


def _open_browser(url: str, delay: float = 1.2) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        print(f"Abrí el navegador en {url}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nListo, apagué el generador.")
        raise SystemExit(0)
