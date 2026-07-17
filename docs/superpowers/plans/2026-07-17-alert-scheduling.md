# Alert Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-time 25-hour pre-start email alert and make check timing and origin visible in the Windows UI.

**Architecture:** Keep all alert eligibility and de-duplication in `rules.py`. Keep wake-up calculation and UI log presentation in `ui.py`; propagate a string check source from the timer, startup callback, or manual action through the worker result handler.

**Tech Stack:** Python 3.11, PySide6, pytest, PyInstaller.

## Global Constraints

- Preserve existing alert timings and all email dispatch behavior.
- Use UTF-8 source and configuration serialization.
- Do not add polling; schedule only daily or activity-specific critical time points.

---

### Task 1: Pre-start 25-hour alert rule

**Files:**
- Modify: `flash_earn_reminder/models.py`
- Modify: `flash_earn_reminder/storage.py`
- Modify: `flash_earn_reminder/rules.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Produces `AppConfig.remind_pre_start_twenty_five_hours: bool` defaulting to `True`.
- Produces alert reason `starts_within_25h` once per campaign start date.

- [ ] **Step 1: Write the failing tests**

```python
def test_build_alerts_sends_once_during_twenty_fifth_hour_before_start() -> None:
    config = AppConfig()
    state = AppState(campaign_first_seen_times={"AI": "2026-07-16T09:00:00"})
    first = build_alerts([_campaign(name="AI", countdown_seconds=25 * 3600)], config, state, datetime(2026, 7, 17, 9))
    repeated = build_alerts([_campaign(name="AI", countdown_seconds=24 * 3600 + 59 * 60)], config, state, datetime(2026, 7, 17, 9, 1))
    assert [alert.reason for alert in first] == ["starts_within_25h"]
    assert repeated == []
```

- [ ] **Step 2: Run the focused test and confirm it fails for the missing rule.**

Run: `pytest tests/test_rules.py -q`

- [ ] **Step 3: Implement the configuration field, persistence, 25-hour rule, and message copy.**

```python
if config.remind_pre_start_twenty_five_hours and campaign.is_upcoming and 24 * 3600 < campaign.countdown_seconds <= 25 * 3600:
    return "starts_within_25h"
```

- [ ] **Step 4: Run the focused test and confirm it passes.**

Run: `pytest tests/test_rules.py -q`

### Task 2: Scheduler and log provenance

**Files:**
- Modify: `flash_earn_reminder/ui.py`
- Test: `tests/test_ui_behavior.py`

**Interfaces:**
- `next_monitor_run_time` schedules the exact `expected_start - timedelta(hours=25)` candidate when enabled.
- `check_now(source: str)` passes `startup`, `automatic`, or `manual` to the worker result handler.
- `format_log_entry(timestamp, message)` returns a full date/time prefix.

- [ ] **Step 1: Write failing tests for the 25-hour wake-up and dated/source-labelled log entry.**

```python
assert next_monitor_run_time(current, current, (8, 20), [campaign], AppConfig()) == datetime(2026, 7, 17, 10, 0)
assert format_log_entry(datetime(2026, 7, 17, 9, 0), "检查完成（自动）") == "[2026-07-17 09:00:00] 检查完成（自动）"
```

- [ ] **Step 2: Run the focused test and confirm it fails for the missing scheduler candidate and formatter.**

Run: `pytest tests/test_ui_behavior.py -q`

- [ ] **Step 3: Implement the scheduler candidate, configuration checkbox, and source propagation.**

```python
candidate = expected_start - timedelta(hours=25)
if config.remind_pre_start_twenty_five_hours and candidate > current:
    candidates.append(candidate)
```

- [ ] **Step 4: Run the focused test and confirm it passes.**

Run: `pytest tests/test_ui_behavior.py -q`

### Task 3: Full verification and Windows package

**Files:**
- Modify: generated `dist/OKXFlashEarnReminder/` output only

- [ ] **Step 1: Run the full test suite.**

Run: `pytest -q`

- [ ] **Step 2: Build the Windows package with the repository build command.**

Run: `powershell -ExecutionPolicy Bypass -File .\\build_windows.ps1`

- [ ] **Step 3: Confirm the rebuilt executable and `dist/OKXFlashEarnReminder/data` exist.**

Run: `Get-Item dist\\OKXFlashEarnReminder\\OKXFlashEarnReminder.exe`
