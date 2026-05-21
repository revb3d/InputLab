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
  echo Install Python 3 and make sure the Python launcher or python command is available.
  echo Then run this file again.
  pause
  exit /b 1
)

if not exist ".venv" (
  %PY_CMD% -m venv .venv
  if errorlevel 1 (
    echo Failed to create the virtual environment.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate the virtual environment.
  pause
  exit /b 1
)

python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install required packages.
  echo Check your internet connection and run this file again.
  pause
  exit /b 1
)

python app.py
if errorlevel 1 (
  echo The app closed with an error.
  pause
  exit /b 1
)
