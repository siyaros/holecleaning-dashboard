@echo off
title CleanSight Data Explorer v3.3.0
echo.
echo ========================================
echo   CleanSight Data Explorer v3.3.0
echo   Multi-Well CUC Comparison Edition
echo ========================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Install requirements if needed
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

echo.
echo Starting dashboard...
echo.
python app.py

pause
