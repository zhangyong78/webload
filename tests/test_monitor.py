from datetime import date, datetime

from flash_earn_reminder.models import AppConfig, AppState, Campaign, ConvertibleBondSubscription
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
        convertible_bond_fetcher=lambda _date: [],
        clock=lambda: current[0],
    )

    assert result.checked_at == datetime(2026, 7, 17, 20, 0, 1)
    assert [alert.reason for alert in result.alerts] == ["ongoing_daily"]


def _subscription() -> ConvertibleBondSubscription:
    return ConvertibleBondSubscription(
        name="派克转债",
        bond_code="111026",
        subscription_code="713123",
        subscription_date=date(2026, 8, 6),
    )


def test_monitor_cycle_builds_convertible_bond_notification() -> None:
    result = run_monitor_cycle(
        AppConfig(),
        AppState(),
        fetcher=lambda _url: [],
        convertible_bond_fetcher=lambda _date: [_subscription()],
        now=datetime(2026, 8, 6, 10, 0),
    )

    assert len(result.notifications) == 1
    assert result.notifications[0].title == "A 股可转债申购提醒"
    assert result.convertible_bond_error == ""


def test_monitor_cycle_reports_zero_convertible_bond_subscriptions() -> None:
    result = run_monitor_cycle(
        AppConfig(),
        AppState(),
        fetcher=lambda _url: [],
        convertible_bond_fetcher=lambda _date: [],
        now=datetime(2026, 8, 5, 14, 0),
    )

    assert result.convertible_bond_subscription_count == 0


def test_convertible_bond_fetch_still_runs_when_okx_fetch_fails() -> None:
    def raising_okx_fetcher(_url: str) -> list[Campaign]:
        raise RuntimeError("OKX unavailable")

    result = run_monitor_cycle(
        AppConfig(),
        AppState(),
        fetcher=raising_okx_fetcher,
        convertible_bond_fetcher=lambda _date: [_subscription()],
        now=datetime(2026, 8, 6, 10, 0),
    )

    assert result.error == "OKX unavailable"
    assert len(result.notifications) == 1


def test_convertible_bond_fetch_failure_does_not_mark_slots() -> None:
    state = AppState()

    def raising_bond_fetcher(_date: date) -> list[ConvertibleBondSubscription]:
        raise RuntimeError("bond source unavailable")

    result = run_monitor_cycle(
        AppConfig(),
        state,
        fetcher=lambda _url: [],
        convertible_bond_fetcher=raising_bond_fetcher,
        now=datetime(2026, 8, 6, 10, 0),
    )

    assert result.convertible_bond_error == "bond source unavailable"
    assert result.notifications == []
    assert state.convertible_bond_alert_slots == {}
