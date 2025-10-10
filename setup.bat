@echo off
echo Setting up Clipboard-to-Pieces service...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found. Installing dependencies...
echo.

REM Install dependencies
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.

REM Create necessary directories
if not exist "logs" mkdir logs
if not exist ".pieces" mkdir .pieces

echo Directories created:
echo - logs/ (for service logs)
echo - .pieces/ (for backup files)
echo.

REM Test the service
echo Testing service components...
python src/clipboard_service.py --test --log-level INFO
if errorlevel 1 (
    echo WARNING: Service test failed, but installation completed
    echo You may need to install additional dependencies or check your system
) else (
    echo Service test passed!
)

echo.
echo Setup completed successfully!
echo.
echo To start the service, run: start_service.bat
echo To run manually: python src/clipboard_service.py
echo.
pause
