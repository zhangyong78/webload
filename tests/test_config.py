from flash_earn_reminder.emailing import build_alert_email, build_simulated_ongoing_email, email_config_from_snapshot, send_email_alert
from flash_earn_reminder.models import AlertEvent, AppState, Campaign, EmailConfig
from flash_earn_reminder.storage import load_app_config, load_app_state, save_app_state


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


def test_default_email_config_includes_requested_recipients() -> None:
    assert EmailConfig().recipient_emails == (
        "conystar@126.com",
        "187377363220@163.com",
        "1057902445@qq.com",
        "xhbyssy@163.com",
    )


def test_load_app_config_enables_twenty_five_hour_reminder_by_default(tmp_path) -> None:
    config_path = tmp_path / "app_config.json"
    config_path.write_text("{}", encoding="utf-8")

    config = load_app_config(config_path)

    assert config.remind_pre_start_twenty_five_hours is True


def test_load_app_config_enables_thirty_minute_reminder_by_default(tmp_path) -> None:
    config_path = tmp_path / "app_config.json"
    config_path.write_text("{}", encoding="utf-8")

    config = load_app_config(config_path)

    assert config.remind_pre_start_thirty_minutes is True


def test_send_email_alert_sends_a_private_message_to_each_recipient(monkeypatch) -> None:
    messages = []

    class FakeSMTP:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def login(self, username, password) -> None:
            return None

        def send_message(self, message) -> None:
            messages.append(message)

    monkeypatch.setattr("flash_earn_reminder.emailing.smtplib.SMTP_SSL", lambda *args, **kwargs: FakeSMTP())
    config = EmailConfig(
        enabled=True,
        smtp_host="smtp.example.com",
        sender_email="sender@example.com",
        recipient_emails=("first@example.com", "second@example.com"),
        use_ssl=True,
    )

    send_email_alert(subject="test", body="body", config=config)

    assert [message["To"] for message in messages] == ["first@example.com", "second@example.com"]


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


def test_muted_campaigns_persist_in_local_state(tmp_path) -> None:
    state_path = tmp_path / "app_state.json"
    save_app_state(state_path, AppState(muted_campaign_ids=["AI"]))

    state = load_app_state(state_path)

    assert state.muted_campaign_ids == ["AI"]


def test_convertible_bond_slots_persist_in_local_state(tmp_path) -> None:
    state_path = tmp_path / "app_state.json"
    save_app_state(
        state_path,
        AppState(convertible_bond_alert_slots={"2026-08-06": [10, 14]}),
    )

    state = load_app_state(state_path)

    assert state.convertible_bond_alert_slots == {"2026-08-06": [10, 14]}


def test_old_state_defaults_convertible_bond_slots_to_empty(tmp_path) -> None:
    state_path = tmp_path / "app_state.json"
    state_path.write_text("{}", encoding="utf-8")

    state = load_app_state(state_path)

    assert state.convertible_bond_alert_slots == {}


def test_load_app_state_normalizes_convertible_bond_slots(tmp_path) -> None:
    state_path = tmp_path / "app_state.json"
    state_path.write_text(
        '{"convertible_bond_alert_slots":{"2026-08-06":[14,10,14,8,"bad"]}}',
        encoding="utf-8",
    )

    state = load_app_state(state_path)

    assert state.convertible_bond_alert_slots == {"2026-08-06": [10, 14]}
