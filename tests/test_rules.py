from datetime import datetime

from flash_earn_reminder.models import AppConfig, AppState, Campaign
from flash_earn_reminder.rules import build_alerts, toggle_campaign_mute


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


def test_build_alerts_skips_muted_campaigns() -> None:
    config = AppConfig()
    state = AppState(muted_campaign_ids=["AI"])

    alerts = build_alerts([_campaign(name="AI", countdown_seconds=2 * 3600)], config, state, datetime(2026, 7, 7, 11, 0, 0))

    assert alerts == []


def test_toggle_campaign_mute_closes_and_restores_a_campaign() -> None:
    state = AppState()

    assert toggle_campaign_mute(state, "AI") is True
    assert state.muted_campaign_ids == ["AI"]
    assert toggle_campaign_mute(state, "AI") is False
    assert state.muted_campaign_ids == []


def test_build_alerts_sends_each_hour_during_six_hours_before_start_once() -> None:
    config = AppConfig()
    state = AppState(campaign_first_seen_times={"AI": "2026-07-07T06:00:00"})

    first_alerts = build_alerts([_campaign(name="AI", countdown_seconds=6 * 3600)], config, state, datetime(2026, 7, 7, 8, 0, 0))
    repeated_alerts = build_alerts([_campaign(name="AI", countdown_seconds=6 * 3600 - 30)], config, state, datetime(2026, 7, 7, 8, 0, 30))
    next_hour_alerts = build_alerts([_campaign(name="AI", countdown_seconds=5 * 3600)], config, state, datetime(2026, 7, 7, 9, 0, 0))

    assert len(first_alerts) == 1
    assert first_alerts[0].reason == "starts_within_6h"
    assert repeated_alerts == []
    assert len(next_hour_alerts) == 1
    assert next_hour_alerts[0].reason == "starts_within_5h"


def test_build_alerts_sends_once_during_twenty_fifth_hour_before_start() -> None:
    config = AppConfig()
    state = AppState(campaign_first_seen_times={"AI": "2026-07-16T09:00:00"})

    first_alerts = build_alerts(
        [_campaign(name="AI", countdown_seconds=25 * 3600)],
        config,
        state,
        datetime(2026, 7, 17, 9, 0, 0),
    )
    repeated_alerts = build_alerts(
        [_campaign(name="AI", countdown_seconds=24 * 3600 + 59 * 60)],
        config,
        state,
        datetime(2026, 7, 17, 9, 1, 0),
    )

    assert [alert.reason for alert in first_alerts] == ["starts_within_25h"]
    assert repeated_alerts == []


def test_build_alerts_sends_once_thirty_minutes_before_start() -> None:
    config = AppConfig()
    state = AppState(campaign_first_seen_times={"AI": "2026-07-17T08:00:00"})

    first_alerts = build_alerts(
        [_campaign(name="AI", countdown_seconds=30 * 60)],
        config,
        state,
        datetime(2026, 7, 17, 9, 0, 0),
    )
    repeated_alerts = build_alerts(
        [_campaign(name="AI", countdown_seconds=29 * 60)],
        config,
        state,
        datetime(2026, 7, 17, 9, 1, 0),
    )

    assert [alert.reason for alert in first_alerts] == ["starts_within_30m"]
    assert repeated_alerts == []


def test_build_alerts_sends_new_upcoming_campaign_at_14_once_per_day() -> None:
    config = AppConfig()
    state = AppState(campaign_first_seen_times={"AI": "2026-07-09T10:00:00"})

    first_alerts = build_alerts([_campaign(name="AI", countdown_seconds=2 * 86400)], config, state, datetime(2026, 7, 10, 14, 0, 0))
    repeated_alerts = build_alerts([_campaign(name="AI", countdown_seconds=2 * 86400 - 60)], config, state, datetime(2026, 7, 10, 14, 1, 0))

    assert len(first_alerts) == 1
    assert first_alerts[0].reason == "new_task_daily"
    assert repeated_alerts == []


def test_build_alerts_sends_once_one_hour_before_ongoing_campaign_ends() -> None:
    config = AppConfig()
    state = AppState(campaign_first_seen_times={"AI": "2026-07-09T10:00:00"})
    campaign = _campaign(
        name="AI",
        status_text="进行中",
        is_ongoing=True,
        countdown_label="结束倒计时",
        countdown_seconds=3599,
    )

    first_alerts = build_alerts([campaign], config, state, datetime(2026, 7, 10, 10, 0, 0))
    repeated_alerts = build_alerts([campaign], config, state, datetime(2026, 7, 10, 10, 5, 0))

    assert len(first_alerts) == 1
    assert first_alerts[0].reason == "ends_within_1h"
    assert repeated_alerts == []


def test_build_alerts_keeps_daily_and_end_reminders_when_both_match() -> None:
    config = AppConfig(reminder_time_hours=(8, 20))
    state = AppState(campaign_first_seen_times={"AI": "2026-07-09T10:00:00"})
    campaign = _campaign(
        name="AI",
        status_text="进行中",
        is_ongoing=True,
        countdown_label="结束倒计时",
        countdown_seconds=3599,
    )

    alerts = build_alerts([campaign], config, state, datetime(2026, 7, 10, 20, 0, 1))

    assert {alert.reason for alert in alerts} == {"ends_within_1h", "ongoing_daily"}


def test_build_alerts_waits_until_daily_schedule_for_late_ongoing_reminders() -> None:
    config = AppConfig(reminder_time_hours=(8, 20))
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


def test_build_alerts_sends_ongoing_daily_at_8_and_20() -> None:
    config = AppConfig(reminder_time_hours=(8, 20))
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
        datetime(2026, 7, 7, 20, 0, 0),
    )

    assert len(morning_alerts) == 1
    assert morning_alerts[0].reason == "ongoing_daily"
    assert len(afternoon_alerts) == 1
    assert afternoon_alerts[0].reason == "ongoing_daily"
