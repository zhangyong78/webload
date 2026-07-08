from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from flash_earn_reminder.models import AppConfig, AppState, EmailConfig


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def data_dir() -> Path:
    target = runtime_root() / "data"
    target.mkdir(parents=True, exist_ok=True)
    return target


def app_config_path() -> Path:
    return data_dir() / "app_config.json"


def app_state_path() -> Path:
    return data_dir() / "app_state.json"


def load_app_config(path: Path | None = None) -> AppConfig:
    target = path or app_config_path()
    if not target.exists():
        config = AppConfig()
        save_app_config(target, config)
        return config
    payload = json.loads(target.read_text(encoding="utf-8"))
    email_payload = payload.get("email_config", {})
    raw_schedule = payload.get("reminder_time_hours")
    if isinstance(raw_schedule, list) and raw_schedule:
        reminder_time_hours = tuple(int(item) for item in raw_schedule)
    else:
        reminder_time_hours = (
            int(payload.get("reminder_time_hour", payload.get("reminder_interval_hours", 8))),
            14,
        )
    return AppConfig(
        okx_url=str(payload.get("okx_url", AppConfig.okx_url)),
        poll_interval_minutes=int(payload.get("poll_interval_minutes", 0)),
        reminder_time_hours=reminder_time_hours,
        remind_first_seen=bool(payload.get("remind_first_seen", True)),
        remind_ongoing=bool(payload.get("remind_ongoing", True)),
        remind_upcoming=bool(payload.get("remind_upcoming", False)),
        remind_upcoming_one_hour=bool(payload.get("remind_upcoming_one_hour", True)),
        remind_started_first_hour=bool(payload.get("remind_started_first_hour", True)),
        enable_system_notification=bool(payload.get("enable_system_notification", True)),
        enable_window_popup=bool(payload.get("enable_window_popup", True)),
        enable_email=bool(payload.get("enable_email", True)),
        minimize_to_tray=bool(payload.get("minimize_to_tray", True)),
        qqokx_project_path=str(payload.get("qqokx_project_path", r"D:\qqokx")),
        email_config=EmailConfig(
            enabled=bool(email_payload.get("enabled", False)),
            smtp_host=str(email_payload.get("smtp_host", "")),
            smtp_port=int(email_payload.get("smtp_port", 465)),
            smtp_username=str(email_payload.get("smtp_username", "")),
            smtp_password=str(email_payload.get("smtp_password", "")),
            sender_email=str(email_payload.get("sender_email", "")),
            recipient_emails=tuple(email_payload.get("recipient_emails", ())),
            use_ssl=bool(email_payload.get("use_ssl", True)),
        ),
    )


def save_app_config(path: Path | None, config: AppConfig) -> None:
    target = path or app_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(config)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_app_state(path: Path | None = None) -> AppState:
    target = path or app_state_path()
    if not target.exists():
        return AppState()
    payload = json.loads(target.read_text(encoding="utf-8"))
    return AppState(
        last_alert_times=dict(payload.get("last_alert_times", {})),
        campaign_first_seen_times=dict(payload.get("campaign_first_seen_times", {})),
        campaign_expected_start_times=dict(payload.get("campaign_expected_start_times", {})),
    )


def save_app_state(path: Path | None, state: AppState) -> None:
    target = path or app_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
