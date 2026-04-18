@echo off
setlocal EnableExtensions

REM Build (onedir). Prefer .venv to avoid Anaconda/base issues.
cd /d "%~dp0.."

set "PYEXE=python"
if exist ".venv\Scripts\python.exe" set "PYEXE=.venv\Scripts\python.exe"

echo [build_release] python = %PYEXE%

"%PYEXE%" -m PyInstaller --noconfirm --clean --windowed --name AutoFill ^
  --collect-all customtkinter ^
  --hidden-import docxtpl --hidden-import docx --hidden-import pdfplumber ^
  app\main.py

if errorlevel 1 exit /b 1
echo Done. Output: dist\AutoFill
