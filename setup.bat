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
pip install -r requirements.txt --disable-pip-version-check
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)
echo Dependencies installation completed successfully!

echo.
echo Checking Tesseract OCR installation...
tesseract --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Tesseract OCR not found. Running installation script...
    echo.
    
    REM Try PowerShell installation script
    powershell -ExecutionPolicy Bypass -File "install_tesseract.ps1"
    if %errorlevel% neq 0 (
        echo PowerShell installation failed. Please install manually:
        echo.
        echo Download from: https://github.com/UB-Mannheim/tesseract/wiki
        echo.
        echo Installation steps:
        echo 1. Download the Windows installer
        echo 2. Run the installer with default settings
        echo 3. Add Tesseract to PATH or set TESSDATA_PREFIX environment variable
        echo.
        echo After installation, restart this setup script.
        echo.
        pause
        exit /b 1
    )
    
    REM Refresh environment and test again
    echo Refreshing environment variables...
    call refreshenv >nul 2>&1
    
    REM Test if installation was successful
    tesseract --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo Installation completed but Tesseract not found in PATH.
        echo Please restart your terminal and run this script again.
        echo.
        pause
        exit /b 1
    )
)

echo Tesseract OCR found! Version:
tesseract --version

echo.
echo Creating necessary directories...
if not exist "logs" mkdir logs
if not exist "docs" mkdir docs

echo.
echo Setup complete! 
echo.
echo Starting clipboard service...
echo.
echo The service will now start monitoring your clipboard.
echo Press Ctrl+C to stop the service when needed.
echo.
echo ==================================
echo Service is starting...
echo ==================================
echo.

REM Start the clipboard service
python src\robust_clipboard_service.py
