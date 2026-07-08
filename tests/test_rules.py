from datetime import datetime

from flash_earn_reminder.models import AppConfig, AppState, Campaign
from flash_earn_reminder.rules import build_alerts


def _campaign(
    *,
    name: str = "ROBO",
    status_text: str = "即将开始",
    is_ongoing: bool = False,
    countdown_label: str = "活动即将开始",
    countdown_text: str = "00 日 12 时 00 分 00 秒",
    countdown_seconds: int | None = 12 * 3600,
) -> Campaign:
    return Campaign(
        campaign_id=name,
        name=name,
        status_text=status_text,
        reward_text="20,000,000 ROBO",
        icon_url="",
        countdown_label=countdown_label,
        countdown_text=countdown_text,
        countdown_seconds=countdown_seconds,
        is_ongoing=is_ongoing,
        is_upcoming=is_ongoing is False,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )


def test_build_alerts_sends_first_seen_immediately_even_before_daily_slot() -> None:
    config = AppConfig(reminder_time_hours=(8, 14))
    state = AppState()

    alerts = build_alerts([_campaign(countdown_seconds=2 * 86400)], config, state, datetime(2026, 7, 7, 7, 59, 0))

    assert len(alerts) == 1
    assert alerts[0].reason == "first_seen"


def test_build_alerts_does_not_send_24h_upcoming_by_default() -> None:
    config = AppConfig(reminder_time_hours=(8, 14))
    state = AppState(campaign_first_seen_times={"AI": "2026-07-07T06:00:00"})

    alerts = build_alerts([_campaign(name="AI", countdown_seconds=12 * 3600)], config, state, datetime(2026, 7, 7, 11, 0, 0))

    assert alerts == []


def test_build_alerts_sends_one_hour_before_start_once() -> None:
    config = AppConfig(reminder_time_hours=(8, 14))
    state = AppState(campaign_first_seen_times={"AI": "2026-07-07T06:00:00"})

    first_alerts = build_alerts([_campaign(name="AI", countdown_seconds=3599)], config, state, datetime(2026, 7, 7, 11, 0, 0))
    second_alerts = build_alerts([_campaign(name="AI", countdown_seconds=3500)], config, state, datetime(2026, 7, 7, 11, 5, 0))

    assert len(first_alerts) == 1
    assert first_alerts[0].reason == "starts_within_1h"
    assert second_alerts == []


def test_build_alerts_sends_during_first_hour_after_start() -> None:
    config = AppConfig(reminder_time_hours=(8, 14))
    state = AppState(
        campaign_first_seen_times={"AI": "2026-07-07T06:00:00"},
        campaign_expected_start_times={"AI": "2026-07-07T14:00:00"},
    )

    alerts = build_alerts(
        [_campaign(name="AI", status_text="进行中", is_ongoing=True, countdown_label="结束倒计时", countdown_seconds=8 * 3600)],
        config,
        state,
        datetime(2026, 7, 7, 14, 20, 0),
    )

    assert len(alerts) == 1
    assert alerts[0].reason == "started_first_hour"


def test_build_alerts_waits_until_daily_schedule_for_late_ongoing_reminders() -> None:
    config = AppConfig(reminder_time_hours=(8, 14))
    state = AppState(
        campaign_first_seen_times={"ROBO": "2026-07-06T07:00:00"},
        campaign_expected_start_times={"ROBO": "2026-07-06T08:00:00"},
    )

    alerts = build_alerts(
        [_campaign(status_text="进行中", is_ongoing=True, countdown_label="结束倒计时", countdown_seconds=5 * 3600)],
        config,
        state,
        datetime(2026, 7, 7, 7, 59, 0),
    )

    assert alerts == []


def test_build_alerts_sends_ongoing_daily_at_8_and_14() -> None:
    config = AppConfig(reminder_time_hours=(8, 14))
    state = AppState(
        campaign_first_seen_times={"ROBO": "2026-07-06T07:00:00"},
        campaign_expected_start_times={"ROBO": "2026-07-06T08:00:00"},
    )

    morning_alerts = build_alerts(
        [_campaign(status_text="进行中", is_ongoing=True, countdown_label="结束倒计时", countdown_seconds=5 * 3600)],
        config,
        state,
        datetime(2026, 7, 7, 8, 0, 0),
    )
    afternoon_alerts = build_alerts(
        [_campaign(status_text="进行中", is_ongoing=True, countdown_label="结束倒计时", countdown_seconds=3 * 3600)],
        config,
        state,
        datetime(2026, 7, 7, 14, 0, 0),
    )

    assert len(morning_alerts) == 1
    assert morning_alerts[0].reason == "ongoing_daily"
    assert len(afternoon_alerts) == 1
    assert afternoon_alerts[0].reason == "ongoing_daily"


def test_build_alerts_can_optionally_send_24h_upcoming() -> None:
    config = AppConfig(reminder_time_hours=(8, 14), remind_upcoming=True)
    state = AppState(campaign_first_seen_times={"AI": "2026-07-07T06:00:00"})

    alerts = build_alerts([_campaign(name="AI", countdown_seconds=12 * 3600)], config, state, datetime(2026, 7, 7, 11, 0, 0))

    assert len(alerts) == 1
    assert alerts[0].reason == "starts_within_24h"
