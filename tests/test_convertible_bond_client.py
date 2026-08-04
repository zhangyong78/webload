from __future__ import annotations

from datetime import date

import pytest

from flash_earn_reminder import convertible_bond_client as client
from flash_earn_reminder.convertible_bond_client import (
    fetch_convertible_bond_subscriptions,
    parse_convertible_bond_payload,
)
from flash_earn_reminder.models import ConvertibleBondSubscription


def test_parse_convertible_bond_payload_maps_valid_rows_and_skips_invalid_rows(caplog) -> None:
    payload = {
        "success": True,
        "result": {
            "data": [
                {
                    "SECURITY_NAME_ABBR": "派克转债",
                    "SECURITY_CODE": "111026",
                    "CORRECODE": "713123",
                    "PUBLIC_START_DATE": "2026-08-06 00:00:00",
                },
                {
                    "SECURITY_NAME_ABBR": "缺代码",
                    "SECURITY_CODE": "",
                    "CORRECODE": "",
                    "PUBLIC_START_DATE": "2026-08-06 00:00:00",
                },
                {
                    "SECURITY_NAME_ABBR": "其他日期",
                    "SECURITY_CODE": "123999",
                    "CORRECODE": "370000",
                    "PUBLIC_START_DATE": "2026-08-07 00:00:00",
                },
            ]
        },
    }

    result = parse_convertible_bond_payload(payload, date(2026, 8, 6))

    assert result == [
        ConvertibleBondSubscription(
            name="派克转债",
            bond_code="111026",
            subscription_code="713123",
            subscription_date=date(2026, 8, 6),
        )
    ]
    assert "缺少必填字段" in caplog.text


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"success": False},
        {"success": True, "result": None},
        {"success": True, "result": {"data": None}},
    ],
)
def test_parse_convertible_bond_payload_rejects_invalid_envelopes(payload: object) -> None:
    with pytest.raises(ValueError):
        parse_convertible_bond_payload(payload, date(2026, 8, 6))


def test_parse_convertible_bond_payload_sorts_by_bond_code() -> None:
    payload = {
        "success": True,
        "result": {
            "data": [
                {
                    "SECURITY_NAME_ABBR": "中仑转债",
                    "SECURITY_CODE": "123281",
                    "CORRECODE": "371565",
                    "PUBLIC_START_DATE": "2026-08-06 00:00:00",
                },
                {
                    "SECURITY_NAME_ABBR": "派克转债",
                    "SECURITY_CODE": "111026",
                    "CORRECODE": "713123",
                    "PUBLIC_START_DATE": "2026-08-06 00:00:00",
                },
            ]
        },
    }

    result = parse_convertible_bond_payload(payload, date(2026, 8, 6))

    assert [item.bond_code for item in result] == ["111026", "123281"]


def test_fetch_convertible_bond_subscriptions_uses_date_filter(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            captured["status_checked"] = True

        def json(self) -> object:
            return {"success": True, "result": {"data": []}}

    def fake_get(url: str, **kwargs: object) -> FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(client.requests, "get", fake_get)

    result = fetch_convertible_bond_subscriptions(date(2026, 8, 6), timeout=7)

    assert result == []
    assert captured["url"] == "https://datacenter-web.eastmoney.com/api/data/v1/get"
    assert captured["params"] == {
        "reportName": "RPT_BOND_CB_LIST",
        "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,PUBLIC_START_DATE,CORRECODE",
        "pageNumber": 1,
        "pageSize": 100,
        "filter": "(PUBLIC_START_DATE='2026-08-06')",
    }
    assert captured["timeout"] == 7
    assert captured["status_checked"] is True
