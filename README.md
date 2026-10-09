# OKX 闪赚提醒器

这是一个 Windows 桌面提醒程序，用来监控 OKX 闪赚活动和 A 股可转债申购日历。

当前版本：**v0.1.1**

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
- 自动获取申购日当天可申购的 A 股可转债
- 在申购日 10:00、14:00 通过托盘、弹窗和邮件提醒
- 程序迟启动时自动补发；14:00 后首次启动只合并补发一条

## 运行

```powershell
pip install -r requirements.txt
python -m flash_earn_reminder.main
```

如果需要无黑窗口启动，可以使用 `run_windows.pyw` 或 `run_windows_silent.vbs`。

## 版本记录

- **v0.1.1**：窗口标题显示版本号；修复 Windows 打包时误收不兼容 ICU DLL 导致 QtCore 无法加载的问题。

## 说明

- 本地运行配置保存在 `data/` 下，不会提交到仓库。
- 打包产物由 `build_windows_exe.bat` 生成，输出到 `dist/`。
