@echo off
echo Clipboard to Pieces - Setup Script
echo ==================================

cd /d "%~dp0"

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

echo Python found! Version:
python --version

echo.
echo Installing required dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "docs" mkdir docs

echo.
echo Setup complete! 
echo.
echo To start the service, run:
echo   scripts\start_clipboard_service.bat
echo.
echo Or run directly:
echo   python src\robust_clipboard_service.py
echo.
pause
