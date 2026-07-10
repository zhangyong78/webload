# OKX 闪赚提醒器

这是一个 Windows 桌面程序，用来监控 OKX 闪赚页面，并在活动出现、即将开始或处于进行中时发送提醒邮件。

## 功能

- Windows 桌面界面，支持最小化到托盘
- 自动解析 OKX 页面中的活动信息和倒计时
- 支持提醒规则：
  - 首次发现立即提醒
  - 开始前 1 小时提醒
  - 开始后的第 1 小时提醒
  - 活动进行中每天 08:00 和 14:00 提醒
  - 可选的开始前 24 小时提醒
- 支持发送邮件提醒，正文为简洁中文内容

## 运行

```powershell
pip install -r requirements.txt
python -m flash_earn_reminder.main
```

如果需要无黑窗口启动，可以使用 `run_windows.pyw` 或 `run_windows_silent.vbs`。

## 说明

- 本地运行配置保存在 `data/` 下，不会提交到仓库。
- 打包产物由 `build_windows_exe.bat` 生成，输出到 `dist/`。
