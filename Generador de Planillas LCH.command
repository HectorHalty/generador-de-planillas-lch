#!/bin/bash
cd "$(dirname "$0")"
chmod +x "$0" 2>/dev/null || true
exec bash "./generador-de-planillas-lch.sh"
