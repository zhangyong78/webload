from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(slots=True)
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    recipient_emails: tuple[str, ...] = (
        "conystar@126.com",
        "187377363220@163.com",
        "1057902445@qq.com",
        "xhbyssy@163.com",
    )
    use_ssl: bool = True


@dataclass(slots=True)
class AppConfig:
    okx_url: str = "https://www.okx.com/zh-hans/flash-earn/stake-to-earn?from-page=trade"
    poll_interval_minutes: int = 0
    reminder_time_hours: tuple[int, ...] = (8, 20)
    remind_first_seen: bool = True
    remind_ongoing: bool = True
    remind_pre_start_twenty_five_hours: bool = True
    remind_pre_start_thirty_minutes: bool = True
    remind_pre_start_six_hours: bool = True
    enable_system_notification: bool = True
    enable_window_popup: bool = True
    enable_email: bool = True
    minimize_to_tray: bool = True
    qqokx_project_path: str = r"D:\qqokx"
    email_config: EmailConfig = field(default_factory=EmailConfig)


@dataclass(slots=True)
class AppState:
    last_alert_times: dict[str, str] = field(default_factory=dict)
    campaign_first_seen_times: dict[str, str] = field(default_factory=dict)
    campaign_expected_start_times: dict[str, str] = field(default_factory=dict)
    muted_campaign_ids: list[str] = field(default_factory=list)
    convertible_bond_alert_slots: dict[str, list[int]] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ConvertibleBondSubscription:
    name: str
    bond_code: str
    subscription_code: str
    subscription_date: date


@dataclass(slots=True)
class Campaign:
    campaign_id: str
    name: str
    status_text: str
    reward_text: str
    icon_url: str
    countdown_label: str
    countdown_text: str
    countdown_seconds: int | None
    is_ongoing: bool
    is_upcoming: bool
    source_url: str
    supported_assets: tuple[str, ...] = ()


@dataclass(slots=True)
class AlertEvent:
    campaign: Campaign
    reason: str
    title: str
    message: str


@dataclass(slots=True, frozen=True)
class NotificationEvent:
    title: str
    message: str


@dataclass(slots=True)
class MonitorCycleResult:
    campaigns: list[Campaign] = field(default_factory=list)
    alerts: list[AlertEvent] = field(default_factory=list)
    notifications: list[NotificationEvent] = field(default_factory=list)
    checked_at: datetime | None = None
    error: str = ""
    convertible_bond_error: str = ""
    check_source: str = "自动"
