# A 股可转债申购提醒 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic A-share convertible-bond subscription reminders at 10:00 and 14:00, including single-message catch-up after both slots are missed.

**Architecture:** Add a focused Eastmoney JSON client and isolated reminder-rule module. Extend the existing monitor result with generic notification events, then reuse the UI's tray, popup, email, persistence, and timer paths without changing OKX campaign behavior.

**Tech Stack:** Python 3.11+, requests, PySide6, dataclasses, pytest

## Global Constraints

- Fetch only the current local date's A-share convertible-bond subscriptions.
- Remind at 10:00 and 14:00; after 14:00, two missed slots become one combined catch-up reminder.
- One notification contains every bond available that day.
- Reuse currently enabled tray, popup, and email channels.
- Keep the existing OKX reminder behavior and existing JSON files backward compatible.
- Do not add listing-date, lottery-result, payment-date, or trading functionality.
- Do not add a new third-party dependency.

---

### Task 1: Eastmoney Convertible-Bond Client

**Files:**
- Create: `flash_earn_reminder/convertible_bond_client.py`
- Modify: `flash_earn_reminder/models.py`
- Create: `tests/test_convertible_bond_client.py`

**Interfaces:**
- Produces: `ConvertibleBondSubscription(name: str, bond_code: str, subscription_code: str, subscription_date: date)`
- Produces: `parse_convertible_bond_payload(payload: object, subscription_date: date) -> list[ConvertibleBondSubscription]`
- Produces: `fetch_convertible_bond_subscriptions(subscription_date: date, *, timeout: int = 20) -> list[ConvertibleBondSubscription]`

- [ ] **Step 1: Write failing parser tests**

```python
def test_parse_convertible_bond_payload_maps_valid_rows_and_skips_invalid_rows() -> None:
    payload = {
        "success": True,
        "result": {"data": [
            {"SECURITY_NAME_ABBR": "派克转债", "SECURITY_CODE": "111026", "CORRECODE": "713123", "PUBLIC_START_DATE": "2026-08-06 00:00:00"},
            {"SECURITY_NAME_ABBR": "缺代码", "SECURITY_CODE": "", "CORRECODE": "", "PUBLIC_START_DATE": "2026-08-06 00:00:00"},
            {"SECURITY_NAME_ABBR": "其他日期", "SECURITY_CODE": "123999", "CORRECODE": "370000", "PUBLIC_START_DATE": "2026-08-07 00:00:00"},
        ]},
    }
    result = parse_convertible_bond_payload(payload, date(2026, 8, 6))
    assert result == [ConvertibleBondSubscription("派克转债", "111026", "713123", date(2026, 8, 6))]

@pytest.mark.parametrize("payload", [{}, {"success": False}, {"success": True, "result": None}])
def test_parse_convertible_bond_payload_rejects_invalid_envelopes(payload: object) -> None:
    with pytest.raises(ValueError):
        parse_convertible_bond_payload(payload, date(2026, 8, 6))
```

- [ ] **Step 2: Run parser tests and verify they fail**

Run: `pytest tests/test_convertible_bond_client.py -v`
Expected: FAIL because the client module and model do not exist.

- [ ] **Step 3: Implement the model and strict payload parser**

```python
@dataclass(slots=True, frozen=True)
class ConvertibleBondSubscription:
    name: str
    bond_code: str
    subscription_code: str
    subscription_date: date
```

Parse `%Y-%m-%d` from the first ten characters of `PUBLIC_START_DATE`, retain only the requested date, require all three text fields, log a `logging.warning` diagnostic for each malformed row, and sort by `bond_code` for deterministic messages.

- [ ] **Step 4: Write and run a failing fetch test**

```python
def test_fetch_convertible_bond_subscriptions_uses_date_filter(monkeypatch) -> None:
    response = FakeResponse({"success": True, "result": {"data": []}})
    monkeypatch.setattr(client.requests, "get", lambda url, **kwargs: capture(url, kwargs, response))
    assert fetch_convertible_bond_subscriptions(date(2026, 8, 6), timeout=7) == []
    assert captured["params"]["reportName"] == "RPT_BOND_CB_LIST"
    assert captured["params"]["filter"] == "(PUBLIC_START_DATE='2026-08-06')"
    assert captured["timeout"] == 7
```

Run: `pytest tests/test_convertible_bond_client.py::test_fetch_convertible_bond_subscriptions_uses_date_filter -v`
Expected: FAIL because the fetch function does not exist.

- [ ] **Step 5: Implement the fetch function and pass client tests**

Use `requests.get("https://datacenter-web.eastmoney.com/api/data/v1/get", params=..., timeout=timeout)`, request only `SECURITY_CODE,SECURITY_NAME_ABBR,PUBLIC_START_DATE,CORRECODE`, call `raise_for_status()`, then parse `response.json()`.

