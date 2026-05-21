@echo off
cd /d "%~dp0"

if not exist ".venv" (
  python -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --windowed --name KeyHoldToggle --collect-binaries vgamepad --collect-data vgamepad app.py
