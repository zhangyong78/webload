from __future__ import annotations

from dataclasses import replace

import pytest
import requests

from flash_earn_reminder import okx_client


ENGLISH_ARTICLE = """
<h1>OKX Flash Earn Lite (ABC) is now live</h1>
<p>Campaign period: January 9, 2099 07:00 – January 14, 2099 07:00 (UTC)</p>
<p>Project token: ABC (Example)</p>
<p>Airdrop total rewards: 15,000,000 ABC</p>
<p>Pool 1: BTC Subscription Pool | Pool 2: XRP Subscription Pool</p>
"""

CHINESE_ARTICLE = """
<h1>欧易闪赚 Lite 上线 Example</h1>
<p>活动时间：2099年1月9日 15:00 至 2099年1月14日 15:00（UTC+8）</p>
<p>项目名称：ABC (Example)</p>
<p>空投总奖池：15,000,000 ABC</p>
<p>奖池 1：BTC 申购池 奖池 2：XRP 申购池</p>
"""


class FakeResponse:
    def __init__(self, url: str, text: str):
        self.url = url
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_public_announcements_use_english_events_when_chinese_list_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    article_url = "https://www.okx.com/help/example-flash-earn-lite-abc"
    requested: list[str] = []

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        requested.append(url)
        if url == okx_client.ANNOUNCEMENT_SECTION_URLS[1]:
            return FakeResponse(url, f'<a href="{article_url}">ABC Flash Earn</a>')
        if url == article_url:
            return FakeResponse(url, ENGLISH_ARTICLE)
        return FakeResponse(url, "<h1>Latest announcements</h1>")

    monkeypatch.setattr(okx_client.requests, "get", fake_get)

    campaigns = okx_client.fetch_public_flash_earn_announcements()

    assert len(campaigns) == 1
    assert campaigns[0].name == "ABC"
    assert campaigns[0].reward_text == "15,000,000 ABC"
    assert campaigns[0].supported_assets == ("BTC", "XRP")
    assert campaigns[0].is_upcoming
    assert requested.count(article_url) == 1


def test_public_announcements_continue_when_one_section_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    article_url = "https://www.okx.com/help/example-flash-earn-lite-abc"

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        if url == okx_client.ANNOUNCEMENT_SECTION_URLS[0]:
            raise requests.ConnectionError("section unavailable")
        if url == okx_client.ANNOUNCEMENT_SECTION_URLS[1]:
            return FakeResponse(url, f'<a href="{article_url}">ABC Flash Earn</a>')
        if url == article_url:
            return FakeResponse(url, ENGLISH_ARTICLE)
        return FakeResponse(url, "<h1>Latest announcements</h1>")

    monkeypatch.setattr(okx_client.requests, "get", fake_get)

    assert [campaign.name for campaign in okx_client.fetch_public_flash_earn_announcements()] == ["ABC"]


def test_public_announcements_deduplicate_localized_article_links(monkeypatch: pytest.MonkeyPatch) -> None:
    chinese_url = "https://www.okx.com/zh-hans/help/example-flash-earn-lite-abc"
    english_url = "https://www.okx.com/help/example-flash-earn-lite-abc"
    requested: list[str] = []

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        requested.append(url)
        if url == okx_client.ANNOUNCEMENT_SECTION_URLS[0]:
            return FakeResponse(url, f'<a href="{chinese_url}">ABC 闪赚</a>')
        if url == okx_client.ANNOUNCEMENT_SECTION_URLS[1]:
            return FakeResponse(url, f'<a href="{english_url}">ABC Flash Earn</a>')
        if url == chinese_url:
            return FakeResponse(url, CHINESE_ARTICLE)
        if url == english_url:
            return FakeResponse(url, ENGLISH_ARTICLE)
        return FakeResponse(url, "<h1>Latest announcements</h1>")

    monkeypatch.setattr(okx_client.requests, "get", fake_get)

    campaigns = okx_client.fetch_public_flash_earn_announcements()

    assert [campaign.name for campaign in campaigns] == ["ABC"]
    assert campaigns[0].supported_assets == ("BTC", "XRP")
    assert requested.count(chinese_url) == 1
    assert english_url not in requested


def test_public_announcements_do_not_report_zero_when_all_lists_lack_links(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        okx_client.requests,
        "get",
        lambda url, **kwargs: FakeResponse(url, "<h1>No announcement links</h1>"),
    )

    with pytest.raises(RuntimeError, match="未返回闪赚公告链接"):
        okx_client.fetch_public_flash_earn_announcements()


def test_product_page_failure_falls_back_to_public_announcements(monkeypatch: pytest.MonkeyPatch) -> None:
    campaign = okx_client._campaign_from_public_announcement(ENGLISH_ARTICLE, "https://www.okx.com/help/example")
    assert campaign is not None
    monkeypatch.setattr(okx_client, "fetch_page", lambda url: (_ for _ in ()).throw(requests.ConnectionError("blocked")))
    monkeypatch.setattr(okx_client, "fetch_public_flash_earn_announcements", lambda: [campaign])

    assert okx_client.fetch_campaigns() == [campaign]


def test_product_page_is_supplemented_by_new_public_campaigns(monkeypatch: pytest.MonkeyPatch) -> None:
    announcement = okx_client._campaign_from_public_announcement(ENGLISH_ARTICLE, "https://www.okx.com/help/example")
    assert announcement is not None
    product = replace(announcement, campaign_id="product", source_url=okx_client.DEFAULT_URL)
    new_coin = replace(announcement, campaign_id="new", name="DEF", reward_text="2,000 DEF")
    monkeypatch.setattr(okx_client, "fetch_page", lambda url: "<html>Product page</html>")
    monkeypatch.setattr(okx_client, "parse_campaigns", lambda html: [product])
    monkeypatch.setattr(okx_client, "fetch_public_flash_earn_announcements", lambda: [announcement, new_coin])

    assert okx_client.fetch_campaigns() == [product, new_coin]
