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
echo No encuentro Python 3.
echo.
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
