# OKX Flash Earn Reminder

Windows desktop app for monitoring the OKX Flash Earn page and sending reminders for Flash Earn campaigns.

## Features

- Windows tray application with visible UI
- Parses live campaign countdown data from the OKX page
- Reminder rules:
  - first seen immediately
  - 1 hour before start
  - first hour after start
  - daily at 08:00 and 14:00 while ongoing
  - optional 24-hour-before-start reminder
- Email alerts with simple Chinese summary content

## Run

```powershell
pip install -r requirements.txt
python -m flash_earn_reminder.main
```

双击 `run_windows.pyw` 或 `run_windows_silent.vbs` 可无黑窗启动。

## Notes

- Local runtime config is stored under `data/` and is intentionally not committed.
- Build outputs are generated under `dist/` by `build_windows_exe.bat`.
