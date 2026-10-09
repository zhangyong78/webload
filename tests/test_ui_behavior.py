from datetime import datetime
from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QLabel

from flash_earn_reminder.models import AppConfig, Campaign
from flash_earn_reminder.models import AlertEvent, EmailConfig
from flash_earn_reminder.ui import (
    AlertPopupController,
    MainWindow,
    can_minimize_to_tray,
    convertible_bond_check_log,
    format_log_entry,
    merge_default_recipients,
    next_monitor_run_time,
    next_scheduled_run_time,
    reuse_active_cached_campaigns,
    timer_interval_ms,
)


def test_can_minimize_to_tray_requires_initial_presentation() -> None:
    assert can_minimize_to_tray(True, False) is False
    assert can_minimize_to_tray(True, True) is True
    assert can_minimize_to_tray(False, True) is False


def test_merge_default_recipients_keeps_imported_addresses() -> None:
    recipients = merge_default_recipients(("legacy@example.com", "conystar@126.com"))

    assert recipients == (
        "conystar@126.com",
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


def test_convertible_bond_check_log_explicitly_reports_no_subscriptions() -> None:
    result = SimpleNamespace(
        check_source="启动",
        convertible_bond_error="",
        convertible_bond_subscription_count=0,
        notifications=[],
    )

    assert convertible_bond_check_log(result) == "可转债检查完成（启动）：今日无可申购转债。"


def test_mail_settings_start_collapsed_without_qqokx_path_and_log_has_room() -> None:
    app = QApplication.instance() or QApplication([])
    fake_window = SimpleNamespace()

    mail_section = MainWindow._build_mail_group(fake_window)
    log_group = MainWindow._build_log_group(fake_window)

    assert fake_window.mail_config_content.isHidden() is True
    assert all(label.text() != "qqokx 项目路径" for label in mail_section.findChildren(QLabel))
    assert fake_window.log_output.minimumHeight() >= 220

    fake_window.mail_config_toggle.click()
    assert fake_window.mail_config_content.isHidden() is False
    mail_section.deleteLater()
    log_group.deleteLater()
    app.processEvents()


def test_manual_check_logs_okx_and_convertible_bond_before_worker_starts(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    class DummyThread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args

        def start(self) -> None:
            events.append(("thread", "started"))

    fake_window = SimpleNamespace(
        _running=True,
        _refreshing=False,
        running_label=SimpleNamespace(setText=lambda text: None),
        _append_log=lambda message: events.append(("log", message)),
        _run_cycle_worker=lambda source: None,
    )
    monkeypatch.setattr("flash_earn_reminder.ui.threading.Thread", DummyThread)

    MainWindow.check_now(fake_window, "手动")

    assert events == [
        ("log", "开始检查（手动）：正在检查 OKX 活动和 A 股可转债申购。"),
        ("thread", "started"),
    ]


def test_timer_interval_rounds_up_to_avoid_early_timeout() -> None:
    current = datetime(2026, 7, 17, 19, 59, 58, 499100)
    target = datetime(2026, 7, 17, 20, 0, 0)

    assert timer_interval_ms(current, target) == 1501


def test_next_monitor_run_time_includes_ten_o_clock_convertible_bond_slot() -> None:
    current = datetime(2026, 7, 7, 9, 0, 0)

    result = next_monitor_run_time(current, current, (8, 20), [], AppConfig())

    assert result == datetime(2026, 7, 7, 10, 0, 0)


def test_next_monitor_run_time_includes_fourteen_o_clock_convertible_bond_slot() -> None:
    current = datetime(2026, 7, 7, 10, 30, 0)

    result = next_monitor_run_time(current, current, (8, 20), [], AppConfig())

    assert result == datetime(2026, 7, 7, 14, 0, 0)


def test_next_monitor_run_time_checks_daily_14_for_new_upcoming_campaigns() -> None:
    current = datetime(2026, 7, 7, 10, 30, 0)
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


def test_dispatch_notification_starts_email_before_popup(monkeypatch) -> None:
    events: list[str] = []

    class DummyThread:
        def __init__(self, *, target, args, daemon):
            self.target = target
            self.args = args
            self.daemon = daemon
            events.append("thread_created")

        def start(self) -> None:
            events.append("thread_started")

    class DummyPopupController:
        def show(self, title: str, message: str) -> None:
            events.append("popup_shown")

    monkeypatch.setattr("flash_earn_reminder.ui.threading.Thread", DummyThread)
    monkeypatch.setattr(
        "flash_earn_reminder.ui.QMessageBox.information",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("blocking popup must not be used")),
    )

    fake_window = SimpleNamespace(
        config=AppConfig(
            enable_email=True,
            enable_window_popup=True,
            enable_system_notification=False,
            email_config=EmailConfig(enabled=True),
        ),
        tray_icon=SimpleNamespace(isVisible=lambda: False, showMessage=lambda *args, **kwargs: None),
        _alert_popup_controller=DummyPopupController(),
        _append_log=lambda message: None,
        _send_email_safe=lambda subject, body: None,
    )
    MainWindow._dispatch_notification(
        fake_window,
        "A 股可转债申购提醒",
        "提醒正文",
        "A 股可转债申购提醒",
        "邮件正文",
    )

    assert events == ["thread_created", "thread_started", "popup_shown"]


def test_dispatch_alert_adapts_okx_email_to_generic_notification() -> None:
    captured: list[tuple[str, str, str, str]] = []
    fake_window = SimpleNamespace(
        _dispatch_notification=lambda title, message, email_subject, email_body: captured.append(
            (title, message, email_subject, email_body)
        )
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
            source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn",
        ),
        reason="starts_within_1h",
        title="OKX 提醒",
        message="活动即将开始",
    )

    MainWindow._dispatch_alert(fake_window, alert)

    assert captured[0][0:2] == ("OKX 提醒", "活动即将开始")
    assert captured[0][2] == "okx 闪赚活动提醒"
    assert "项目：AI" in captured[0][3]


def test_alert_popup_controller_reuses_one_non_modal_window() -> None:
    app = QApplication.instance() or QApplication([])
    controller = AlertPopupController(None)

    first_dialog = controller.show("提醒一", "第一条消息")
    second_dialog = controller.show("提醒二", "第二条消息")

    assert second_dialog is first_dialog
    assert second_dialog.isModal() is False
    assert second_dialog.text() == "第二条消息"
    assert second_dialog.informativeText() == "窗口未关闭期间累计 2 条提醒。"

    second_dialog.close()
    app.processEvents()
    third_dialog = controller.show("提醒三", "第三条消息")

    assert third_dialog is first_dialog
    assert third_dialog.informativeText() == "窗口未关闭期间累计 1 条提醒。"
    third_dialog.close()