Run: `pytest tests/test_convertible_bond_client.py -v`
Expected: PASS.

- [ ] **Step 6: Commit the client slice**

```powershell
git add flash_earn_reminder/models.py flash_earn_reminder/convertible_bond_client.py tests/test_convertible_bond_client.py
git commit -m "feat: fetch convertible bond subscriptions"
```

### Task 2: Reminder Rules and Persistent Deduplication

**Files:**
- Modify: `flash_earn_reminder/models.py`
- Create: `flash_earn_reminder/convertible_bond_rules.py`
- Modify: `flash_earn_reminder/storage.py`
- Create: `tests/test_convertible_bond_rules.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: `ConvertibleBondSubscription`
- Produces: `NotificationEvent(title: str, message: str)`
- Produces: `build_convertible_bond_notification(subscriptions: list[ConvertibleBondSubscription], state: AppState, now: datetime) -> NotificationEvent | None`
- Produces: `AppState.convertible_bond_alert_slots: dict[str, list[int]]`

- [ ] **Step 1: Write failing rule tests for normal slots, catch-up, and aggregation**

```python
def test_ten_o_clock_alert_marks_only_ten_slot() -> None:
    state = AppState()
    event = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 10, 0))
    assert event is not None
    assert state.convertible_bond_alert_slots == {"2026-08-06": [10]}

def test_after_fourteen_combines_two_missed_slots_into_one_alert() -> None:
    state = AppState()
    event = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 15, 0))
    assert event is not None
    assert "补发" in event.message
    assert state.convertible_bond_alert_slots == {"2026-08-06": [10, 14]}

def test_notification_lists_all_bonds_once() -> None:
    event = build_convertible_bond_notification(BONDS, AppState(), datetime(2026, 8, 6, 10, 0))
    assert event.message.count("派克转债") == 1
    assert event.message.count("先锋转债") == 1

def test_empty_list_and_duplicate_slot_do_not_alert() -> None:
    state = AppState(convertible_bond_alert_slots={"2026-08-06": [10]})
    assert build_convertible_bond_notification([], state, datetime(2026, 8, 6, 10, 30)) is None
    assert build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 10, 30)) is None
```

- [ ] **Step 2: Run rules tests and verify they fail**

Run: `pytest tests/test_convertible_bond_rules.py -v`
Expected: FAIL because the rule module, notification model, and state field do not exist.

- [ ] **Step 3: Implement minimal slot selection and message construction**

Slot behavior:

```python
if now.hour < 10:
    return None
pending = [slot for slot in (10, 14) if slot <= now.hour and slot not in completed]
if not pending:
    return None
completed.update(pending)
```

For `now.hour >= 14` with both slots pending, create one event containing “补发” and mark both slots. Format each bond as `名称｜转债代码：...｜申购代码：...｜申购日期：YYYY-MM-DD`.

- [ ] **Step 4: Add failing storage compatibility tests**

```python
def test_convertible_bond_slots_persist(tmp_path) -> None:
    path = tmp_path / "state.json"
    save_app_state(path, AppState(convertible_bond_alert_slots={"2026-08-06": [10, 14]}))
    assert load_app_state(path).convertible_bond_alert_slots == {"2026-08-06": [10, 14]}

def test_old_state_defaults_convertible_bond_slots_to_empty(tmp_path) -> None:
    path = tmp_path / "state.json"
    path.write_text("{}", encoding="utf-8")
    assert load_app_state(path).convertible_bond_alert_slots == {}
```

Run: `pytest tests/test_config.py -v`
Expected: FAIL until `load_app_state` maps the new field.

- [ ] **Step 5: Implement persistence and pass focused tests**

Normalize loaded keys to strings and loaded slot values to unique integers limited to `10` and `14`; missing data becomes `{}`.

Run: `pytest tests/test_convertible_bond_rules.py tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 6: Commit the rules and persistence slice**

```powershell
git add flash_earn_reminder/models.py flash_earn_reminder/convertible_bond_rules.py flash_earn_reminder/storage.py tests/test_convertible_bond_rules.py tests/test_config.py
git commit -m "feat: add convertible bond reminder rules"
```

### Task 3: Monitor and Notification Integration

**Files:**
- Modify: `flash_earn_reminder/models.py`
- Modify: `flash_earn_reminder/monitor.py`
- Modify: `flash_earn_reminder/ui.py`
- Modify: `tests/test_monitor.py`
- Modify: `tests/test_ui_behavior.py`

**Interfaces:**
- Consumes: `fetch_convertible_bond_subscriptions(date)`, `build_convertible_bond_notification(...)`
- Extends: `MonitorCycleResult.notifications: list[NotificationEvent]`, `convertible_bond_error: str`
- Produces: `MainWindow._dispatch_notification(title: str, message: str, email_subject: str, email_body: str) -> None`

