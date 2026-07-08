from flash_earn_reminder.emailing import build_alert_email, build_simulated_ongoing_email, email_config_from_snapshot
from flash_earn_reminder.models import AlertEvent, Campaign


def test_email_config_from_snapshot_parses_recipients() -> None:
    snapshot = {
        "enabled": True,
        "smtp_host": "smtp.126.com",
        "smtp_port": 465,
        "smtp_username": "qqokx78@126.com",
        "smtp_password": "secret",
        "sender_email": "qqokx78@126.com",
        "recipient_emails": "a@example.com;b@example.com\nc@example.com",
        "use_ssl": True,
    }

    config = email_config_from_snapshot(snapshot)

    assert config.enabled is True
    assert config.smtp_host == "smtp.126.com"
    assert config.smtp_port == 465
    assert config.recipient_emails == ("a@example.com", "b@example.com", "c@example.com")


def test_build_simulated_ongoing_email_uses_robo_campaign_copy() -> None:
    subject, body = build_simulated_ongoing_email(
        "https://www.okx.com/zh-hans/flash-earn/stake-to-earn?from-page=trade"
    )

    assert subject == "okx 闪赚活动提醒"
    assert "页面：质押赚币" in body
    assert "项目：ROBO Lite" in body
    assert "状态：进行中" in body
    assert "总奖励：20,000,000 ROBO" in body
    assert "支持币种：BTC、OKSOL、OKB、AI" in body
    assert "倒计时：00日00时33分44秒" in body


def test_build_alert_email_uses_simple_flash_earn_copy() -> None:
    alert = AlertEvent(
        campaign=Campaign(
            campaign_id="AI",
            name="AI",
            status_text="即将上线",
            reward_text="8,000,000 AI",
            icon_url="",
            countdown_label="活动即将开始",
            countdown_text="02 日 17 时 18 分 31 秒",
            countdown_seconds=234000,
            is_ongoing=False,
            is_upcoming=True,
            source_url="https://www.okx.com/zh-hans/flash-earn/stake-to-earn?from-page=trade",
            supported_assets=("BTC", "OKSOL", "OKB", "AI"),
        ),
        reason="first_seen",
        title="unused",
        message="unused",
    )

    subject, body = build_alert_email(alert)

    assert subject == "okx 闪赚活动提醒"
    assert "页面：质押赚币" in body
    assert "项目：AI" in body
    assert "状态：活动即将开始" in body
    assert "总奖励：8,000,000 AI" in body
    assert "支持币种：BTC、OKSOL、OKB、AI" in body
    assert "倒计时：02 日 17 时 18 分 31 秒" in body
