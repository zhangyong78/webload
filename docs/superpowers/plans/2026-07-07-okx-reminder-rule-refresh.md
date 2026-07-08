# OKX Reminder Rule Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 OKX 页面即将开始卡片的倒计时解析，并把提醒规则改成首次发现、开始前 1 小时、开始后第 1 小时、进行中每日 08:00/14:00，保留开始前 24 小时提醒但默认关闭。

**Architecture:** 在 `okx_client.py` 放宽倒计时行识别，优先按可解析时间值提取倒计时；在 `rules.py` 按“事件类型”重写提醒匹配逻辑，并用 `AppState` 持久化首次发现时间与预计开始时间；在 `ui.py` 增加新的提醒开关并让下次检查时间同时考虑每日时段和活动关键节点。

**Tech Stack:** Python 3.11, PySide6, pytest, requests, BeautifulSoup

## Global Constraints

- 只修改与本次提醒规则和倒计时显示有关的代码。
- 继续保持 Windows 桌面程序形态，不引入新依赖。
- 新增行为必须先有失败测试，再补最小实现。
- `开始前 24 小时提醒` 保留但默认关闭。

---

### Task 1: 锁定解析与提醒规则

**Files:**
- Modify: `D:\mycode\webload\tests\test_okx_parser.py`
- Modify: `D:\mycode\webload\tests\test_rules.py`

**Interfaces:**
- Consumes: `parse_campaigns(html: str, *, source_url: str = DEFAULT_URL) -> list[Campaign]`
- Consumes: `build_alerts(campaigns: list[Campaign], config: AppConfig, state: AppState, now: datetime) -> list[AlertEvent]`
- Produces: 失败测试，覆盖 `活动即将开始` 倒计时解析、首次发现、开始前 1 小时、开始后第 1 小时、进行中每日提醒、24 小时默认关闭

### Task 2: 最小实现解析与状态

**Files:**
- Modify: `D:\mycode\webload\flash_earn_reminder\okx_client.py`
- Modify: `D:\mycode\webload\flash_earn_reminder\models.py`
- Modify: `D:\mycode\webload\flash_earn_reminder\storage.py`
- Modify: `D:\mycode\webload\flash_earn_reminder\rules.py`

**Interfaces:**
- Produces: `AppConfig` 新提醒开关字段
- Produces: `AppState` 新活动跟踪字段
- Produces: `build_alerts(...)` 新规则实现

### Task 3: 接入 UI 与调度

**Files:**
- Modify: `D:\mycode\webload\flash_earn_reminder\ui.py`
- Modify: `D:\mycode\webload\data\app_config.json`

**Interfaces:**
- Produces: 新提醒复选框
- Produces: 下一次检查时间同时考虑 `08:00/14:00` 和活动关键节点

### Task 4: 验证与打包

**Files:**
- No code changes required unless verification发现问题

**Interfaces:**
- Produces: 通过的测试、编译检查、可运行 exe
