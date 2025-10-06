@echo off
echo Starting Clipboard to Pieces Service...
echo ======================================

cd /d "%~dp0\.."

if not exist "logs" mkdir logs

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Checking dependencies...
python -c "import pieces_os_client, pyperclip, PIL, win32clipboard" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies
        echo Please check your internet connection and try again
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
    echo.
)

echo Starting robust clipboard service...
echo Service will monitor clipboard every 2 seconds
echo Press Ctrl+C to stop the service
echo.

cd src
python robust_clipboard_service.py

pause
