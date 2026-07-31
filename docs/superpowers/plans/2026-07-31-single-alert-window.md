# Single Alert Window Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reuse one non-modal reminder dialog so unattended alerts never accumulate nested popup windows.

**Architecture:** `AlertPopupController` owns a single `QMessageBox` and updates it for every alert. `MainWindow._dispatch_alert` keeps email dispatch first, then delegates popup presentation to the controller.

**Tech Stack:** Python 3.11, PySide6, pytest, PyInstaller.

## Global Constraints

- Preserve email, system tray, and scheduler behavior.
- Preserve the existing window-popup configuration checkbox.
- Never create more than one reminder dialog per application instance.

---

### Task 1: Reusable non-modal popup

**Files:**
- Modify: `flash_earn_reminder/ui.py`
- Test: `tests/test_ui_behavior.py`

**Interfaces:**
- Add `AlertPopupController(parent: QWidget)`.
- Add `show(title: str, message: str) -> QMessageBox`.

- [ ] **Step 1: Add a failing test that calls `show` twice and asserts object identity, non-modal behavior, latest content, and count.**
- [ ] **Step 2: Run the focused test and confirm the controller is missing.**

Run: `pytest tests/test_ui_behavior.py -q`

- [ ] **Step 3: Implement the controller and use it from `MainWindow._dispatch_alert`.**
- [ ] **Step 4: Update the email-before-popup test to exercise the controller boundary.**
- [ ] **Step 5: Run the focused and complete test suites.**

Run: `pytest tests/test_ui_behavior.py -q`

Run: `pytest -q`

### Task 2: Package and publish

**Files:**
- Generated: `dist/OKXFlashEarnReminder/`

- [ ] **Step 1: Back up `dist/OKXFlashEarnReminder/data` and run `build_windows_exe.bat`.**
- [ ] **Step 2: Restore the saved data directory and verify the executable timestamp.**
- [ ] **Step 3: Commit, merge to `main`, test the merged result, and push `origin/main`.**
