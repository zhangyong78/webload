@echo off
setlocal
cd /d %~dp0

pyinstaller --noconfirm --clean --distpath dist OKXFlashEarnReminder_v0.1.6.spec

if errorlevel 1 exit /b %errorlevel%

endlocal
