from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from flash_earn_reminder.models import Campaign


DEFAULT_URL = "https://www.okx.com/zh-hans/flash-earn/stake-to-earn?from-page=trade"
ANNOUNCEMENTS_URL = "https://www.okx.com/zh-hans/help/section/announcements-latest-announcements"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
_COUNTDOWN_CN_RE = re.compile(
    r"^\s*(?:(?P<days>\d+)\s*日)?\s*(?:(?P<hours>\d+)\s*时)?\s*"
    r"(?:(?P<minutes>\d+)\s*分)?\s*(?:(?P<seconds>\d+)\s*秒)?\s*$"
)
_COUNTDOWN_EN_RE = re.compile(
    r"^\s*(?:(?P<days>\d+)\s*d(?:ays?)?)?\s*(?:(?P<hours>\d+)\s*h(?:ours?)?)?\s*"
    r"(?:(?P<minutes>\d+)\s*m(?:in(?:utes?)?)?)?\s*(?:(?P<seconds>\d+)\s*s(?:ec(?:onds?)?)?)?\s*$",
    re.IGNORECASE,
)
_REGION_RESTRICTION_MARKERS = (
    "不支持您所在的地区",
    "无法在中国香港特别行政区提供服务",
    "this product is unavailable in your current country/region",
    "not available in your region",
    "unavailable in your region",
)


def fetch_page(url: str = DEFAULT_URL, *, timeout: int = 20) -> str:
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def fetch_campaigns(url: str = DEFAULT_URL) -> list[Campaign]:
    html = fetch_page(url)
    campaigns = parse_campaigns(html)
    if campaigns:
        return campaigns
    if _has_region_restriction_notice(html):
        try:
            announcement_campaigns = fetch_public_flash_earn_announcements()
        except Exception as exc:
            raise RuntimeError(
                f"OKX 产品页受地区限制，且官方活动公告暂时无法读取：{exc}"
            ) from exc
        if announcement_campaigns:
            return announcement_campaigns
        raise RuntimeError("OKX 产品页受地区限制，官方公告中暂未找到有效期内的闪赚活动。")
    return campaigns


def _has_region_restriction_notice(html: str) -> bool:
    page_text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True).casefold()
    return any(marker.casefold() in page_text for marker in _REGION_RESTRICTION_MARKERS)


