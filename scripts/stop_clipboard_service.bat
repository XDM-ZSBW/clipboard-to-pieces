@echo off
echo Stopping Clipboard to Pieces Service...
echo ======================================

echo Stopping Python processes...
taskkill /f /im python.exe 2>nul

echo Checking for remaining processes...
tasklist /fi "imagename eq python.exe" 2>nul | find /i "python.exe" >nul
if %errorlevel% equ 0 (
    echo Warning: Some Python processes may still be running
    echo Please check Task Manager if needed
) else (
    echo All Python processes stopped successfully
)

echo.
echo Service stopped.
pause
