@echo off
REM 在项目根目录创建 .venv，并只安装 AutoFill 所需依赖（避免 Anaconda 全库导致 PyInstaller 卡死）
cd /d "%~dp0.."
where python >nul 2>&1
if errorlevel 1 (
  echo 未找到 python，请先安装 Python 3.11/3.12 并加入 PATH。
  exit /b 1
)
echo 创建虚拟环境: .venv
python -m venv .venv
if errorlevel 1 exit /b 1
call .venv\Scripts\activate.bat
python -m pip install -U pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
echo.
echo 完成。请在本目录执行: scripts\build_release.bat
echo （脚本会自动使用 .venv 里的 Python 调用 PyInstaller）
pause
