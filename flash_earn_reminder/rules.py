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
        if campaign.campaign_id in state.muted_campaign_ids:
            continue
        first_seen = _get_or_set_first_seen(state, campaign, now)
        expected_start_at = _update_expected_start_time(state, campaign, now)
        expected_end_at = _expected_end_time(campaign, now)
        reasons = _match_reasons(campaign, config, now, first_seen, expected_start_at, expected_end_at, slot_hour)
        for reason in reasons:
            state_key = _build_state_key(campaign.campaign_id, reason, now, slot_hour, expected_start_at, expected_end_at)
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


def _expected_end_time(campaign: Campaign, now: datetime) -> datetime | None:
    if campaign.is_ongoing and campaign.countdown_seconds is not None:
        return now + timedelta(seconds=campaign.countdown_seconds)
    return None


def _match_reasons(
    campaign: Campaign,
    config: AppConfig,
    now: datetime,
    first_seen: datetime,
    expected_start_at: datetime | None,
    expected_end_at: datetime | None,
    slot_hour: int | None,
) -> list[str]:
    reasons: list[str] = []
    if config.remind_first_seen and first_seen == now:
        reasons.append("first_seen")
    elif campaign.is_upcoming and campaign.countdown_seconds is not None:
        if config.remind_pre_start_twenty_five_hours and 24 * 3600 < campaign.countdown_seconds <= 25 * 3600:
            reasons.append("starts_within_25h")
        if config.remind_pre_start_thirty_minutes and 0 < campaign.countdown_seconds <= 30 * 60:
            reasons.append("starts_within_30m")
        elif config.remind_pre_start_six_hours:
            remaining_hours = (campaign.countdown_seconds + 3599) // 3600
            if 1 <= remaining_hours <= 6:
                reasons.append(f"starts_within_{remaining_hours}h")
    if campaign.is_ongoing and campaign.countdown_seconds is not None and 0 <= campaign.countdown_seconds <= 3600:
        reasons.append("ends_within_1h")
    if config.remind_ongoing and campaign.is_ongoing and slot_hour is not None and now.hour == slot_hour:
        reasons.append("ongoing_daily")
    if campaign.is_upcoming and first_seen < now and now.hour == 14:
        reasons.append("new_task_daily")
    return reasons


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
    expected_end_at: datetime | None,
) -> str:
    if reason == "ongoing_daily":
        return f"{campaign_id}|{now.date().isoformat()}|{slot_hour:02d}"
    if reason == "new_task_daily":
        return f"{campaign_id}|{now.date().isoformat()}|14"
    if reason == "first_seen":
        return f"{campaign_id}|first_seen"
    event_marker = (expected_start_at or expected_end_at or now).date().isoformat()
    return f"{campaign_id}|{reason}|{event_marker}"


def _build_message(campaign: Campaign, reason: str) -> str:
    if reason == "first_seen":
        return f"{campaign.name} 首次被检测到，当前状态 {campaign.status_text or '未知'}，倒计时 {campaign.countdown_text or '-'}。"
    if reason == "starts_within_30m":
        return f"{campaign.name} 将在 30 分钟内开始，当前倒计时 {campaign.countdown_text or '-'}。"
    if reason.startswith("starts_within_"):
        remaining_hours = reason.removeprefix("starts_within_").removesuffix("h")
        return f"{campaign.name} 将在 {remaining_hours} 小时内开始，当前倒计时 {campaign.countdown_text or '-'}。"
    if reason == "ends_within_1h":
        return f"{campaign.name} 将在 1 小时内结束，当前倒计时 {campaign.countdown_text or '-'}。"
    if reason == "ongoing_daily":
        return f"{campaign.name} 当前进行中，奖励 {campaign.reward_text}。"
    if reason == "new_task_daily":
        return f"{campaign.name} 是已发现的新活动，当前倒计时 {campaign.countdown_text or '-'}。"
    return f"{campaign.name} 当前状态 {campaign.status_text or '未知'}。"


def toggle_campaign_mute(state: AppState, campaign_id: str) -> bool:
    if campaign_id in state.muted_campaign_ids:
        state.muted_campaign_ids.remove(campaign_id)
        return False
    state.muted_campaign_ids.append(campaign_id)
    return True


def _parse_datetime(value: str | None) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    return datetime.fromisoformat(raw)
