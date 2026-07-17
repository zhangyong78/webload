# Daily Slot Timing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make scheduled reminders use request-completion time and allow independent reminder rules to fire together.

**Architecture:** `monitor.py` owns the post-fetch evaluation timestamp. `rules.py` produces all matching reasons and de-duplicates each reason independently. `ui.py` uses precise upward-rounded timer delays and logs the evaluation time for non-alert checks.

**Tech Stack:** Python 3.11, PySide6, pytest, PyInstaller.

## Global Constraints

- Keep daily reminder slots at 08:00 and 20:00.
- Do not add periodic polling.
- Preserve current configuration, state files, and email delivery behavior.

---

### Task 1: Evaluate after fetch completion

**Files:**
- Modify: `flash_earn_reminder/monitor.py`
- Test: `tests/test_monitor.py`

**Interfaces:**
- Add optional `clock: Callable[[], datetime]` to `run_monitor_cycle`.
- Set `checked_at` and call `build_alerts` with the clock value read after `fetcher` returns.

- [ ] **Step 1: Add a failing regression test.**

```python
def test_monitor_uses_fetch_completion_time_for_daily_rule():
    current = [datetime(2026, 7, 17, 19, 59, 58)]
    def fetcher(_url):
        current[0] = datetime(2026, 7, 17, 20, 0, 1)
        return [ongoing_campaign()]
    result = run_monitor_cycle(config, state, fetcher=fetcher, clock=lambda: current[0])
    assert result.checked_at == datetime(2026, 7, 17, 20, 0, 1)
    assert [alert.reason for alert in result.alerts] == ["ongoing_daily"]
```

- [ ] **Step 2: Run the test and confirm it fails because the timestamp is captured before fetch.**

Run: `pytest tests/test_monitor.py -q`

- [ ] **Step 3: Move live timestamp capture after the fetch and retain explicit `now` support.**

- [ ] **Step 4: Run the focused monitor test.**

Run: `pytest tests/test_monitor.py -q`

### Task 2: Independent rules and precise timer

**Files:**
- Modify: `flash_earn_reminder/rules.py`
- Modify: `flash_earn_reminder/ui.py`
- Test: `tests/test_rules.py`
- Test: `tests/test_ui_behavior.py`

**Interfaces:**
- Replace `_match_reason(...) -> str | None` with `_match_reasons(...) -> list[str]`.
- Add `timer_interval_ms(current: datetime, target: datetime) -> int` using `math.ceil`.

- [ ] **Step 1: Add failing tests for two simultaneous reasons and upward timer rounding.**

```python
assert {alert.reason for alert in alerts} == {"ends_within_1h", "ongoing_daily"}
assert timer_interval_ms(current, target) == 1501
```

- [ ] **Step 2: Run the focused tests and confirm the current single-reason and truncating behavior fails.**

Run: `pytest tests/test_rules.py tests/test_ui_behavior.py -q`

- [ ] **Step 3: Implement multi-reason emission, precise Qt timer configuration, and evaluation-time diagnostics.**

- [ ] **Step 4: Run the complete suite.**

Run: `pytest -q`

### Task 3: Package and publish

**Files:**
- Generated: `dist/OKXFlashEarnReminder/`

- [ ] **Step 1: Back up `dist/OKXFlashEarnReminder/data` and run `build_windows_exe.bat`.**
- [ ] **Step 2: Restore the saved data directory and verify the executable timestamp.**
- [ ] **Step 3: Commit the implementation, merge to `main`, run tests on `main`, and push `origin/main`.**
