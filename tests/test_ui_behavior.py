from datetime import datetime

from flash_earn_reminder.models import AppConfig, Campaign
from flash_earn_reminder.ui import can_minimize_to_tray, next_monitor_run_time, next_scheduled_run_time


def test_can_minimize_to_tray_requires_initial_presentation() -> None:
    assert can_minimize_to_tray(True, False) is False
    assert can_minimize_to_tray(True, True) is True
    assert can_minimize_to_tray(False, True) is False


def test_next_scheduled_run_time_picks_same_day_afternoon_slot() -> None:
    current = datetime(2026, 7, 7, 9, 30, 0)

    result = next_scheduled_run_time(current, (8, 14))

    assert result == datetime(2026, 7, 7, 14, 0, 0)


def test_next_scheduled_run_time_rolls_to_next_day() -> None:
    current = datetime(2026, 7, 7, 14, 1, 0)

    result = next_scheduled_run_time(current, (8, 14))

    assert result == datetime(2026, 7, 8, 8, 0, 0)


def test_next_monitor_run_time_prefers_one_hour_before_start_over_daily_slot() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="即将上线",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="活动即将开始",
        countdown_text="03 日 00 时 00 分 00 秒",
        countdown_seconds=3 * 3600,
        is_ongoing=False,
        is_upcoming=True,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    result = next_monitor_run_time(current, current, (8, 14), [campaign], AppConfig())

    assert result == datetime(2026, 7, 7, 11, 0, 0)


def test_next_monitor_run_time_falls_back_to_daily_slot_when_no_special_event() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)

    result = next_monitor_run_time(current, current, (8, 14), [], AppConfig())

    assert result == datetime(2026, 7, 7, 14, 0, 0)