def fetch_public_flash_earn_announcements(*, timeout: int = 20) -> list[Campaign]:
    response = requests.get(ANNOUNCEMENTS_URL, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    article_urls: list[str] = []
    for link in soup.select('a[href*="/help/"]'):
        href = str(link.get("href", "")).strip()
        if not href or "flash-earn" not in href.casefold() or "help/section/" in href:
            continue
        article_url = urljoin(response.url, href)
        if article_url not in article_urls:
            article_urls.append(article_url)

    campaigns: list[Campaign] = []
    for article_url in article_urls:
        article_response = requests.get(article_url, headers=REQUEST_HEADERS, timeout=timeout)
        article_response.raise_for_status()
        campaign = _campaign_from_public_announcement(article_response.text, article_response.url)
        if campaign is not None:
            campaigns.append(campaign)
    return campaigns


def _campaign_from_public_announcement(html: str, source_url: str) -> Campaign | None:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    period_match = re.search(
        r"活动时间\s*[：:]?\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*"
        r"(\d{1,2}):(\d{2})\s*至\s*(\d{4})年\s*(\d{1,2})月\s*"
        r"(\d{1,2})日\s*(\d{1,2}):(\d{2})\s*[（(]UTC\s*\+\s*8[）)]",
        text,
    )
    if period_match is None:
        return None
    values = [int(value) for value in period_match.groups()]
    local_timezone = timezone(timedelta(hours=8))
    start_at = datetime(*values[:5], tzinfo=local_timezone).astimezone().replace(tzinfo=None)
    end_at = datetime(*values[5:], tzinfo=local_timezone).astimezone().replace(tzinfo=None)
    now = datetime.now().astimezone().replace(tzinfo=None)
    if end_at <= now:
        return None

    name_match = re.search(r"(?:本期上线|推出)\s*([A-Z0-9]{2,})\s*[（(]", text)
    if name_match is None:
        title = _text(soup.select_one("h1"))
        name_match = re.search(r"Flash Earn(?: Lite)?\s*\(([A-Z0-9]{2,})\)", title, re.IGNORECASE)
    if name_match is None:
        return None
    name = name_match.group(1).upper()
    reward_match = re.search(r"空投总奖池\s*[：:]?\s*([\d,]+\s+[A-Z0-9]+)", text)
    reward_text = reward_match.group(1) if reward_match else ""
    supported_assets = tuple(dict.fromkeys(
        re.findall(r"奖池\s*\d+\s*[：:]\s*([A-Z0-9]+)\s*申购池", text)
    ))

    is_upcoming = now < start_at
    countdown_target = start_at if is_upcoming else end_at
    countdown_seconds = max(0, int((countdown_target - now).total_seconds()))
    countdown_label = "活动即将开始" if is_upcoming else "结束倒计时"
    return Campaign(
        campaign_id=hashlib.sha1(f"{name}|{start_at.isoformat()}|{end_at.isoformat()}".encode("utf-8")).hexdigest()[:16],
        name=name,
        status_text="即将开始（官方公告）" if is_upcoming else "进行中（官方公告）",
        reward_text=reward_text,
        icon_url="",
        countdown_label=countdown_label,
        countdown_text=_format_countdown_text(countdown_seconds),
        countdown_seconds=countdown_seconds,
        is_ongoing=not is_upcoming,
        is_upcoming=is_upcoming,
        source_url=source_url,
        supported_assets=supported_assets,
    )


def parse_campaigns(html: str, *, source_url: str = DEFAULT_URL) -> list[Campaign]:
    soup = BeautifulSoup(html, "html.parser")
    countdown_overrides = _load_countdown_overrides(soup)
    campaigns: list[Campaign] = []
    for card in soup.select(".flash-earn-campaign-card"):
        name = _text(card.select_one(".flash-earn-campaign-name"))
        if not name:
            continue
        status_text = _text(card.select_one(".flash-earn-campaign-status"))
        icon_url = _attr(card.select_one(".flash-earn-campaign-icon"), "src")
        supported_assets = _supported_assets_from_card(card)
        reward_text = ""
        countdown_label = ""
        countdown_text = ""
        for row in card.select(".flash-earn-campaign-meta > div"):
            spans = [_text(span) for span in row.select("span")]
            if len(spans) < 2:
                continue
            label, value = spans[0], spans[1]
            if "奖励" in label or "reward" in label.lower():
                reward_text = value
            if _looks_like_countdown_row(label, value):
                countdown_label = label
                countdown_text = value
        reward_text = _override_reward_text(name, reward_text, countdown_overrides)
        countdown_label, countdown_text = _override_countdown_fields(
            name,
            reward_text,
            countdown_label,
            countdown_text,
            countdown_overrides,
        )
        is_ongoing = _is_ongoing(status_text, countdown_label)
        is_upcoming = _is_upcoming(status_text, countdown_label)
        campaigns.append(
            Campaign(
                campaign_id=_campaign_id(name=name, reward_text=reward_text, countdown_label=countdown_label),
                name=name,
                status_text=status_text,
                reward_text=reward_text,
                icon_url=icon_url,
                countdown_label=countdown_label,
                countdown_text=countdown_text,
                countdown_seconds=parse_countdown_to_seconds(countdown_text),
                is_ongoing=is_ongoing,
                is_upcoming=is_upcoming,
                source_url=source_url,
                supported_assets=supported_assets,
            )
        )
    return campaigns


def parse_countdown_to_seconds(value: str) -> int | None:
    raw = value.strip()
    if not raw:
        return None
    for pattern in (_COUNTDOWN_CN_RE, _COUNTDOWN_EN_RE):
        match = pattern.match(raw)
        if not match:
            continue
        parts = {key: int(chunk or 0) for key, chunk in match.groupdict().items()}
        total = parts["days"] * 86400 + parts["hours"] * 3600 + parts["minutes"] * 60 + parts["seconds"]
        return total
    return None


def _load_countdown_overrides(soup: BeautifulSoup) -> dict[tuple[str, str], tuple[str, str]]:
    script = soup.select_one("#appState")
    if script is None:
        return {}
    try:
        payload = json.loads(script.get_text())
        flash_data = payload["appContext"]["initialProps"]["preData"]["flashEarnStore"]["flashEarnData"]
    except Exception:
        return {}
    overrides: dict[tuple[str, str], tuple[str, str]] = {}
    for project in flash_data.get("upcomingProjects", []):
        name = _project_currency_name(project)
        reward_text = _project_reward_text(project)
        countdown_seconds = int(int(project.get("countdownToStart", 0) or 0) / 1000)
        if name and reward_text and countdown_seconds > 0:
            overrides[(name, reward_text)] = ("活动即将开始", _format_countdown_text(countdown_seconds))
    for project in flash_data.get("ongoingProjects", []):
        name = _project_currency_name(project)
        reward_text = _project_reward_text(project)
        countdown_seconds = int(int(project.get("countdownToEnd", 0) or 0) / 1000)
        if name and reward_text and countdown_seconds > 0:
            overrides[(name, reward_text)] = ("结束倒计时", _format_countdown_text(countdown_seconds))
    return overrides


def _project_currency_name(project: dict) -> str:
    reward_details = project.get("rewardDetails") or []
    if not reward_details:
        return ""
    return str(reward_details[0].get("currencyName", "")).strip()


def _project_reward_text(project: dict) -> str:
    reward_details = project.get("rewardDetails") or []
    if not reward_details:
        return ""
    amount = str(reward_details[0].get("totalRewardAmount", "")).strip()
    name = str(reward_details[0].get("currencyName", "")).strip()
    if not amount or not name:
        return ""
    return f"{int(amount):,} {name}"


def _override_reward_text(
    name: str,
    reward_text: str,
    overrides: dict[tuple[str, str], tuple[str, str]],
) -> str:
    for project_name, candidate_reward in overrides:
        if project_name == name:
            return candidate_reward
    return reward_text


def _override_countdown_fields(
    name: str,
    reward_text: str,
    countdown_label: str,
    countdown_text: str,
    overrides: dict[tuple[str, str], tuple[str, str]],
) -> tuple[str, str]:
    return overrides.get((name, reward_text), (countdown_label, countdown_text))


def _format_countdown_text(total_seconds: int) -> str:
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days:02d} 日 {hours:02d} 时 {minutes:02d} 分 {seconds:02d} 秒"


