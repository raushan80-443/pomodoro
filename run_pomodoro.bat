@echo off
setlocal enabledelayedexpansion
title Pomodoro Focus System - Cross-Platform Windows Launcher

:: Navigate to script directory
cd /d "%~dp0"

echo ========================================================
echo     POMODORO FOCUS SYSTEM (Windows Edition)
echo ========================================================
echo.

:: Detect Python executable
set "PYTHON_EXE="

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    echo [*] Using project virtual environment: .venv\Scripts\python.exe
) else if exist "%~dp0env\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0env\Scripts\python.exe"
    echo [*] Using project virtual environment: env\Scripts\python.exe
) else (
    where python >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
        echo [*] Using system Python
    ) else (
        where py >nul 2>nul
        if !errorlevel! equ 0 (
            set "PYTHON_EXE=py -3"
            echo [*] Using Python Launcher (py -3)
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python 3 was not found on your system!
    echo Please install Python 3 from https://www.python.org/ or the Microsoft Store.
    echo Ensure "Add Python to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

:: Ensure core requirements are present
echo [*] Checking dependencies...
"%PYTHON_EXE%" -c "import psutil, pymongo" >nul 2>nul
if !errorlevel! neq 0 (
    echo [*] Installing required packages (psutil, pymongo, etc.)...
    "%PYTHON_EXE%" -m pip install -r requirements.txt --quiet
)

:: Launch Pomodoro
echo [*] Starting Pomodoro Focus Timer with Live System Monitoring...
echo [*] Daily early continue / skip limit is set to 2 per day.
echo [*] 2-minute pre-break warning toast enabled.
echo.

"%PYTHON_EXE%" -m pomodoro

if !errorlevel! neq 0 (
    echo [*] Fallback execution via pomo.py...
    "%PYTHON_EXE%" pomo.py
)

endlocal
