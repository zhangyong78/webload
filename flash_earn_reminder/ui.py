from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QCloseEvent, QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSystemTrayIcon,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from flash_earn_reminder import __version__
from flash_earn_reminder.emailing import build_alert_email, build_simulated_ongoing_email, import_qqokx_email_config, send_email_alert
from flash_earn_reminder.instance_guard import SingleInstanceGuard
from flash_earn_reminder.models import AlertEvent, AppConfig, AppState, Campaign, EmailConfig
from flash_earn_reminder.monitor import run_monitor_cycle
from flash_earn_reminder.rules import build_alerts, toggle_campaign_mute
from flash_earn_reminder.storage import app_config_path, app_state_path, load_app_config, load_app_state, save_app_config, save_app_state


class WorkerSignals(QObject):
    cycle_finished = Signal(object)
    email_finished = Signal(str)
    email_failed = Signal(str)


class AlertPopupController:
    def __init__(self, parent: QWidget | None) -> None:
        self._dialog = QMessageBox(parent)
        self._dialog.setIcon(QMessageBox.Information)
        self._dialog.setStandardButtons(QMessageBox.Ok)
        self._dialog.setModal(False)
        self._dialog.finished.connect(self._reset_count)
        self._count = 0

    def show(self, title: str, message: str) -> QMessageBox:
        if not self._dialog.isVisible():
            self._count = 0
        self._count += 1
        self._dialog.setWindowTitle(title)
        self._dialog.setText(message)
        self._dialog.setInformativeText(f"窗口未关闭期间累计 {self._count} 条提醒。")
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()
        return self._dialog

    def _reset_count(self, _result: int) -> None:
        self._count = 0


def merge_default_recipients(recipients: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*EmailConfig().recipient_emails, *recipients)))


class CollapsibleSection(QWidget):
    def __init__(self, title: str, *, expanded: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName("sectionToggle")
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)
        self.toggle_button.toggled.connect(self.set_expanded)
        self.toggle_button.setChecked(expanded)
        self.set_expanded(expanded)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_button.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.content.setVisible(expanded)


