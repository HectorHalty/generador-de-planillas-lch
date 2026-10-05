@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Generador de Planillas LCH
echo.
echo   Generador de Planillas LCH
echo   La Chacra Futbol
echo.
where py >nul 2>&1 && (
  py -3 lanzar.py
  goto :done
)
where python >nul 2>&1 && (
  python lanzar.py
  goto :done
)
echo No encuentro Python 3. Intento instalarlo solo...
where winget >nul 2>&1 && (
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    "%LocalAppData%\Programs\Python\Python312\python.exe" lanzar.py
    goto :done
  )
)
echo.
echo No pude instalarlo solo. Hacelo a mano:
echo 1. Entra a https://www.python.org/downloads/
echo 2. Instala Python 3.12 o superior
echo 3. Tilda "Add python.exe to PATH"
echo 4. Volve a hacer doble clic en este archivo
echo.
pause
exit /b 1
:done
if errorlevel 1 (
  echo.
  echo Algo fallo. Revisa el mensaje de arriba.
  pause
)
