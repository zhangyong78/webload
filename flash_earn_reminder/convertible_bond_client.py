from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import date

import requests

from flash_earn_reminder.models import ConvertibleBondSubscription


DATA_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
LOGGER = logging.getLogger(__name__)


def fetch_convertible_bond_subscriptions(
    subscription_date: date,
    *,
    timeout: int = 20,
) -> list[ConvertibleBondSubscription]:
    response = requests.get(
        DATA_URL,
        params={
            "reportName": "RPT_BOND_CB_LIST",
            "columns": "SECURITY_CODE,SECURITY_NAME_ABBR,PUBLIC_START_DATE,CORRECODE",
            "pageNumber": 1,
            "pageSize": 100,
            "filter": f"(PUBLIC_START_DATE='{subscription_date.isoformat()}')",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_convertible_bond_payload(response.json(), subscription_date)


def parse_convertible_bond_payload(
    payload: object,
    subscription_date: date,
) -> list[ConvertibleBondSubscription]:
    if not isinstance(payload, Mapping):
        raise ValueError("可转债接口返回失败：响应不是对象。")
    if payload.get("success") is not True:
        if str(payload.get("code", "")) == "9201":
            return []
        code = _clean_text(payload.get("code")) or "未知"
        message = _clean_text(payload.get("message")) or "未知错误"
        raise ValueError(f"可转债接口返回失败（code={code}）：{message}")
    result = payload.get("result")
    if not isinstance(result, Mapping) or not isinstance(result.get("data"), list):
        raise ValueError("可转债接口数据结构异常。")

    subscriptions: list[ConvertibleBondSubscription] = []
    for row in result["data"]:
        if not isinstance(row, Mapping):
            LOGGER.warning("忽略无效的可转债记录：记录不是对象。")
            continue
        name = _clean_text(row.get("SECURITY_NAME_ABBR"))
        bond_code = _clean_text(row.get("SECURITY_CODE"))
        subscription_code = _clean_text(row.get("CORRECODE"))
        raw_date = _clean_text(row.get("PUBLIC_START_DATE"))
        if not (name and bond_code and subscription_code and raw_date):
            LOGGER.warning("忽略缺少必填字段的可转债记录：%s", row)
            continue
        try:
            parsed_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            LOGGER.warning("忽略申购日期无效的可转债记录：%s", row)
            continue
        if parsed_date != subscription_date:
            continue
        subscriptions.append(
            ConvertibleBondSubscription(
                name=name,
                bond_code=bond_code,
                subscription_code=subscription_code,
                subscription_date=parsed_date,
            )
        )
    return sorted(subscriptions, key=lambda item: item.bond_code)


def _clean_text(value: object) -> str:
    return str(value or "").strip()