def _supported_assets_from_card(card: object) -> tuple[str, ...]:
    values: list[str] = []
    for node in card.select(".flash-earn-pool-type"):
        asset = _text(node).strip()
        if asset and asset not in values:
            values.append(asset)
    return tuple(values)


def _looks_like_countdown_row(label: str, value: str) -> bool:
    normalized_label = label.strip().lower()
    if parse_countdown_to_seconds(value) is not None:
        return True
    return (
        "倒计时" in label
        or "start" in normalized_label
        or "end" in normalized_label
        or "即将开始" in label
    )


def _campaign_id(*, name: str, reward_text: str, countdown_label: str) -> str:
    digest = hashlib.sha1(f"{name}|{reward_text}|{countdown_label}".encode("utf-8")).hexdigest()
    return digest[:16]


def _is_ongoing(status_text: str, countdown_label: str) -> bool:
    normalized_status = status_text.strip().lower()
    normalized_label = countdown_label.strip().lower()
    if any(token in normalized_status for token in ("进行中", "ongoing", "running")):
        return True
    return "结束" in countdown_label or "end" in normalized_label


def _is_upcoming(status_text: str, countdown_label: str) -> bool:
    normalized_status = status_text.strip().lower()
    normalized_label = countdown_label.strip().lower()
    if any(token in normalized_status for token in ("即将", "未开始", "upcoming", "starts soon")):
        return True
    return "开始" in countdown_label or "start" in normalized_label


def _text(node: object) -> str:
    if node is None:
        return ""
    return str(node.get_text(" ", strip=True))


def _attr(node: object, name: str) -> str:
    if node is None:
        return ""
    return str(node.get(name, "")).strip()
