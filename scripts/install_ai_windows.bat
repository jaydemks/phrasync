@echo off
setlocal
cd /d "%~dp0\.."
if not exist .venv\Scripts\activate.bat (
  echo Run install_windows.bat or install_core_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install -r requirements-ai.txt
pause
