@echo off
setlocal enabledelayedexpansion
title Configure Pomodoro Auto-Start on Windows Restart

:: Navigate to script directory
cd /d "%~dp0"

echo ========================================================
echo     POMODORO AUTO-START INSTALLER (Windows)
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
:: Remove trailing backslash if present
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "SILENT_LAUNCHER=%SCRIPT_DIR%\run_pomodoro_silent.vbs"
set "BAT_LAUNCHER=%SCRIPT_DIR%\run_pomodoro.bat"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

echo [*] Target Script Directory: "%SCRIPT_DIR%"
echo [*] Windows Startup Folder:  "%STARTUP_FOLDER%"
echo.

:: 1. Copy silent runner to Windows Startup Folder
if exist "%SILENT_LAUNCHER%" (
    echo [*] Creating Startup Folder entry using silent launcher...
    copy /y "%SILENT_LAUNCHER%" "%STARTUP_FOLDER%\PomodoroFocus.vbs" >nul
    if !errorlevel! equ 0 (
        echo [✓] Successfully placed PomodoroFocus.vbs in Startup folder.
    ) else (
        echo [!] Warning: Could not write to Startup folder, attempting Registry fallback.
    )
) else (
    echo [*] Placing run_pomodoro.bat in Startup folder...
    copy /y "%BAT_LAUNCHER%" "%STARTUP_FOLDER%\PomodoroFocus.bat" >nul
)

:: 2. Register Windows Run Registry Key as secondary fail-safe
echo [*] Registering Windows Run key in registry (HKCU)...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PomodoroFocus" /t REG_SZ /d "wscript.exe \"%SILENT_LAUNCHER%\"" /f >nul
if !errorlevel! equ 0 (
    echo [✓] Successfully registered auto-start key in HKCU CurrentVersion\Run.
) else (
    echo [!] Warning: Could not write registry key.
)

echo.
echo ========================================================
echo [SUCCESS] Pomodoro Focus Timer will now start automatically
echo whenever your Windows computer reboots or you sign in!
echo ========================================================
echo.
echo Settings Configured:
echo - Auto-run on restart: ENABLED
echo - Daily Early Continue / Skip Limit: 2 times per day
echo - Warning Timer: 2 minutes before break
echo - System Resource Monitoring: Active
echo - Network Latency Monitoring: Active
echo.
pause
endlocal
