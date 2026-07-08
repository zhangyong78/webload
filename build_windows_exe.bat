@echo off
setlocal
cd /d %~dp0

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name OKXFlashEarnReminder ^
  run_windows.pyw

endlocal
