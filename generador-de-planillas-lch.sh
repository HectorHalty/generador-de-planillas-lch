#!/bin/bash
cd "$(dirname "$0")"
echo
echo "  Generador de Planillas LCH"
echo "  La Chacra Fútbol"
echo
if command -v python3 >/dev/null 2>&1; then
  exec python3 lanzar.py
fi
if command -v python >/dev/null 2>&1; then
  exec python lanzar.py
fi
echo "No encuentro Python 3."
echo "En macOS: instala Python desde https://www.python.org/downloads/"
echo "En Ubuntu: sudo apt install python3 python3-venv python3-pip"
read -r -p "Enter para salir "
exit 1
