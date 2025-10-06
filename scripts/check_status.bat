@echo off
echo Clipboard to Pieces Service Status
echo ==================================

echo Checking for running Python processes...
tasklist /fi "imagename eq python.exe" 2>nul | find /i "python.exe" >nul
if %errorlevel% equ 0 (
    echo Status: Service is RUNNING
    echo.
    echo Running Python processes:
    tasklist /fi "imagename eq python.exe"
) else (
    echo Status: Service is NOT RUNNING
)

echo.
echo Recent log entries:
if exist "logs\robust_clipboard_service.log" (
    echo Last 10 log entries:
    powershell -Command "Get-Content 'logs\robust_clipboard_service.log' -Tail 10"
) else (
    echo No log file found
)

echo.
pause
