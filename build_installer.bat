@echo off
setlocal
cd /d "%~dp0"

set "PY_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PY_CMD=py -3"

if not defined PY_CMD (
  where python >nul 2>nul
  if %errorlevel%==0 set "PY_CMD=python"
)

if not defined PY_CMD (
  echo Python was not found on this PC.
  pause
  exit /b 1
)

set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC_PATH%" set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if not exist "%ISCC_PATH%" (
  echo Inno Setup was not found.
  echo Install it, then run this file again.
  pause
  exit /b 1
)

%PY_CMD% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo Failed to install build dependencies.
  pause
  exit /b 1
)

if exist "dist\InputLab" rmdir /s /q "dist\InputLab"
if exist "dist\KeyHoldToggle" rmdir /s /q "dist\KeyHoldToggle"
if exist "build\InputLab" rmdir /s /q "build\InputLab"
if exist "build\KeyHoldToggle" rmdir /s /q "build\KeyHoldToggle"
if exist "InputLab.spec" del /q "InputLab.spec"
if exist "KeyHoldToggle.spec" del /q "KeyHoldToggle.spec"

%PY_CMD% -m PyInstaller --noconfirm --windowed --name InputLab --collect-binaries vgamepad --collect-data vgamepad app.py
if errorlevel 1 (
  echo Failed to build the application files.
  pause
  exit /b 1
)

"%ISCC_PATH%" installer.iss
if errorlevel 1 (
  echo Failed to build the installer.
  pause
  exit /b 1
)

echo Installer created in installer-dist\
pause
