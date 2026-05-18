import json
from decimal import Decimal
from typing import Any

import httpx

from app.ai.prompts import SCAFFOLD_EXTRACT_SYSTEM_PROMPT, SCAFFOLD_EXTRACT_USER_PROMPT
from app.core.config import get_settings


def _empty_result(text: str, reason: str) -> dict[str, Any]:
    return {
        "is_scaffold_related": any(keyword in text for keyword in ["脚手架", "盘扣", "扣件式", "钢管", "爬架", "周转材料"]),
        "announcement_type": None,
        "project_name": None,
        "province": None,
        "city": None,
        "district": None,
        "buyer": None,
        "agency": None,
        "winner": None,
        "bid_amount": None,
        "publish_date": None,
        "scaffold_type": None,
        "procurement_type": None,
        "service_scope": None,
        "duration_text": None,
        "quantity_text": None,
        "area_m2": None,
        "tonnage": None,
        "rental_days": None,
        "pricing_method": None,
        "unit_price_candidates": [],
        "ai_summary": f"AI 抽取不可用：{reason}",
        "missing_fields": ["model_response"],
        "confidence": 0.0,
    }


def _coerce_numbers(data: dict[str, Any]) -> dict[str, Any]:
    for key in ["bid_amount", "area_m2", "tonnage"]:
        if data.get(key) in ("", None):
            data[key] = None
        else:
            try:
                data[key] = Decimal(str(data[key]))
            except Exception:
                data[key] = None
    if data.get("rental_days") not in ("", None):
        try:
            data["rental_days"] = int(data["rental_days"])
        except Exception:
            data["rental_days"] = None
    return data


async def extract_scaffold_bid(text: str) -> dict[str, Any]:
    settings = get_settings()
    payload = {
        "model": settings.vllm_model,
        "messages": [
            {"role": "system", "content": SCAFFOLD_EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": SCAFFOLD_EXTRACT_USER_PROMPT.format(text=text[:12000])},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    try:
        async with httpx.AsyncClient(base_url=settings.vllm_base_url, timeout=8.0) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            return _coerce_numbers({**_empty_result(text, "missing defaults"), **data})
    except Exception as exc:
        return _empty_result(text, str(exc))
