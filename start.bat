@echo off
title AI Video Dubbing Studio Launcher
echo ===================================================
echo     AI Multi-Speaker Video Dubbing Studio
echo ===================================================
echo.

:: 1. Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not installed or not in PATH!
    echo Attempting to install Python 3.11 via winget...
    winget install Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements
    echo Please restart this start.bat file after installation completes.
    pause
    exit /b
)

:: 2. Check FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] FFmpeg is not found in PATH!
    echo Attempting to install FFmpeg via winget...
    winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
    echo.
    echo If winget just finished installing FFmpeg, please close this window
    echo and re-run start.bat so the newly added PATH environment variables take effect.
    pause
    exit /b
)

:: 3. Setup Virtual Environment
if not exist "venv" (
    echo [*] Creating virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv. Make sure Python is fully installed.
        pause
        exit /b
    )
)

:: 4. Activate Venv and Install Dependencies
call venv\Scripts\activate.bat
echo [*] Checking and installing dependencies from requirements.txt...
pip install -r requirements.txt

:: 5. Launch FastAPI Application
echo.
echo ===================================================
echo  Starting server at http://localhost:8000
echo ===================================================
start "" http://localhost:8000
python app.py

pause
