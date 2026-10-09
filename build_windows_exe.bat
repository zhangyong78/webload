@echo off
setlocal
cd /d %~dp0

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name OKXFlashEarnReminder ^
  run_windows.pyw

if errorlevel 1 exit /b %errorlevel%

del /Q "dist\OKXFlashEarnReminder\_internal\icuuc.dll" 2>nul
for %%F in ("dist\OKXFlashEarnReminder\_internal\icudt*.dll") do if exist "%%~F" del /Q "%%~F"

endlocal
