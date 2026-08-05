# Collapsible Mail Settings and Manual Check Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Default the mail settings to a compact collapsed section, remove the qqokx path field from the UI, enlarge the log, and make manual OKX plus convertible-bond checks explicit in the log.

**Architecture:** Add one small reusable Qt collapsible section in `ui.py` and use it only for the mail form. Keep `qqokx_project_path` in persisted configuration but stop binding it to a visible field. Add the manual-check start message at the existing `check_now` boundary before its worker thread starts; the existing monitor result handler continues to report both result streams.

**Tech Stack:** Python 3.11, PySide6, pytest, PyInstaller

## Global Constraints

- Mail settings are collapsed on every application start.
- The visible qqokx project path row is removed; internal import fallback remains `D:\qqokx`.
- Manual checks continue to use the same `run_monitor_cycle` call as scheduled checks.
- Convertible-bond alert timing and deduplication behavior are unchanged.
- Changes stay limited to the UI and UI behavior tests.

---

### Task 1: Collapsible Mail Section and Larger Log

**Files:**
- Modify: `flash_earn_reminder/ui.py`
- Test: `tests/test_ui_behavior.py`

**Interfaces:**
- Produces: `CollapsibleSection(title: str, expanded: bool = False)` with `toggle_button`, `content`, and `content_layout`.
- Consumes: `MainWindow._build_mail_group()` and `MainWindow._build_log_group()`.

- [x] **Step 1: Write the failing UI behavior test**

```python
def test_mail_settings_start_collapsed_without_qqokx_path_and_log_has_room() -> None:
    app = QApplication.instance() or QApplication([])
    fake_window = SimpleNamespace()

    mail_section = MainWindow._build_mail_group(fake_window)
    log_group = MainWindow._build_log_group(fake_window)

    assert fake_window.mail_config_content.isHidden() is True
    assert all(label.text() != "qqokx 项目路径" for label in mail_section.findChildren(QLabel))
    assert fake_window.log_output.minimumHeight() >= 220

    fake_window.mail_config_toggle.click()
    assert fake_window.mail_config_content.isHidden() is False
    mail_section.deleteLater()
    log_group.deleteLater()
    app.processEvents()
```

- [x] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/test_ui_behavior.py::test_mail_settings_start_collapsed_without_qqokx_path_and_log_has_room -q`

Expected: FAIL because the current mail group is not collapsible, still renders the qqokx path row, and the log has no minimum height.

- [x] **Step 3: Implement the minimal collapsible section**

```python
class CollapsibleSection(QWidget):
    def __init__(self, title: str, *, expanded: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)
        self.toggle_button.toggled.connect(self.set_expanded)
        self.toggle_button.setChecked(expanded)
        self.set_expanded(expanded)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.content.setVisible(expanded)
```

Update `_build_mail_group` to store `mail_config_toggle` and `mail_config_content`, place only the SMTP fields into the content form, and default the section to collapsed. Remove all `qqokx_path_edit` reads and writes; `import_mail_config` reads `self.config.qqokx_project_path.strip() or r"D:\qqokx"`. Set `self.log_output.setMinimumHeight(220)`.

- [x] **Step 4: Run the focused test and verify GREEN**

Run: `python -m pytest tests/test_ui_behavior.py::test_mail_settings_start_collapsed_without_qqokx_path_and_log_has_room -q`

Expected: PASS.

---

### Task 2: Explicit Manual Check Start Log

**Files:**
- Modify: `flash_earn_reminder/ui.py`
- Test: `tests/test_ui_behavior.py`

**Interfaces:**
- Consumes: `MainWindow.check_now(source: str = "手动")`.
- Produces: one immediate manual-start log before the worker thread starts.

- [x] **Step 1: Write the failing manual-check behavior test**

```python
def test_manual_check_logs_okx_and_convertible_bond_before_worker_starts(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    class DummyThread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args

        def start(self) -> None:
            events.append(("thread", "started"))

    fake_window = SimpleNamespace(
        _running=True,
        _refreshing=False,
        running_label=SimpleNamespace(setText=lambda text: None),
        _append_log=lambda message: events.append(("log", message)),
        _run_cycle_worker=lambda source: None,
    )
    monkeypatch.setattr("flash_earn_reminder.ui.threading.Thread", DummyThread)

    MainWindow.check_now(fake_window, "手动")

    assert events == [
        ("log", "开始检查（手动）：正在检查 OKX 活动和 A 股可转债申购。"),
        ("thread", "started"),
    ]
```

- [x] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/test_ui_behavior.py::test_manual_check_logs_okx_and_convertible_bond_before_worker_starts -q`

Expected: FAIL because the worker currently starts without the requested log.

- [x] **Step 3: Add the minimal logging side effect**

```python
if source == "手动":
    self._append_log("开始检查（手动）：正在检查 OKX 活动和 A 股可转债申购。")
```

Place it after the existing pause/refresh guard and before creating the worker thread.

- [x] **Step 4: Run the focused test and verify GREEN**

Run: `python -m pytest tests/test_ui_behavior.py::test_manual_check_logs_okx_and_convertible_bond_before_worker_starts -q`

Expected: PASS.

---

### Task 3: Regression Verification and Windows Package

**Files:**
- Modify: `docs/superpowers/plans/2026-08-05-collapsible-mail-and-manual-check-log.md`

**Interfaces:**
- Consumes: the complete pytest suite and `build_windows_exe.bat`.
- Produces: a verified Windows executable in `dist/OKXFlashEarnReminder/OKXFlashEarnReminder.exe`.

- [x] **Step 1: Run the full test suite**

Run: `python -m pytest -q`

Expected: all tests pass with zero failures.

- [x] **Step 2: Check the scoped diff**

Run: `git diff --check` and `git status --short`.

Expected: only the plan, `flash_earn_reminder/ui.py`, and `tests/test_ui_behavior.py` are changed after the already committed design document.

- [x] **Step 3: Stop only the running packaged app that locks the target EXE**

Resolve the process by exact executable path `D:\mycode\webload\dist\OKXFlashEarnReminder\OKXFlashEarnReminder.exe`, then stop only matching processes.

- [x] **Step 4: Build and verify the package**

Run: `cmd /c build_windows_exe.bat`.

Expected: exit code 0 and a newly timestamped executable at `dist/OKXFlashEarnReminder/OKXFlashEarnReminder.exe`.

- [ ] **Step 5: Commit, push main, and relaunch the verified package**

```powershell
git add -- flash_earn_reminder/ui.py tests/test_ui_behavior.py docs/superpowers/plans/2026-08-05-collapsible-mail-and-manual-check-log.md
git commit -m "feat: collapse mail settings and clarify manual checks"
git -c http.proxy= -c https.proxy= push origin main
Start-Process -FilePath 'D:\mycode\webload\dist\OKXFlashEarnReminder\OKXFlashEarnReminder.exe'
```

Expected: local and remote `main` point to the same commit, the worktree is clean, and the new executable remains running.
