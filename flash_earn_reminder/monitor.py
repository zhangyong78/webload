from __future__ import annotations

from datetime import date, datetime
from typing import Callable

from flash_earn_reminder.convertible_bond_client import fetch_convertible_bond_subscriptions
from flash_earn_reminder.convertible_bond_rules import build_convertible_bond_notification
from flash_earn_reminder.models import (
    AppConfig,
    AppState,
    Campaign,
    ConvertibleBondSubscription,
    MonitorCycleResult,
)
from flash_earn_reminder.okx_client import fetch_campaigns
from flash_earn_reminder.rules import build_alerts


def run_monitor_cycle(
    config: AppConfig,
    state: AppState,
    *,
    fetcher: Callable[[str], list[Campaign]] | None = None,
    convertible_bond_fetcher: Callable[[date], list[ConvertibleBondSubscription]] | None = None,
    now: datetime | None = None,
    check_source: str = "自动",
    clock: Callable[[], datetime] | None = None,
) -> MonitorCycleResult:
    active_clock = clock or datetime.now
    active_fetcher = fetcher or fetch_campaigns
    active_convertible_bond_fetcher = convertible_bond_fetcher or fetch_convertible_bond_subscriptions
    campaigns: list[Campaign] = []
    error = ""
    try:
        campaigns = active_fetcher(config.okx_url)
    except Exception as exc:
        error = str(exc)

    fetch_time = now or active_clock()
    subscriptions: list[ConvertibleBondSubscription] = []
    convertible_bond_error = ""
    try:
        subscriptions = active_convertible_bond_fetcher(fetch_time.date())
    except Exception as exc:
        convertible_bond_error = str(exc)

    current_time = now or active_clock()
    alerts = build_alerts(campaigns, config, state, current_time)
    notifications = []
    if not convertible_bond_error:
        notification = build_convertible_bond_notification(subscriptions, state, current_time)
        if notification is not None:
            notifications.append(notification)
    return MonitorCycleResult(
        campaigns=campaigns,
        alerts=alerts,
        notifications=notifications,
        checked_at=current_time,
        error=error,
        convertible_bond_error=convertible_bond_error,
        check_source=check_source,
    )
