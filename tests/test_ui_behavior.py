from datetime import datetime
from types import SimpleNamespace

from flash_earn_reminder.models import AppConfig, Campaign
from flash_earn_reminder.models import AlertEvent, EmailConfig
from flash_earn_reminder.ui import (
    MainWindow,
    can_minimize_to_tray,
    format_log_entry,
    merge_default_recipients,
    next_monitor_run_time,
    next_scheduled_run_time,
    reuse_active_cached_campaigns,
)


def test_can_minimize_to_tray_requires_initial_presentation() -> None:
    assert can_minimize_to_tray(True, False) is False
    assert can_minimize_to_tray(True, True) is True
    assert can_minimize_to_tray(False, True) is False


def test_merge_default_recipients_keeps_imported_addresses() -> None:
    recipients = merge_default_recipients(("legacy@example.com", "conystar@126.com"))

    assert recipients == (
        "conystar@126.com",
        "187377363220@163.com",
        "1057902445@qq.com",
        "xhbyssy@163.com",
        "legacy@example.com",
    )


def test_next_scheduled_run_time_picks_same_day_evening_slot() -> None:
    current = datetime(2026, 7, 7, 9, 30, 0)

    result = next_scheduled_run_time(current, (8, 20))

    assert result == datetime(2026, 7, 7, 20, 0, 0)


def test_next_scheduled_run_time_rolls_to_next_day() -> None:
    current = datetime(2026, 7, 7, 20, 1, 0)

    result = next_scheduled_run_time(current, (8, 20))

    assert result == datetime(2026, 7, 8, 8, 0, 0)


def test_next_monitor_run_time_uses_next_hourly_pre_start_slot() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="即将上线",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="活动即将开始",
        countdown_text="03 日 00 时 00 分 00 秒",
        countdown_seconds=5 * 3600 + 30 * 60,
        is_ongoing=False,
        is_upcoming=True,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    result = next_monitor_run_time(current, current, (8, 20), [campaign], AppConfig())

    assert result == datetime(2026, 7, 7, 9, 30, 0)


def test_next_monitor_run_time_checks_twenty_five_hours_before_start() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="upcoming",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="starts",
        countdown_text="01 day 02 hours",
        countdown_seconds=26 * 3600,
        is_ongoing=False,
        is_upcoming=True,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    result = next_monitor_run_time(current, current, (8, 20), [campaign], AppConfig())

    assert result == datetime(2026, 7, 7, 10, 0, 0)


def test_next_monitor_run_time_checks_thirty_minutes_before_start() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="upcoming",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="starts",
        countdown_text="01 hour",
        countdown_seconds=3600,
        is_ongoing=False,
        is_upcoming=True,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    result = next_monitor_run_time(current, current, (8, 20), [campaign], AppConfig())

    assert result == datetime(2026, 7, 7, 9, 30, 0)


def test_reuse_active_cached_campaigns_keeps_and_updates_countdown_after_empty_response() -> None:
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="ongoing",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="ends",
        countdown_text="01 hour",
        countdown_seconds=3600,
        is_ongoing=True,
        is_upcoming=False,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    cached = reuse_active_cached_campaigns([campaign], elapsed_seconds=75)

    assert len(cached) == 1
    assert cached[0].countdown_seconds == 3525
    assert cached[0].countdown_text == "00 日 00 时 58 分 45 秒"


def test_format_log_entry_includes_date_and_check_source() -> None:
    result = format_log_entry(datetime(2026, 7, 17, 9, 0, 0), "检查完成（自动）")

    assert result == "[2026-07-17 09:00:00] 检查完成（自动）"


def test_next_monitor_run_time_falls_back_to_daily_slot_when_no_special_event() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)

    result = next_monitor_run_time(current, current, (8, 20), [], AppConfig())

    assert result == datetime(2026, 7, 7, 20, 0, 0)


def test_next_monitor_run_time_checks_daily_14_for_new_upcoming_campaigns() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="即将上线",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="活动即将开始",
        countdown_text="02 日 00 时 00 分 00 秒",
        countdown_seconds=2 * 86400,
        is_ongoing=False,
        is_upcoming=True,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    result = next_monitor_run_time(current, current, (8, 20), [campaign], AppConfig())

    assert result == datetime(2026, 7, 7, 14, 0, 0)


def test_next_monitor_run_time_checks_one_hour_before_ongoing_campaign_ends() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="进行中",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="结束倒计时",
        countdown_text="00 日 02 时 00 分 00 秒",
        countdown_seconds=2 * 3600,
        is_ongoing=True,
        is_upcoming=False,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    result = next_monitor_run_time(current, current, (8, 20), [campaign], AppConfig())

    assert result == datetime(2026, 7, 7, 10, 0, 0)


def test_next_monitor_run_time_checks_when_upcoming_campaign_starts_to_schedule_end_reminder() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)
    campaign = Campaign(
        campaign_id="AI",
        name="AI",
        status_text="即将上线",
        reward_text="8,000,000 AI",
        icon_url="",
        countdown_label="活动即将开始",
        countdown_text="00 日 30 分 00 秒",
        countdown_seconds=30 * 60,
        is_ongoing=False,
        is_upcoming=True,
        source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
    )

    result = next_monitor_run_time(current, current, (8, 20), [campaign], AppConfig())

    assert result == datetime(2026, 7, 7, 9, 30, 0)


def test_dispatch_alert_starts_email_before_popup(monkeypatch) -> None:
    events: list[str] = []

    class DummyThread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon
            events.append("thread_created")

        def start(self) -> None:
            events.append("thread_started")

    def fake_popup(*args, **kwargs) -> None:
        events.append("popup_shown")

    monkeypatch.setattr("flash_earn_reminder.ui.threading.Thread", DummyThread)
    monkeypatch.setattr("flash_earn_reminder.ui.QMessageBox.information", fake_popup)

    fake_window = SimpleNamespace(
        config=AppConfig(
            enable_email=True,
            enable_window_popup=True,
            enable_system_notification=False,
            email_config=EmailConfig(enabled=True),
        ),
        tray_icon=SimpleNamespace(isVisible=lambda: False, showMessage=lambda *args, **kwargs: None),
        _append_log=lambda message: None,
        _send_email_safe=lambda subject, body: None,
    )
    alert = AlertEvent(
        campaign=Campaign(
            campaign_id="AI",
            name="AI",
            status_text="即将上线",
            reward_text="8,000,000 AI",
            icon_url="",
            countdown_label="活动即将开始",
            countdown_text="00 日 01 时 00 分 00 秒",
            countdown_seconds=3600,
            is_ongoing=False,
            is_upcoming=True,
            source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn?from-page=trade",
            supported_assets=("BTC", "OKSOL", "OKB", "AI"),
        ),
        reason="starts_within_1h",
        title="okx 闪赚活动提醒",
        message="unused",
    )

    MainWindow._dispatch_alert(fake_window, alert)

    assert events == ["thread_created", "thread_started", "popup_shown"]
