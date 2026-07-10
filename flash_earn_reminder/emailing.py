from __future__ import annotations

import importlib
import json
import re
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Mapping

from flash_earn_reminder.models import AlertEvent, EmailConfig


def email_config_from_snapshot(snapshot: Mapping[str, Any]) -> EmailConfig:
    recipients = tuple(
        item.strip()
        for item in re.split(r"[,\n;]+", str(snapshot.get("recipient_emails", "")))
        if item.strip()
    )
    return EmailConfig(
        enabled=bool(snapshot.get("enabled", False)),
        smtp_host=str(snapshot.get("smtp_host", "")).strip(),
        smtp_port=int(snapshot.get("smtp_port", 465)),
        smtp_username=str(snapshot.get("smtp_username", "")).strip(),
        smtp_password=str(snapshot.get("smtp_password", "")).strip(),
        sender_email=str(snapshot.get("sender_email", "")).strip(),
        recipient_emails=recipients,
        use_ssl=bool(snapshot.get("use_ssl", True)),
    )


def import_qqokx_email_config(project_root: Path) -> EmailConfig:
    snapshot = _load_snapshot_from_project(project_root)
    return email_config_from_snapshot(snapshot)


def build_alert_email(alert: AlertEvent) -> tuple[str, str]:
    status = _display_status(alert)
    supported_assets = _display_supported_assets(alert)
    subject = "okx 闪赚活动提醒"
    body = (
        "页面：质押赚币\n"
        f"项目：{alert.campaign.name}\n"
        f"状态：{status}\n"
        f"总奖励：{alert.campaign.reward_text or '-'}\n"
        f"支持币种：{supported_assets}\n"
        f"倒计时：{alert.campaign.countdown_text or '-'}\n"
        f"链接：{alert.campaign.source_url}"
    )
    return subject, body


def build_simulated_ongoing_email(okx_url: str) -> tuple[str, str]:
    return (
        "okx 闪赚活动提醒",
        (
            "页面：质押赚币\n"
            "项目：ROBO Lite\n"
            "状态：进行中\n"
            "总奖励：20,000,000 ROBO\n"
            "支持币种：BTC、OKSOL、OKB、AI\n"
            "倒计时：00日00时33分44秒\n"
            f"链接：{okx_url}"
        ),
    )


def send_email_alert(*, subject: str, body: str, config: EmailConfig) -> None:
    sender = (config.sender_email or config.smtp_username).strip()
    if not (config.enabled and config.smtp_host and sender and config.recipient_emails):
        raise ValueError("邮件配置不完整，无法发送邮件。")
    if config.use_ssl:
        with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=20) as smtp:
            _login_if_needed(smtp, config)
            _send_private_messages(smtp, subject, body, sender, config.recipient_emails)
        return
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        _login_if_needed(smtp, config)
        _send_private_messages(smtp, subject, body, sender, config.recipient_emails)


def _send_private_messages(
    smtp: smtplib.SMTP,
    subject: str,
    body: str,
    sender: str,
    recipients: tuple[str, ...],
) -> None:
    for recipient in recipients:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = recipient
        message.set_content(body, charset="utf-8")
        smtp.send_message(message)


def _login_if_needed(smtp: smtplib.SMTP, config: EmailConfig) -> None:
    if config.smtp_username and config.smtp_password:
        smtp.login(config.smtp_username, config.smtp_password)


def _load_snapshot_from_project(project_root: Path) -> Mapping[str, Any]:
    normalized_root = Path(project_root).expanduser().resolve()
    sys.path.insert(0, str(normalized_root))
    try:
        importlib.invalidate_caches()
        module = importlib.import_module("okx_quant.persistence")
        snapshot = module.load_notification_snapshot()
        if isinstance(snapshot, Mapping):
            return snapshot
    except Exception:
        pass
    finally:
        try:
            sys.path.remove(str(normalized_root))
        except ValueError:
            pass
    for candidate in (
        normalized_root.parent / "qqokx_data" / "config" / "settings.json",
        Path(r"D:\qqokx_data\config\settings.json"),
    ):
        if candidate.exists():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
    raise FileNotFoundError(f"未能从 {normalized_root} 导入 qqokx 邮件配置。")


def _display_status(alert: AlertEvent) -> str:
    if alert.campaign.countdown_label.strip():
        return alert.campaign.countdown_label.strip()
    return alert.campaign.status_text.strip() or "状态未知"


def _display_supported_assets(alert: AlertEvent) -> str:
    if alert.campaign.supported_assets:
        return "、".join(alert.campaign.supported_assets)
    return "-"
