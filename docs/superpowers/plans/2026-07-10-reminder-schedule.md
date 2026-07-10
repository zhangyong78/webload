# 活动提醒规则调整 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支持单活动关闭提醒，开始前六小时按小时提醒，开始后每天 08:00 和 20:00 提醒。

**Architecture:** `AppState` 保存被静音活动；`rules.py` 负责规则匹配和去重；`ui.py` 提供卡片入口并安排关键时点检查。现有邮件、弹窗、系统通知继续消费相同的 `AlertEvent`。

**Tech Stack:** Python 3, PySide6, pytest。

## Global Constraints

- 仅修改提醒规则、活动卡片和本地状态。
- 保留首次发现立即提醒；静音活动例外。
- 进行中时段固定为 08:00、20:00。

---

### Task 1: 状态与规则

**Files:**
- Modify: `flash_earn_reminder/models.py`
- Modify: `flash_earn_reminder/storage.py`
- Modify: `flash_earn_reminder/rules.py`
- Test: `tests/test_rules.py`

- [ ] 写失败测试：静音活动无提醒、开始前六小时每小时提醒、进行中 08:00/20:00 提醒。
- [ ] 运行相关测试，确认新行为当前失败。
- [ ] 增加静音活动状态，替换旧的 24 小时、1 小时、开始后首小时规则。
- [ ] 将指定的四个地址写为新配置的默认收件人。
- [ ] 运行规则测试，确认通过。

### Task 2: 调度与界面

**Files:**
- Modify: `flash_earn_reminder/ui.py`
- Test: `tests/test_ui_behavior.py`

- [ ] 写失败测试：调度器选择开始前六小时内的下一个整点；卡片可切换静音状态。
- [ ] 运行相关测试，确认新行为当前失败。
- [ ] 将每日时段改为 08:00/20:00；增加关闭和恢复提醒按钮；调度开始前六小时的整点与开始时刻。
- [ ] 运行界面行为测试，确认通过。

### Task 3: 回归验证

**Files:**
- Modify: `docs/superpowers/specs/2026-07-10-reminder-schedule-design.md`
- Modify: `docs/superpowers/plans/2026-07-10-reminder-schedule.md`

- [ ] 运行完整 `pytest` 套件。
- [ ] 构建 Windows 可执行文件并启动冒烟验证。
