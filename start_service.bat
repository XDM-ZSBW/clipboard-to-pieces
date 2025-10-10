@echo off
echo Starting Clipboard-to-Pieces service...
echo.

REM Check if service is already running
tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq clipboard_service*" >nul 2>&1
if not errorlevel 1 (
    echo WARNING: Service may already be running
    echo Check Task Manager for python.exe processes
    echo.
)

REM Start the service
echo Starting service with 2-second check interval...
echo Press Ctrl+C to stop the service
echo.

python src/clipboard_service.py --interval 2 --log-level INFO

echo.
echo Service stopped.
pause
