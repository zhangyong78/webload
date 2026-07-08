# OKX Flash Earn Reminder Design

## Goal

Build a Windows desktop app with a visible UI that monitors the OKX Flash Earn page and reminds the user when a campaign is `进行中` or starts within the next 24 hours. Reminders must support system notification, in-app popup, and email using the existing `D:\qqokx` mail configuration.

## Constraints

- Windows desktop app with visible UI.
- Keep the implementation minimal and focused on this reminder workflow only.
- Prefer lightweight HTTP + HTML parsing over browser automation.
- Closing the main window minimizes to tray instead of exiting.
- Reminder frequency is configurable and defaults to every 8 hours.
- Mail config must be imported from the existing `qqokx` project settings format.

## Architecture

The app is a small PySide6 desktop shell over a pure-Python monitoring core. The monitoring core fetches the OKX page, parses campaign cards, classifies campaigns into `ongoing` or `upcoming_within_24h`, applies reminder throttling, and produces alert events. The UI renders campaign cards, edits settings, and dispatches alerts through tray messages, modal popups, and email.

## Components

### Page Fetcher

- Request `https://www.okx.com/zh-hans/flash-earn/stake-to-earn?from-page=trade`
- Parse `.flash-earn-campaign-card` blocks
- Extract:
  - campaign name
  - status text
  - icon URL
  - reward text
  - countdown label
  - countdown text

### Rule Engine

- `ongoing` if the parsed status text matches running keywords such as `进行中` or `ongoing`
- `upcoming_within_24h` if the card has a start-oriented countdown and the countdown is `<= 24h`
- Apply reminder cooldown per campaign key using local persisted state

### Notification Layer

- Tray notification via `QSystemTrayIcon.showMessage`
- Window popup via `QMessageBox`
- Email via SMTP using imported `qqokx` settings

### Local Persistence

- Save app config in local JSON next to the project/exe
- Save reminder history in local JSON to keep cooldowns across restarts
- Import mail settings from the `qqokx` settings snapshot format

## UI

The main window has four areas:

1. Status bar with running state, last check time, next check time, and quick actions
2. Campaign card list showing the current Flash Earn campaigns
3. Reminder settings with poll interval, cooldown, and channel toggles
4. Mail settings with import-from-qqokx and send-test-email actions

Tray menu actions:

- Open window
- Check now
- Pause / Resume
- Exit

## Data Flow

1. UI starts a polling timer
2. Background worker fetches and parses the OKX page
3. Rule engine produces zero or more alert events
4. UI updates campaign cards and status labels
5. UI dispatches notifications and persists updated reminder state

## Error Handling

- Network or parsing failures update the status bar and log area without crashing the app
- Failed mail import shows a clear error dialog
- Failed email sends are logged and shown in the UI
- Missing tray support falls back to the visible window only

## Testing

- Parser test for ongoing campaign extraction
- Rule tests for upcoming-window detection and cooldown throttling
- Config test for `qqokx` mail snapshot parsing

