from __future__ import annotations

from datetime import datetime, timedelta

from flash_earn_reminder.models import AlertEvent, AppConfig, AppState, Campaign


def build_alerts(
    campaigns: list[Campaign],
    config: AppConfig,
    state: AppState,
    now: datetime,
) -> list[AlertEvent]:
    alerts: list[AlertEvent] = []
    slot_hour = _current_slot_hour(now, config.reminder_time_hours)
    for campaign in campaigns:
        first_seen = _get_or_set_first_seen(state, campaign, now)
        expected_start_at = _update_expected_start_time(state, campaign, now)
        reason = _match_reason(campaign, config, now, first_seen, expected_start_at, slot_hour)
        if not reason:
            continue
        state_key = _build_state_key(campaign.campaign_id, reason, now, slot_hour, expected_start_at)
        if _parse_datetime(state.last_alert_times.get(state_key)) is not None:
            continue
        state.last_alert_times[state_key] = now.isoformat()
        alerts.append(
            AlertEvent(
                campaign=campaign,
                reason=reason,
                title=f"OKX Flash Earn 提醒: {campaign.name}",
                message=_build_message(campaign, reason),
            )
        )
    return alerts


def _get_or_set_first_seen(state: AppState, campaign: Campaign, now: datetime) -> datetime:
    existing = _parse_datetime(state.campaign_first_seen_times.get(campaign.campaign_id))
    if existing is not None:
        return existing
    state.campaign_first_seen_times[campaign.campaign_id] = now.isoformat()
    return now


def _update_expected_start_time(state: AppState, campaign: Campaign, now: datetime) -> datetime | None:
    existing = _parse_datetime(state.campaign_expected_start_times.get(campaign.campaign_id))
    if campaign.is_upcoming and campaign.countdown_seconds is not None:
        expected = now + timedelta(seconds=campaign.countdown_seconds)
        state.campaign_expected_start_times[campaign.campaign_id] = expected.isoformat()
        return expected
    return existing


def _match_reason(
    campaign: Campaign,
    config: AppConfig,
    now: datetime,
    first_seen: datetime,
    expected_start_at: datetime | None,
    slot_hour: int | None,
) -> str | None:
    if config.remind_first_seen and first_seen == now:
        return "first_seen"
    if (
        config.remind_upcoming_one_hour
        and campaign.is_upcoming
        and campaign.countdown_seconds is not None
        and 0 <= campaign.countdown_seconds <= 3600
    ):
        return "starts_within_1h"
    if (
        config.remind_started_first_hour
        and campaign.is_ongoing
        and expected_start_at is not None
        and expected_start_at <= now < expected_start_at + timedelta(hours=1)
    ):
        return "started_first_hour"
    if config.remind_ongoing and campaign.is_ongoing and slot_hour is not None and now.hour == slot_hour:
        return "ongoing_daily"
    if (
        config.remind_upcoming
        and campaign.is_upcoming
        and campaign.countdown_seconds is not None
        and 3600 < campaign.countdown_seconds <= 86400
    ):
        return "starts_within_24h"
    return None


def _current_slot_hour(now: datetime, reminder_time_hours: tuple[int, ...]) -> int | None:
    valid_hours = sorted({hour for hour in reminder_time_hours if 0 <= int(hour) <= 23})
    active_slot: int | None = None
    for hour in valid_hours:
        if now.hour >= hour:
            active_slot = hour
    return active_slot


def _build_state_key(
    campaign_id: str,
    reason: str,
    now: datetime,
    slot_hour: int | None,
    expected_start_at: datetime | None,
) -> str:
    if reason == "ongoing_daily":
        return f"{campaign_id}|{now.date().isoformat()}|{slot_hour:02d}"
    if reason == "first_seen":
        return f"{campaign_id}|first_seen"
    event_marker = (expected_start_at or now).date().isoformat()
    return f"{campaign_id}|{reason}|{event_marker}"


def _build_message(campaign: Campaign, reason: str) -> str:
    if reason == "first_seen":
        return f"{campaign.name} 首次被检测到，当前状态 {campaign.status_text or '未知'}，倒计时 {campaign.countdown_text or '-'}。"
    if reason == "starts_within_1h":
        return f"{campaign.name} 将在 1 小时内开始，当前倒计时 {campaign.countdown_text or '-'}。"
    if reason == "started_first_hour":
        return f"{campaign.name} 已开始且处于第 1 个小时内，奖励 {campaign.reward_text}。"
    if reason == "ongoing_daily":
        return f"{campaign.name} 当前进行中，奖励 {campaign.reward_text}。"
    return f"{campaign.name} 将在 24 小时内开始，当前倒计时 {campaign.countdown_text or '-'}。"


def _parse_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return datetime.fromisoformat(raw)
