@echo off
REM cm2 installer for Windows - double-click this, or run it from cmd.exe.
REM Runs install.ps1 without needing to change the PowerShell execution policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
set EXITCODE=%ERRORLEVEL%
echo.
pause
exit /b %EXITCODE%
