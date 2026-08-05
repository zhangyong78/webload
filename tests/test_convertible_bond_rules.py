from datetime import date, datetime

from flash_earn_reminder.convertible_bond_rules import build_convertible_bond_notification
from flash_earn_reminder.models import AppState, ConvertibleBondSubscription


BONDS = [
    ConvertibleBondSubscription("派克转债", "111026", "713123", date(2026, 8, 6)),
    ConvertibleBondSubscription("先锋转债", "118076", "718605", date(2026, 8, 6)),
]


def test_before_ten_does_not_alert_or_mark_a_slot() -> None:
    state = AppState()

    event = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 9, 59))

    assert event is None
    assert state.convertible_bond_alert_slots == {}


def test_ten_o_clock_alert_marks_only_ten_slot() -> None:
    state = AppState()

    event = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 10, 0))

    assert event is not None
    assert event.title == "A 股可转债申购提醒"
    assert "10:00" in event.message
    assert "补发" not in event.message
    assert state.convertible_bond_alert_slots == {"2026-08-06": [10]}


def test_after_ten_catches_up_ten_slot_once() -> None:
    state = AppState()

    first = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 10, 30))
    duplicate = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 13, 0))

    assert first is not None
    assert "补发 10:00" in first.message
    assert duplicate is None
    assert state.convertible_bond_alert_slots == {"2026-08-06": [10]}


def test_after_fourteen_combines_two_missed_slots_into_one_alert() -> None:
    state = AppState()

    event = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 15, 0))

    assert event is not None
    assert "合并补发 10:00 和 14:00" in event.message
    assert state.convertible_bond_alert_slots == {"2026-08-06": [10, 14]}
    assert build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 15, 1)) is None


def test_fourteen_slot_is_normal_when_ten_slot_was_completed() -> None:
    state = AppState(convertible_bond_alert_slots={"2026-08-06": [10]})

    event = build_convertible_bond_notification(BONDS, state, datetime(2026, 8, 6, 14, 0))

    assert event is not None
    assert "14:00" in event.message
    assert "补发" not in event.message
    assert state.convertible_bond_alert_slots == {"2026-08-06": [10, 14]}


def test_notification_lists_all_bonds_once() -> None:
    event = build_convertible_bond_notification(BONDS, AppState(), datetime(2026, 8, 6, 10, 0))

    assert event is not None
    assert event.message.count("派克转债") == 1
    assert event.message.count("先锋转债") == 1
    assert "转债代码：111026" in event.message
    assert "申购代码：713123" in event.message
    assert "申购日期：2026-08-06" in event.message


def test_empty_or_wrong_date_subscriptions_do_not_alert() -> None:
    state = AppState()
    wrong_date = [ConvertibleBondSubscription("次日转债", "123999", "370000", date(2026, 8, 7))]

    assert build_convertible_bond_notification([], state, datetime(2026, 8, 6, 10, 0)) is None
    assert build_convertible_bond_notification(wrong_date, state, datetime(2026, 8, 6, 10, 0)) is None
    assert state.convertible_bond_alert_slots == {}
