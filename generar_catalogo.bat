@echo off
chcp 65001 >nul
title FixPro — Generador de catalogo PDF

echo.
echo  Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python no esta instalado.
    echo  Instalalo desde: https://www.python.org/downloads/
    echo  IMPORTANTE: durante la instalacion, tilda "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo  Python OK
echo.
echo  Verificando librerias necesarias (Pillow, reportlab)...
python -m pip show pillow reportlab >nul 2>&1
if errorlevel 1 (
    echo  Instalando librerias necesarias, puede tardar un minuto...
    python -m pip install pillow reportlab
)

echo.
echo  Generando catalogo... esto puede tardar varios minutos
echo  (hay que procesar miles de fotos, no te asustes si tarda)
echo.

python "%~dp0catalogo_fixpro.py"

if errorlevel 1 (
    echo.
    echo  Algo salio mal. Avisame con una captura de pantalla.
    pause
)