class CampaignCard(QFrame):
    def __init__(self, campaign: Campaign, muted: bool = False, on_toggle_reminder: Callable[[], None] | None = None) -> None:
        super().__init__()
        self.setObjectName("campaignCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title = QLabel(campaign.name)
        title.setObjectName("campaignTitle")
        title_row.addWidget(title)

        status = QLabel(campaign.status_text or ("即将开始" if campaign.is_upcoming else "未知"))
        status.setObjectName("campaignStatus")
        if campaign.is_ongoing:
            status.setProperty("tone", "ongoing")
        elif campaign.is_upcoming:
            status.setProperty("tone", "upcoming")
        else:
            status.setProperty("tone", "idle")
        title_row.addWidget(status)
        if on_toggle_reminder is not None:
            reminder_button = QPushButton("恢复提醒" if muted else "关闭此活动提醒")
            reminder_button.clicked.connect(on_toggle_reminder)
            title_row.addWidget(reminder_button)
        title_row.addStretch(1)
        layout.addLayout(title_row)

        reward = QLabel(f"总奖励: {campaign.reward_text or '-'}")
        reward.setObjectName("campaignMeta")
        layout.addWidget(reward)

        countdown = QLabel(
            f"{campaign.countdown_label or '倒计时'}: {campaign.countdown_text or '-'}"
        )
        countdown.setObjectName("campaignMeta")
        layout.addWidget(countdown)

        url = QLabel(campaign.source_url)
        url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        url.setObjectName("campaignUrl")
        layout.addWidget(url)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"OKX Flash Earn Reminder v{__version__}")
        self.resize(1180, 860)
        self._signals = WorkerSignals()
        self._signals.cycle_finished.connect(self._handle_cycle_result)
        self._signals.email_finished.connect(self._append_log)
        self._signals.email_failed.connect(self._handle_email_error)

        self.config = load_app_config(app_config_path())
        self.state = load_app_state(app_state_path())
        self._running = True
        self._refreshing = False
        self._last_checked_at: datetime | None = None
        self._latest_campaigns: list[Campaign] = []
        self._has_presented_once = False
        self._alert_popup_controller = AlertPopupController(self)

        self._maybe_bootstrap_email_config()
        self._build_ui()
        self._apply_config_to_form()
        self._apply_styles()
        self._create_tray()
        self._append_log("应用已启动。")
        self._rearm_timer()
        QTimer.singleShot(0, self._present_initial_window)
        QTimer.singleShot(200, lambda: self.check_now("启动"))

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)

        status_group = QGroupBox("运行状态")
        status_layout = QGridLayout(status_group)
        self.running_label = QLabel("运行中")
        self.last_check_label = QLabel("-")
        self.next_check_label = QLabel("-")
        self.page_label = QLabel(self.config.okx_url)
        self.page_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        status_layout.addWidget(QLabel("状态"), 0, 0)
        status_layout.addWidget(self.running_label, 0, 1)
        status_layout.addWidget(QLabel("上次检查"), 0, 2)
        status_layout.addWidget(self.last_check_label, 0, 3)
        status_layout.addWidget(QLabel("下次检查"), 1, 0)
        status_layout.addWidget(self.next_check_label, 1, 1)
        status_layout.addWidget(QLabel("页面"), 1, 2)
        status_layout.addWidget(self.page_label, 1, 3)
        root_layout.addWidget(status_group)

        action_row = QHBoxLayout()
        self.check_now_button = QPushButton("立即检查")
        self.check_now_button.clicked.connect(lambda: self.check_now("手动"))
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.toggle_running)
        self.save_button = QPushButton("保存配置")
        self.save_button.clicked.connect(self.save_settings)
        self.import_mail_button = QPushButton("从 qqokx 导入邮件")
        self.import_mail_button.clicked.connect(self.import_mail_config)
        self.test_mail_button = QPushButton("发送测试邮件")
        self.test_mail_button.clicked.connect(self.send_test_email)
        for widget in (
            self.check_now_button,
            self.pause_button,
            self.save_button,
            self.import_mail_button,
            self.test_mail_button,
        ):
            action_row.addWidget(widget)
        action_row.addStretch(1)
        root_layout.addLayout(action_row)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        left_column = QVBoxLayout()
        left_column.setSpacing(14)
        left_column.addWidget(self._build_settings_group())
        left_column.addWidget(self._build_mail_group())
        left_column.addWidget(self._build_log_group(), 1)
        body_layout.addLayout(left_column, 1)

        self.campaign_container = QWidget()
        self.campaign_layout = QVBoxLayout(self.campaign_container)
        self.campaign_layout.setContentsMargins(0, 0, 0, 0)
        self.campaign_layout.setSpacing(12)
        self.campaign_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.campaign_container)
        scroll.setFrameShape(QFrame.NoFrame)

        campaign_group = QGroupBox("活动列表")
        campaign_layout = QVBoxLayout(campaign_group)
        campaign_layout.addWidget(scroll)
        body_layout.addWidget(campaign_group, 1)

        root_layout.addLayout(body_layout, 1)

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(lambda: self.check_now("自动"))

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("提醒设置")
        form = QFormLayout(group)
        self.schedule_mode_label = QLabel("每日 08:00 / 20:00 + 新活动 14:00 + 关键时点")
        self.reminder_time_label = QLabel()
        self.remind_first_seen_checkbox = QCheckBox("首次发现立即提醒")
        self.remind_pre_start_twenty_five_hours_checkbox = QCheckBox("开始前 25 小时提醒一次")
        self.remind_pre_start_thirty_minutes_checkbox = QCheckBox("开始前 30 分钟提醒一次")
        self.remind_pre_start_six_hours_checkbox = QCheckBox("开始前 6 小时内每小时提醒")
        self.remind_ongoing_checkbox = QCheckBox("进行中每日 08:00 / 20:00 提醒")
        self.system_notify_checkbox = QCheckBox("系统通知")
        self.window_popup_checkbox = QCheckBox("窗口弹窗")
        self.email_checkbox = QCheckBox("邮件提醒")
        self.tray_checkbox = QCheckBox("关闭窗口最小化到托盘")
        form.addRow("检查方式", self.schedule_mode_label)
        form.addRow("提醒时间", self.reminder_time_label)
        form.addRow("", self.remind_first_seen_checkbox)
        form.addRow("", self.remind_pre_start_twenty_five_hours_checkbox)
        form.addRow("", self.remind_pre_start_thirty_minutes_checkbox)
        form.addRow("", self.remind_pre_start_six_hours_checkbox)
        form.addRow("", self.remind_ongoing_checkbox)
        form.addRow("", self.system_notify_checkbox)
        form.addRow("", self.window_popup_checkbox)
        form.addRow("", self.email_checkbox)
        form.addRow("", self.tray_checkbox)
        return group

    def _build_mail_group(self) -> CollapsibleSection:
        section = CollapsibleSection("邮件配置")
        self.mail_config_toggle = section.toggle_button
        self.mail_config_content = section.content
        form = QFormLayout()
        self.smtp_host_edit = QLineEdit()
        self.smtp_port_spin = QSpinBox()
        self.smtp_port_spin.setRange(1, 65535)
        self.smtp_username_edit = QLineEdit()
        self.smtp_password_edit = QLineEdit()
        self.smtp_password_edit.setEchoMode(QLineEdit.Password)
        self.sender_email_edit = QLineEdit()
        self.recipients_edit = QLineEdit()
        self.ssl_checkbox = QCheckBox("使用 SSL")
        form.addRow("SMTP Host", self.smtp_host_edit)
        form.addRow("SMTP Port", self.smtp_port_spin)
        form.addRow("SMTP 用户名", self.smtp_username_edit)
        form.addRow("SMTP 密码", self.smtp_password_edit)
        form.addRow("发件邮箱", self.sender_email_edit)
        form.addRow("收件邮箱", self.recipients_edit)
        form.addRow("", self.ssl_checkbox)
        section.content_layout.addLayout(form)
        return section

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("运行日志")
        layout = QVBoxLayout(group)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(220)
        layout.addWidget(self.log_output)
        return group

    def _apply_config_to_form(self) -> None:
        self.schedule_mode_label.setText("每日 08:00 / 20:00 + 新活动 14:00 + 关键时点")
        self.reminder_time_label.setText("每日 08:00 / 20:00（新活动额外 14:00）")
        self.remind_first_seen_checkbox.setChecked(self.config.remind_first_seen)
        self.remind_pre_start_twenty_five_hours_checkbox.setChecked(self.config.remind_pre_start_twenty_five_hours)
        self.remind_pre_start_thirty_minutes_checkbox.setChecked(self.config.remind_pre_start_thirty_minutes)
        self.remind_pre_start_six_hours_checkbox.setChecked(self.config.remind_pre_start_six_hours)
        self.remind_ongoing_checkbox.setChecked(self.config.remind_ongoing)
        self.system_notify_checkbox.setChecked(self.config.enable_system_notification)
        self.window_popup_checkbox.setChecked(self.config.enable_window_popup)
        self.email_checkbox.setChecked(self.config.enable_email)
        self.tray_checkbox.setChecked(self.config.minimize_to_tray)
        self.smtp_host_edit.setText(self.config.email_config.smtp_host)
        self.smtp_port_spin.setValue(self.config.email_config.smtp_port or 465)
        self.smtp_username_edit.setText(self.config.email_config.smtp_username)
        self.smtp_password_edit.setText(self.config.email_config.smtp_password)
        self.sender_email_edit.setText(self.config.email_config.sender_email)
        self.recipients_edit.setText(";".join(self.config.email_config.recipient_emails))
        self.ssl_checkbox.setChecked(self.config.email_config.use_ssl)

    def _apply_form_to_config(self) -> None:
        recipients = tuple(
            item.strip()
            for item in self.recipients_edit.text().replace(",", ";").split(";")
            if item.strip()
        )
        self.config.poll_interval_minutes = 0
        self.config.reminder_time_hours = (8, 20)
        self.config.remind_first_seen = self.remind_first_seen_checkbox.isChecked()
        self.config.remind_ongoing = self.remind_ongoing_checkbox.isChecked()
        self.config.remind_pre_start_twenty_five_hours = self.remind_pre_start_twenty_five_hours_checkbox.isChecked()
        self.config.remind_pre_start_thirty_minutes = self.remind_pre_start_thirty_minutes_checkbox.isChecked()
        self.config.remind_pre_start_six_hours = self.remind_pre_start_six_hours_checkbox.isChecked()
        self.config.enable_system_notification = self.system_notify_checkbox.isChecked()
        self.config.enable_window_popup = self.window_popup_checkbox.isChecked()
        self.config.enable_email = self.email_checkbox.isChecked()
        self.config.minimize_to_tray = self.tray_checkbox.isChecked()
        self.config.email_config.enabled = self.email_checkbox.isChecked()
        self.config.email_config.smtp_host = self.smtp_host_edit.text().strip()
        self.config.email_config.smtp_port = self.smtp_port_spin.value()
        self.config.email_config.smtp_username = self.smtp_username_edit.text().strip()
        self.config.email_config.smtp_password = self.smtp_password_edit.text()
        self.config.email_config.sender_email = self.sender_email_edit.text().strip()
        self.config.email_config.recipient_emails = recipients
        self.config.email_config.use_ssl = self.ssl_checkbox.isChecked()

    def save_settings(self) -> None:
        self._apply_form_to_config()
        save_app_config(app_config_path(), self.config)
        self._append_log("配置已保存。")
        self._rearm_timer()

    def import_mail_config(self) -> None:
        self._apply_form_to_config()
        try:
            project_path = self.config.qqokx_project_path.strip() or r"D:\qqokx"
            imported = import_qqokx_email_config(project_path)
        except Exception as exc:
            QMessageBox.critical(self, "导入失败", str(exc))
            return
        self.config.email_config = imported
        self.config.enable_email = True
        self._apply_config_to_form()
        save_app_config(app_config_path(), self.config)
        self._append_log("已从 qqokx 导入邮件配置。")

    def send_test_email(self) -> None:
        self._apply_form_to_config()
        subject, body = build_simulated_ongoing_email(self.config.okx_url)
        threading.Thread(
            target=self._send_email_safe,
            args=(subject, body),
            daemon=True,
        ).start()

    def toggle_running(self) -> None:
        self._running = not self._running
        self.pause_button.setText("暂停" if self._running else "继续")
        self.running_label.setText("运行中" if self._running else "已暂停")
        self._append_log("轮询已恢复。" if self._running else "轮询已暂停。")
        self._rearm_timer()

    def check_now(self, source: str = "手动") -> None:
        if not self._running or self._refreshing:
            return
        if source == "手动":
            self._append_log("开始检查（手动）：正在检查 OKX 活动和 A 股可转债申购。")
        self._refreshing = True
        self.running_label.setText("检查中")
        thread = threading.Thread(target=self._run_cycle_worker, args=(source,), daemon=True)
        thread.start()

    def _run_cycle_worker(self, source: str) -> None:
        result = run_monitor_cycle(self.config, self.state, check_source=source)
        self._signals.cycle_finished.emit(result)

    def _handle_cycle_result(self, result: object) -> None:
        self._refreshing = False
        if not hasattr(result, "campaigns"):
            return
        used_cached_campaigns = False
        previous_checked_at = self._last_checked_at
        if not result.error and not result.campaigns and self._latest_campaigns and previous_checked_at is not None:
            elapsed_seconds = max(0, int((result.checked_at - previous_checked_at).total_seconds()))
            cached_campaigns = reuse_active_cached_campaigns(self._latest_campaigns, elapsed_seconds=elapsed_seconds)
            if cached_campaigns:
                result.campaigns = cached_campaigns
                result.alerts = build_alerts(cached_campaigns, self.config, self.state, result.checked_at)
                used_cached_campaigns = True
        self._last_checked_at = result.checked_at
        self._latest_campaigns = list(result.campaigns)
        if result.error:
            self.running_label.setText("检查失败")
            self._append_log(f"检查失败（{result.check_source}）: {result.error}")
        elif used_cached_campaigns:
            self.running_label.setText("运行中" if self._running else "已暂停")
            self._append_log(f"页面返回空活动（{result.check_source}），沿用上一轮 {len(result.campaigns)} 个活动。")
        else:
            self.running_label.setText("运行中" if self._running else "已暂停")
            if not result.campaigns:
                self._append_log(f"检查完成（{result.check_source}）：产品页和公开公告均未发现有效期内的闪赚活动。")
            else:
                from_announcements = any("/help/" in campaign.source_url for campaign in result.campaigns)
                from_product = any("/help/" not in campaign.source_url for campaign in result.campaigns)
                source = "产品页 + 官方公告" if from_announcements and from_product else "官方公告" if from_announcements else "产品页"
                self._append_log(f"检查完成（{result.check_source}，{source}），发现 {len(result.campaigns)} 个活动。")
        self._append_log(convertible_bond_check_log(result))
        if not result.error and result.campaigns and not result.alerts:
            self._append_log(f"本次未触发提醒，规则判定时间 {_format_dt(result.checked_at)}。")
        self.last_check_label.setText(_format_dt(result.checked_at))
        self.next_check_label.setText(_format_dt(self._next_run_time()))
        empty_message = f"活动数据获取失败：{result.error}" if result.error else "当前无可提醒活动。"
        self._render_campaigns(result.campaigns, empty_message=empty_message)
        save_app_state(app_state_path(), self.state)
        for alert in result.alerts:
            self._dispatch_alert(alert)
        for notification in result.notifications:
            self._dispatch_notification(
                notification.title,
                notification.message,
                notification.title,
                notification.message,
            )
        self._rearm_timer()

    def _dispatch_alert(self, alert: AlertEvent) -> None:
        subject, body = build_alert_email(alert)
        self._dispatch_notification(alert.title, alert.message, subject, body)

    def _dispatch_notification(
        self,
        title: str,
        message: str,
        email_subject: str,
        email_body: str,
    ) -> None:
        self._append_log(f"发送通知: {title}")
        if self.config.enable_system_notification and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 10000)
        if self.config.enable_email:
            threading.Thread(
                target=self._send_email_safe,
                args=(email_subject, email_body),
                daemon=True,
            ).start()
        if self.config.enable_window_popup:
            self._alert_popup_controller.show(title, message)

    def _send_email_safe(self, subject: str, body: str) -> None:
        try:
            send_email_alert(subject=subject, body=body, config=self.config.email_config)
        except Exception as exc:
            self._signals.email_failed.emit(str(exc))
            return
        self._signals.email_finished.emit(f"邮件已发送: {subject}")

    def _render_campaigns(self, campaigns: list[Campaign], *, empty_message: str = "当前无可提醒活动。") -> None:
        while self.campaign_layout.count():
            item = self.campaign_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not campaigns:
            empty = QLabel(empty_message)
            empty.setObjectName("emptyState")
            empty.setWordWrap(True)
            self.campaign_layout.addWidget(empty)
            self.campaign_layout.addStretch(1)
            return
        for campaign in campaigns:
            muted = campaign.campaign_id in self.state.muted_campaign_ids
            self.campaign_layout.addWidget(
                CampaignCard(
                    campaign,
                    muted=muted,
                    on_toggle_reminder=lambda campaign_id=campaign.campaign_id: self._toggle_campaign_reminder(campaign_id),
                )
            )
        self.campaign_layout.addStretch(1)

    def _toggle_campaign_reminder(self, campaign_id: str) -> None:
        muted = toggle_campaign_mute(self.state, campaign_id)
        save_app_state(app_state_path(), self.state)
        self._render_campaigns(self._latest_campaigns)
        self._append_log(f"已{'关闭' if muted else '恢复'}活动提醒: {campaign_id}")

    def _append_log(self, message: str) -> None:
        self.log_output.append(format_log_entry(datetime.now(), message))

    def _handle_email_error(self, message: str) -> None:
        self._append_log(f"邮件发送失败: {message}")

    def _create_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(_build_app_icon())
        menu = QMenu(self)
        open_action = QAction("打开主窗口", self)
        open_action.triggered.connect(self._restore_window)
        check_action = QAction("立即检查一次", self)
        check_action.triggered.connect(lambda: self.check_now("手动"))
        pause_action = QAction("暂停/继续", self)
        pause_action.triggered.connect(self.toggle_running)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        for action in (open_action, check_action, pause_action, exit_action):
            menu.addAction(action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _maybe_bootstrap_email_config(self) -> None:
        if self.config.email_config.smtp_host.strip():
            return
        project_path = self.config.qqokx_project_path.strip()
        if not project_path:
            return
        try:
            imported = import_qqokx_email_config(project_path)
            imported.recipient_emails = merge_default_recipients(imported.recipient_emails)
            self.config.email_config = imported
            self.config.enable_email = True
            save_app_config(app_config_path(), self.config)
        except Exception:
            return

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self._restore_window()

    def _restore_window(self) -> None:
        self.show()
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self._move_to_visible_screen_if_needed()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
        self.show()
        self._has_presented_once = True

    def _present_initial_window(self) -> None:
        self._restore_window()

    def _move_to_visible_screen_if_needed(self) -> None:
        frame = self.frameGeometry()
        center = frame.center()
        for screen in QApplication.screens():
            if screen.availableGeometry().contains(center):
                return
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        target = screen.availableGeometry()
        frame.moveCenter(target.center())
        self.move(frame.topLeft())

    def _rearm_timer(self) -> None:
        self.timer.stop()
        if not self._running:
            self.next_check_label.setText("-")
            return
        next_run = self._next_run_time()
        self.next_check_label.setText(_format_dt(next_run))
        if next_run is None:
            return
        interval_ms = timer_interval_ms(datetime.now(), next_run)
        self.timer.start(interval_ms)

    def _next_run_time(self) -> datetime | None:
        if not self._running:
            return None
        reference_time = self._last_checked_at or datetime.now()
        return next_monitor_run_time(
            datetime.now(),
            reference_time,
            self.config.reminder_time_hours,
            self._latest_campaigns,
            self.config,
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if can_minimize_to_tray(self.config.minimize_to_tray, self._has_presented_once):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "OKX Flash Earn Reminder",
                "程序已最小化到系统托盘，仍会继续检查活动。",
                QSystemTrayIcon.Information,
                5000,
            )
            return
        super().closeEvent(event)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #101114; color: #f3f4f6; }
            QGroupBox {
                border: 1px solid #262a33;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: 600;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QLineEdit, QSpinBox, QTextEdit {
                background: #171923;
                border: 1px solid #2c3340;
                border-radius: 8px;
                padding: 6px;
                color: #f3f4f6;
            }
            QPushButton {
                background: #1f6feb;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover { background: #388bfd; }
            QToolButton#sectionToggle {
                background: #171923;
                border: 1px solid #262a33;
                border-radius: 10px;
                padding: 9px 12px;
                color: #f3f4f6;
                font-weight: 600;
                text-align: left;
            }
            QToolButton#sectionToggle:hover { border-color: #388bfd; }
            QCheckBox { spacing: 8px; }
            QFrame#campaignCard {
                background: #171923;
                border: 1px solid #2d333b;
                border-radius: 16px;
            }
            QLabel#campaignTitle { font-size: 26px; font-weight: 700; }
            QLabel#campaignMeta { font-size: 16px; color: #d1d5db; }
            QLabel#campaignUrl { font-size: 12px; color: #8b949e; }
            QLabel#campaignStatus {
                border-radius: 10px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: 700;
            }
            QLabel#campaignStatus[tone="ongoing"] { background: #16351f; color: #7ee787; }
            QLabel#campaignStatus[tone="upcoming"] { background: #3a2a12; color: #f2cc60; }
            QLabel#campaignStatus[tone="idle"] { background: #2a2f3a; color: #d1d5db; }
            QLabel#emptyState { color: #9ca3af; padding: 24px; font-size: 16px; }
            """
        )


def _build_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#1f6feb"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(6, 6, 52, 52)
    painter.setBrush(QColor("#7ee787"))
    painter.drawEllipse(18, 18, 28, 28)
    painter.end()
    return QIcon(pixmap)


def _format_dt(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def format_log_entry(timestamp: datetime, message: str) -> str:
    return f"[{_format_dt(timestamp)}] {message}"


def convertible_bond_check_log(result: object) -> str:
    source = str(getattr(result, "check_source", "自动"))
    error = str(getattr(result, "convertible_bond_error", "")).strip()
    if error:
        return f"可转债检查失败（{source}）: {error}"
    count = max(0, int(getattr(result, "convertible_bond_subscription_count", 0)))
    if count == 0:
        return f"可转债检查完成（{source}）：今日无可申购转债。"
    return f"可转债检查完成（{source}）：今日有 {count} 只可申购转债。"


def timer_interval_ms(current: datetime, target: datetime) -> int:
    return max(1000, ceil((target - current).total_seconds() * 1000))


def reuse_active_cached_campaigns(campaigns: list[Campaign], *, elapsed_seconds: int) -> list[Campaign]:
    elapsed = max(0, int(elapsed_seconds))
    cached_campaigns: list[Campaign] = []
    for campaign in campaigns:
        if campaign.countdown_seconds is None:
            continue
        remaining_seconds = max(0, campaign.countdown_seconds - elapsed)
        if remaining_seconds == 0:
            continue
        cached_campaigns.append(
            replace(
                campaign,
                countdown_seconds=remaining_seconds,
                countdown_text=_format_countdown_text(remaining_seconds),
            )
        )
    return cached_campaigns


def _format_countdown_text(total_seconds: int) -> str:
    days, remainder = divmod(max(0, total_seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days:02d} 日 {hours:02d} 时 {minutes:02d} 分 {seconds:02d} 秒"


def next_scheduled_run_time(current: datetime, hours: tuple[int, ...]) -> datetime:
    valid_hours = sorted({int(hour) for hour in hours if 0 <= int(hour) <= 23})
    for hour in valid_hours:
        candidate = current.replace(hour=hour, minute=0, second=0, microsecond=0)
        if candidate > current:
            return candidate
    first_hour = valid_hours[0] if valid_hours else 8
    next_day = current + timedelta(days=1)
    return next_day.replace(hour=first_hour, minute=0, second=0, microsecond=0)


def next_monitor_run_time(
    current: datetime,
    reference_time: datetime,
    daily_hours: tuple[int, ...],
    campaigns: list[Campaign],
    config: AppConfig,
) -> datetime:
    candidates = [
        next_scheduled_run_time(current, daily_hours),
        next_scheduled_run_time(current, (10, 14)),
    ]
    for campaign in campaigns:
        if campaign.countdown_seconds is None:
            continue
        if campaign.is_upcoming:
            candidates.append(next_scheduled_run_time(current, (14,)))
            expected_start = reference_time + timedelta(seconds=campaign.countdown_seconds)
            if expected_start > current:
                candidates.append(expected_start)
            if config.remind_pre_start_twenty_five_hours:
                candidate = expected_start - timedelta(hours=25)
                if candidate > current:
                    candidates.append(candidate)
            if config.remind_pre_start_thirty_minutes:
                candidate = expected_start - timedelta(minutes=30)
                if candidate > current:
                    candidates.append(candidate)
            if config.remind_pre_start_six_hours:
                for hours_before_start in range(6, 0, -1):
                    candidate = expected_start - timedelta(hours=hours_before_start)
                    if candidate > current:
                        candidates.append(candidate)
        if campaign.is_ongoing:
            ending_reminder = reference_time + timedelta(seconds=campaign.countdown_seconds - 3600)
            if ending_reminder > current:
                candidates.append(ending_reminder)
    return min(candidates)


def can_minimize_to_tray(config_enabled: bool, has_presented_once: bool) -> bool:
    return bool(config_enabled and has_presented_once)


def run() -> int:
    QGuiApplication.setApplicationDisplayName("OKX Flash Earn Reminder")
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    instance_root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
    guard = SingleInstanceGuard(instance_root, window._restore_window)
    if not guard.activate_or_become_primary():
        return 0
    window._instance_guard = guard
    window.show()
    return app.exec()
