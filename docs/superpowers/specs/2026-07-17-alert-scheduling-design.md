# Alert Scheduling Design

## Goal

Make the Windows reminder's activity checks auditable and ensure every configured alert point sends email exactly once.

## Behavior

- Run logs show a full local date and time and label each check as startup, automatic, or manual.
- Existing alerts remain unchanged: first seen, the six hourly points before start, daily ongoing alerts, daily 14:00 upcoming alert, and one hour before end.
- Add one default-enabled alert for the 25th hour before an upcoming activity starts.
- The scheduler wakes at the 25-hour point and retains the existing hourly and daily wake-up points.
- Every emitted alert follows the existing independent email dispatch path when email alerts are enabled. Repeated checks in the same alert slot do not resend email.

## Error Handling

If a page check fails, the result is logged with its source. A manual or startup check may refresh activity data, but it cannot create duplicate emails for an alert state key already sent.

## Verification

Tests cover the 25-hour alert, its de-duplication, the 25-hour scheduler wake-up, and dated/source-labelled log formatting. The full test suite and Windows build must succeed.
