@echo off
cd /d "%~dp0"

if not exist ".venv" (
  python -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
if exist "dist\InputLab" rmdir /s /q "dist\InputLab"
if exist "dist\KeyHoldToggle" rmdir /s /q "dist\KeyHoldToggle"
if exist "build\InputLab" rmdir /s /q "build\InputLab"
if exist "build\KeyHoldToggle" rmdir /s /q "build\KeyHoldToggle"
if exist "InputLab.spec" del /q "InputLab.spec"
if exist "KeyHoldToggle.spec" del /q "KeyHoldToggle.spec"
pyinstaller --noconfirm --windowed --name InputLab --icon InputLabLogo.ico --add-data "InputLabLogo.png;." --add-data "InputLabLogo.ico;." --collect-binaries vgamepad --collect-data vgamepad app.py
