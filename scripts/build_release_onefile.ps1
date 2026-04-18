$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

$py = "python"
if (Test-Path ".\.venv\Scripts\python.exe") { $py = ".\.venv\Scripts\python.exe" }

Write-Host "[build_release_onefile] python = $py"

& $py -m PyInstaller --noconfirm --clean --windowed --onefile --name AutoFill `
  --collect-all customtkinter `
  --collect-all docxtpl `
  --hidden-import docxtpl --hidden-import docx --hidden-import pdfplumber `
  app\main.py

Write-Host "Done. Output: dist\AutoFill.exe"

