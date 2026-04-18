$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$py = "python"
if (Test-Path ".\.venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe" }

Write-Host "[build_release] python = $py"

& $py -m PyInstaller --noconfirm --clean --windowed --name AutoFill `
  --collect-all customtkinter `
  --hidden-import docxtpl --hidden-import docx --hidden-import pdfplumber `
  app\main.py

Write-Host "Done. Output: dist\AutoFill"

