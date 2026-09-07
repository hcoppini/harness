@echo off
setlocal enabledelayedexpansion
title HARNESS // Executive OS
cd /d "%~dp0"

echo ========================================================
echo   HARNESS // Executive OS Launcher
echo ========================================================

:: 1. If standalone Harness.exe exists, launch it directly
if exist "Harness.exe" (
    echo [OK] Found standalone Harness.exe. Launching...
    start "" "Harness.exe"
    exit /b 0
)

:: 2. Find working Python binary
set "PY_CMD="

py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=py"
    goto :FOUND_PYTHON
)

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=python"
    goto :FOUND_PYTHON
)

python3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PY_CMD=python3"
    goto :FOUND_PYTHON
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :FOUND_PYTHON
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :FOUND_PYTHON
)

echo [ERROR] No Python installation or Harness.exe found.
echo Please install Python (3.11 or 3.12) from python.org or place Harness.exe in this folder.
echo.
pause
exit /b 1

:FOUND_PYTHON
echo [OK] Using Python: %PY_CMD%

:: 3. Verify PyWebView is installed
%PY_CMD% -c "import webview" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installing required dependencies (pywebview)...
    %PY_CMD% -m pip install pywebview
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install pywebview. Please check your internet connection.
        pause
        exit /b 1
    )
)

:: 4. Launch Application
echo [OK] Starting Harness...
%PY_CMD% main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Harness exited with error code %ERRORLEVEL%.
    if exist "crash.log" (
        echo --- Crash Log Details ---
        type "crash.log"
    )
    pause
    exit /b %ERRORLEVEL%
)
