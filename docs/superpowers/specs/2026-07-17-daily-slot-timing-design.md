# Daily Slot Timing Design

## Goal

Prevent daily reminders from being skipped when an automatic page request starts just before a configured hour and finishes just after it.

## Root Cause

The monitor currently captures `datetime.now()` before fetching the OKX page. A request that starts at 19:59:58 and completes at 20:00:01 is therefore evaluated as 19:59, then the scheduler advances directly to the next daily slot.

## Design

- Evaluate alert rules using the time after the page fetch completes.
- Configure the Qt timer as a precise timer and round wait intervals upward so it does not intentionally truncate milliseconds before a target.
- Return every matching reminder reason for a campaign instead of only the first reason. Each reason keeps its own persisted de-duplication key.
- Log the exact rule evaluation time whenever a successful check finds campaigns but emits no alert.
- Keep daily reminders at 08:00 and 20:00. Do not add frequent polling or move reminders to minute 05.

## Verification

- Simulate a fetch that starts at 19:59:58 and completes at 20:00:01; it must emit `ongoing_daily`.
- Verify simultaneous `ongoing_daily` and `ends_within_1h` rules both emit once.
- Verify timer delay rounding never schedules earlier than the target.
- Run the complete test suite and rebuild the Windows package while preserving its `data` directory.
