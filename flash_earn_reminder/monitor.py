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
) -> MonitorCycleResult:
    current_time = now or datetime.now()
    active_fetcher = fetcher or fetch_campaigns
    try:
        campaigns = active_fetcher(config.okx_url)
    except Exception as exc:
        return MonitorCycleResult(campaigns=[], alerts=[], checked_at=current_time, error=str(exc))
    alerts = build_alerts(campaigns, config, state, current_time)
    return MonitorCycleResult(campaigns=campaigns, alerts=alerts, checked_at=current_time)

