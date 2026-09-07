@echo off
title Universal Video Downloader
echo =======================================================
echo   Starting Universal Video Downloader Server
echo   (YouTube, Instagram, Facebook, and more)
echo =======================================================

cd /d "%~dp0"

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [INFO] Installing required dependencies...
    pip install -r requirements.txt
) ELSE (
    call venv\Scripts\activate.bat
)

echo [INFO] Starting web application on http://127.0.0.1:8000 ...
start "" http://127.0.0.1:8000
python app.py

pause
