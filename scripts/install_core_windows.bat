@echo off
setlocal
cd /d "%~dp0\.."
py -3.11 -m venv .venv 2>nul || py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip wheel
python -m pip install -r requirements.txt
pause
