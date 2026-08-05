from __future__ import annotations

from datetime import datetime

from flash_earn_reminder.models import (
    AppState,
    ConvertibleBondSubscription,
    NotificationEvent,
)


REMINDER_SLOTS = (10, 14)


def build_convertible_bond_notification(
    subscriptions: list[ConvertibleBondSubscription],
    state: AppState,
    now: datetime,
) -> NotificationEvent | None:
    today = now.date()
    todays_subscriptions = [item for item in subscriptions if item.subscription_date == today]
    if not todays_subscriptions or now.hour < REMINDER_SLOTS[0]:
        return None

    date_key = today.isoformat()
    completed = set(state.convertible_bond_alert_slots.get(date_key, []))
    pending = [slot for slot in REMINDER_SLOTS if slot <= now.hour and slot not in completed]
    if not pending:
        return None

    completed.update(pending)
    state.convertible_bond_alert_slots[date_key] = sorted(completed)
    timing = _build_timing_text(pending, now)
    rows = [
        (
            f"{item.name}｜转债代码：{item.bond_code}｜申购代码：{item.subscription_code}"
            f"｜申购日期：{item.subscription_date.isoformat()}"
        )
        for item in sorted(todays_subscriptions, key=lambda item: item.bond_code)
    ]
    return NotificationEvent(
        title="A 股可转债申购提醒",
        message="\n".join((timing, *rows)),
    )


def _build_timing_text(pending: list[int], now: datetime) -> str:
    if pending == [10, 14]:
        return "本次为合并补发 10:00 和 14:00 提醒。"
    slot = pending[0]
    if now.hour == slot and now.minute == 0:
        return f"现在是 {slot:02d}:00 申购提醒。"
    return f"本次为补发 {slot:02d}:00 申购提醒。"
