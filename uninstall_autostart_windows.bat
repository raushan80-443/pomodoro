@echo off
setlocal enabledelayedexpansion
title Uninstall Pomodoro Auto-Start from Windows Restart

echo ========================================================
echo     POMODORO AUTO-START UNINSTALLER (Windows)
echo ========================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"

:: 1. Remove files from Startup folder
if exist "%STARTUP_FOLDER%\PomodoroFocus.vbs" (
    del /f /q "%STARTUP_FOLDER%\PomodoroFocus.vbs" >nul 2>nul
    echo [✓] Removed PomodoroFocus.vbs from Startup folder.
)
if exist "%STARTUP_FOLDER%\PomodoroFocus.bat" (
    del /f /q "%STARTUP_FOLDER%\PomodoroFocus.bat" >nul 2>nul
    echo [✓] Removed PomodoroFocus.bat from Startup folder.
)
if exist "%STARTUP_FOLDER%\PomodoroFocus.lnk" (
    del /f /q "%STARTUP_FOLDER%\PomodoroFocus.lnk" >nul 2>nul
    echo [✓] Removed PomodoroFocus.lnk from Startup folder.
)

:: 2. Remove registry key
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "PomodoroFocus" /f >nul 2>nul
if !errorlevel! equ 0 (
    echo [✓] Removed PomodoroFocus registry key.
)

echo.
echo ========================================================
echo [SUCCESS] Auto-start on Windows reboot has been completely disabled.
echo You can still start Pomodoro manually anytime by running run_pomodoro.bat.
echo ========================================================
echo.
pause
endlocal
