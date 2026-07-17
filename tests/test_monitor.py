from datetime import datetime

from flash_earn_reminder.models import AppConfig, AppState, Campaign
from flash_earn_reminder.monitor import run_monitor_cycle


def _ongoing_campaign() -> Campaign:
    return Campaign(
        campaign_id="SENT",
        name="SENT",
        status_text="进行中",
        reward_text="32,000,000 SENT",
        icon_url="",
        countdown_label="结束倒计时",
        countdown_text="09 日 18 时 59 分 00 秒",
        countdown_seconds=9 * 86400 + 18 * 3600 + 59 * 60,
        is_ongoing=True,
        is_upcoming=False,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )


def test_monitor_uses_fetch_completion_time_for_daily_rule() -> None:
    current = [datetime(2026, 7, 17, 19, 59, 58)]

    def fetcher(_url: str) -> list[Campaign]:
        current[0] = datetime(2026, 7, 17, 20, 0, 1)
        return [_ongoing_campaign()]

    state = AppState(campaign_first_seen_times={"SENT": "2026-07-17T18:17:35"})
    result = run_monitor_cycle(
        AppConfig(),
        state,
        fetcher=fetcher,
        clock=lambda: current[0],
    )

    assert result.checked_at == datetime(2026, 7, 17, 20, 0, 1)
    assert [alert.reason for alert in result.alerts] == ["ongoing_daily"]