- [ ] **Step 1: Write failing monitor tests proving independent source behavior**

```python
def test_monitor_cycle_builds_bond_notification() -> None:
    result = run_monitor_cycle(
        AppConfig(), AppState(), fetcher=lambda _: [],
        convertible_bond_fetcher=lambda _: BONDS,
        now=datetime(2026, 8, 6, 10, 0),
    )
    assert len(result.notifications) == 1

def test_bond_fetch_still_runs_when_okx_fetch_fails() -> None:
    result = run_monitor_cycle(
        AppConfig(), AppState(), fetcher=raising_okx_fetcher,
        convertible_bond_fetcher=lambda _: BONDS,
        now=datetime(2026, 8, 6, 10, 0),
    )
    assert result.error
    assert len(result.notifications) == 1

def test_bond_fetch_failure_does_not_mark_slots() -> None:
    state = AppState()
    result = run_monitor_cycle(
        AppConfig(), state, fetcher=lambda _: [],
        convertible_bond_fetcher=raising_bond_fetcher,
        now=datetime(2026, 8, 6, 10, 0),
    )
    assert result.convertible_bond_error
    assert state.convertible_bond_alert_slots == {}
```

- [ ] **Step 2: Run monitor tests and verify they fail**

Run: `pytest tests/test_monitor.py -v`
Expected: FAIL because the monitor does not accept or expose convertible-bond results.

- [ ] **Step 3: Extend the monitor without early-return coupling**

Capture `current_time` once. Fetch OKX and convertible bonds in separate `try/except` blocks, preserving both error strings. Always build the convertible-bond notification only after a successful bond fetch.

- [ ] **Step 4: Write failing UI tests for schedule and generic dispatch**

```python
def test_next_monitor_run_time_includes_convertible_bond_slots() -> None:
    assert next_monitor_run_time(datetime(2026, 8, 6, 9, 0), datetime(2026, 8, 6, 9, 0), (8, 20), [], AppConfig()) == datetime(2026, 8, 6, 10, 0)

def test_dispatch_notification_starts_email_before_popup(monkeypatch) -> None:
    MainWindow._dispatch_notification(fake_window, "标题", "正文", "邮件标题", "邮件正文")
    assert events == ["thread_created", "thread_started", "popup_shown"]
```

Run: `pytest tests/test_ui_behavior.py -v`
Expected: FAIL because the 10:00/14:00 schedule and generic dispatcher do not exist.

- [ ] **Step 5: Reuse notification channels and schedule both daily slots**

Initialize scheduling candidates with both existing daily hours and `next_scheduled_run_time(current, (10, 14))`. Make `_dispatch_alert` adapt the OKX alert through `_dispatch_notification`; dispatch `result.notifications` through the same method using title/message for email as well. Log convertible-bond errors separately and save state before dispatch as today.

- [ ] **Step 6: Pass monitor and UI tests**

Run: `pytest tests/test_monitor.py tests/test_ui_behavior.py -v`
Expected: PASS.

- [ ] **Step 7: Commit the integration slice**

```powershell
git add flash_earn_reminder/models.py flash_earn_reminder/monitor.py flash_earn_reminder/ui.py tests/test_monitor.py tests/test_ui_behavior.py
git commit -m "feat: deliver convertible bond reminders"
```

### Task 4: Documentation and End-to-End Verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Verifies all interfaces and constraints from Tasks 1-3.

- [ ] **Step 1: Update the user-facing feature list**

Add concise README bullets stating that the program fetches A-share convertible-bond subscriptions and reminds at 10:00/14:00 with automatic catch-up after late startup. Keep the run and package commands unchanged.

- [ ] **Step 2: Run the complete automated test suite**

Run: `pytest -q`
Expected: all tests PASS with no network access required by tests.

- [ ] **Step 3: Perform a live read-only data-source smoke test**

Run:

```powershell
python -c "from datetime import date; from flash_earn_reminder.convertible_bond_client import fetch_convertible_bond_subscriptions; print(fetch_convertible_bond_subscriptions(date(2026, 8, 6)))"
```

Expected: prints the current API response parsed as subscription models, or a clearly reported external network error without changing local state.

- [ ] **Step 4: Build the Windows executable**

Run: `cmd /c build_windows_exe.bat`
Expected: exit code 0 and `dist/OKXFlashEarnReminder.exe` exists.

- [ ] **Step 5: Inspect the final diff and repository state**

Run: `git diff --check` and `git status --short`
Expected: no whitespace errors; only the intended README change is uncommitted at this point.

- [ ] **Step 6: Commit documentation**

```powershell
git add README.md
git commit -m "docs: describe convertible bond reminders"
```

- [ ] **Step 7: Re-run final verification after the commit**

Run: `pytest -q` and confirm `git status --short` is empty.
Expected: all tests PASS and the working tree is clean.
