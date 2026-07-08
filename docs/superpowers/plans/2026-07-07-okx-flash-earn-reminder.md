# OKX Flash Earn Reminder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows desktop reminder app that monitors OKX Flash Earn campaigns and alerts on ongoing or upcoming campaigns within 24 hours.

**Architecture:** Use a small PySide6 shell over a pure-Python monitoring core. Parse the public OKX page with `requests + BeautifulSoup`, evaluate reminder rules with persisted cooldown state, and dispatch alerts through tray, popup, and SMTP email.

**Tech Stack:** Python 3.11, PySide6, requests, beautifulsoup4, pytest

## Global Constraints

- Windows desktop app with visible UI.
- Keep the implementation minimal and focused on this reminder workflow only.
- Prefer lightweight HTTP + HTML parsing over browser automation.
- Closing the main window minimizes to tray instead of exiting.
- Reminder frequency is configurable and defaults to every 8 hours.
- Mail config must be imported from the existing `D:\qqokx` mail configuration format.

---

### Task 1: Core Parser And Rules

**Files:**
- Create: `flash_earn_reminder/models.py`
- Create: `flash_earn_reminder/okx_client.py`
- Create: `flash_earn_reminder/rules.py`
- Test: `tests/test_okx_parser.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Produces: `parse_campaigns(html: str) -> list[Campaign]`
- Produces: `build_alerts(campaigns: list[Campaign], config: AppConfig, state: AppState, now: datetime) -> list[AlertEvent]`

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_campaign_extracts_ongoing_status():
    campaigns = parse_campaigns(SAMPLE_HTML)
    assert campaigns[0].name == "ROBO"
    assert campaigns[0].is_ongoing is True

def test_build_alerts_respects_cooldown():
    alerts = build_alerts([campaign], config, state, now)
    assert len(alerts) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_okx_parser.py tests/test_rules.py -v`
Expected: FAIL with import errors or missing functions.

- [ ] **Step 3: Write minimal implementation**

```python
def parse_campaigns(html: str) -> list[Campaign]:
    ...

def build_alerts(campaigns: list[Campaign], config: AppConfig, state: AppState, now: datetime) -> list[AlertEvent]:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_okx_parser.py tests/test_rules.py -v`
Expected: PASS

### Task 2: Config, State, And QQOKX Mail Import

**Files:**
- Create: `flash_earn_reminder/storage.py`
- Create: `flash_earn_reminder/emailing.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `load_app_config(path: Path) -> AppConfig`
- Produces: `save_app_config(path: Path, config: AppConfig) -> None`
- Produces: `email_config_from_snapshot(snapshot: Mapping[str, Any]) -> EmailConfig`
- Produces: `import_qqokx_email_config(project_root: Path) -> EmailConfig`

- [ ] **Step 1: Write the failing test**

```python
def test_email_config_from_snapshot_parses_recipients():
    config = email_config_from_snapshot(snapshot)
    assert config.recipient_emails == ("a@example.com", "b@example.com")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with import errors or missing functions.

- [ ] **Step 3: Write minimal implementation**

```python
def email_config_from_snapshot(snapshot: Mapping[str, Any]) -> EmailConfig:
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

### Task 3: Monitoring Cycle And Email Sending

**Files:**
- Create: `flash_earn_reminder/monitor.py`
- Extend: `flash_earn_reminder/emailing.py`

**Interfaces:**
- Consumes: `fetch_campaigns() -> list[Campaign]`
- Produces: `run_monitor_cycle(config: AppConfig, state: AppState) -> MonitorCycleResult`
- Produces: `send_email(subject: str, body: str, config: EmailConfig) -> None`

- [ ] **Step 1: Write the failing test**

```python
def test_run_monitor_cycle_emits_alerts_for_matching_campaigns():
    result = run_monitor_cycle(config, state, fetcher=lambda: [campaign], now=now)
    assert len(result.alerts) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL with missing `run_monitor_cycle`.

- [ ] **Step 3: Write minimal implementation**

```python
def run_monitor_cycle(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_rules.py -v`
Expected: PASS

### Task 4: PySide6 UI And Tray App

**Files:**
- Create: `flash_earn_reminder/ui.py`
- Create: `flash_earn_reminder/main.py`
- Create: `README.md`
- Create: `requirements.txt`
- Create: `pyproject.toml`

**Interfaces:**
- Produces: `run() -> int`

- [ ] **Step 1: Write the failing smoke check**

```python
python -m flash_earn_reminder.main
```

- [ ] **Step 2: Run it to verify missing-module or missing-symbol failure**

Run: `python -m flash_earn_reminder.main`
Expected: startup failure before UI exists.

- [ ] **Step 3: Write minimal implementation**

```python
def run() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()
```

- [ ] **Step 4: Run startup verification**

Run: `python -m flash_earn_reminder.main`
Expected: app window opens without traceback.

## Self-Review

- Spec coverage: parser, rules, config import, UI, tray behavior, and notifications are all mapped to tasks.
- Placeholder scan: no `TODO` or `TBD` markers remain.
- Type consistency: the same `Campaign`, `AppConfig`, `AppState`, and `EmailConfig` names are used across tasks.

