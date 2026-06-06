@echo off
chcp 65001 >nul
title SD Image Sorter
cd /d "%~dp0"

echo ========================================
echo   SD Image Sorter
echo ========================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
    echo.
) else (
    echo [1/3] Virtual environment OK
)

echo [2/3] Installing dependencies...
echo This may take a few minutes, please wait...
echo.
.venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
.venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

echo [3/3] Checking model directories...
if not exist "models" mkdir models
if not exist "models\clip" mkdir models\clip
if not exist "models\aesthetic" mkdir models\aesthetic
if not exist "models\wd14" mkdir models\wd14
echo [OK] Model directories ready

echo.
echo ========================================
echo   Application Starting...
echo ========================================
echo.
echo Frontend: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo Server stopped
pause
