@echo off
setlocal EnableExtensions

REM Build (onefile). Slower startup, more AV false-positives.
cd /d "%~dp0.."

set "PYEXE=python"
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"

echo [build_release_onefile] python = %PYEXE%

"%PYEXE%" -m PyInstaller --noconfirm --clean --windowed --onefile --name AutoFill ^
  --collect-all customtkinter ^
  --collect-all docxtpl ^
  --hidden-import docxtpl --hidden-import docx --hidden-import pdfplumber ^
  app\main.py

if errorlevel 1 exit /b 1
echo Done. Output: dist\AutoFill.exe
