from __future__ import annotations

from datetime import datetime
from typing import Callable

from flash_earn_reminder.models import AppConfig, AppState, Campaign, MonitorCycleResult
from flash_earn_reminder.okx_client import fetch_campaigns
from flash_earn_reminder.rules import build_alerts


def run_monitor_cycle(
    config: AppConfig,
    state: AppState,
    *,
    fetcher: Callable[[str], list[Campaign]] | None = None,
    now: datetime | None = None,
    check_source: str = "自动",
    clock: Callable[[], datetime] | None = None,
) -> MonitorCycleResult:
    active_clock = clock or datetime.now
    active_fetcher = fetcher or fetch_campaigns
    try:
        campaigns = active_fetcher(config.okx_url)
    except Exception as exc:
        current_time = now or active_clock()
        return MonitorCycleResult(campaigns=[], alerts=[], checked_at=current_time, error=str(exc), check_source=check_source)
    current_time = now or active_clock()
    alerts = build_alerts(campaigns, config, state, current_time)
    return MonitorCycleResult(campaigns=campaigns, alerts=alerts, checked_at=current_time, check_source=check_source)
