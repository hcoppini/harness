@echo off
title HARNESS // Building Standalone Executable...
cd /d "%~dp0"

echo [1/3] Running test suite...
"C:\Users\heito\AppData\Local\Microsoft\WindowsApps\python.exe" -m pytest tests/ -v
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Tests failed. Aborting build.
    pause
    exit /b %ERRORLEVEL%
)

echo [2/3] Compiling standalone Harness.exe with PyInstaller...
"C:\Users\heito\AppData\Local\Microsoft\WindowsApps\python.exe" -m PyInstaller --name "Harness" --onefile --windowed --noconsole --add-data "ui;ui" --clean -y main.py

if exist "dist\Harness.exe" (
    copy /y "dist\Harness.exe" "Harness.exe" >nul
    echo [3/3] Build complete! Standalone executable is ready at: Harness.exe
) else (
    echo [3/3] Build complete in dist\Harness.exe
)
pause
