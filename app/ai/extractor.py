import asyncio
import json
import logging
import re
from decimal import Decimal
from typing import Any

import httpx

from app.ai.prompts import SCAFFOLD_EXTRACT_SYSTEM_PROMPT, SCAFFOLD_EXTRACT_USER_PROMPT
from app.core.config import get_settings

logger = logging.getLogger(__name__)

SCAFFOLD_KEYWORDS = ["脚手架", "盘扣", "扣件式", "钢管", "爬架", "周转材料"]
REQUIRED_FIELDS = [
    "project_name",
    "province",
    "city",
    "buyer",
    "winner",
    "bid_amount",
    "area_m2",
    "tonnage",
    "duration_text",
]


def _find_first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.S)
        if match:
            value = match.group(1).strip(" ：:，,。；;\n\t")
            if value:
                return value
    return None


def _amount_to_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    raw = value.replace(",", "").replace("，", "")
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(亿元|万元|元)?", raw)
    if not match:
        return None
    amount = Decimal(match.group(1))
    unit = match.group(2) or "元"
    if unit == "亿元":
        amount *= Decimal("100000000")
    elif unit == "万元":
        amount *= Decimal("10000")
    return amount.quantize(Decimal("0.01"))


def _decimal_from_text(patterns: list[str], text: str) -> Decimal | None:
    value = _find_first(patterns, text)
    if not value:
        return None
    try:
        return Decimal(value.replace(",", "").replace("，", ""))
    except Exception:
        return None


def _evidence(text: str, terms: list[str], max_items: int = 5) -> list[str]:
    snippets: list[str] = []
    compact = re.sub(r"\s+", " ", text)
    for term in terms:
        index = compact.find(term)
        if index >= 0:
            start = max(0, index - 45)
            end = min(len(compact), index + 95)
            snippet = compact[start:end].strip()
            if snippet and snippet not in snippets:
                snippets.append(snippet)
        if len(snippets) >= max_items:
            break
    return snippets


def _empty_result(text: str, reason: str, source_url: str | None = None) -> dict[str, Any]:
    is_related = any(keyword in text for keyword in SCAFFOLD_KEYWORDS)
    return {
        "is_scaffold_related": is_related,
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
        "source_url": source_url,
        "ai_summary": f"AI 抽取不可用：{reason}",
        "missing_fields": REQUIRED_FIELDS.copy(),
        "raw_evidence_snippets": _evidence(text, SCAFFOLD_KEYWORDS) or [text[:160]],
        "confidence": 0.0,
        "extraction_confidence": 0.0,
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
    confidence = data.get("extraction_confidence", data.get("confidence", 0))
    try:
        confidence_decimal = Decimal(str(confidence))
    except Exception:
        confidence_decimal = Decimal("0.0")
    data["confidence"] = confidence_decimal
    data["extraction_confidence"] = confidence_decimal
    if not data.get("missing_fields"):
        data["missing_fields"] = [field for field in REQUIRED_FIELDS if data.get(field) in (None, "", [])]
    if not data.get("raw_evidence_snippets"):
        data["raw_evidence_snippets"] = []
    return data


def _infer_region(text: str) -> tuple[str | None, str | None, str | None]:
    province = _find_first([r"(广东省|广东|广西壮族自治区|广西|湖南省|湖南|湖北省|湖北|江西省|江西|福建省|福建|海南省|海南)"], text)
    if province == "广东":
        province = "广东省"
    city = _find_first([r"(广州市|深圳市|佛山市|东莞市|中山市|珠海市|惠州市|江门市|肇庆市|清远市|韶关市|湛江市|茂名市|汕头市|汕尾市|揭阳市|潮州市|梅州市|河源市|云浮市|阳江市)"], text)
    district = _find_first([r"(白云区|天河区|越秀区|海珠区|番禺区|黄埔区|南沙区|花都区|增城区|从化区|顺德区|南海区|禅城区|三水区|高明区)"], text)
    return province, city, district


def rule_based_extract_scaffold_bid(text: str, source_url: str | None = None, reason: str = "offline rule fallback") -> dict[str, Any]:
    result = _empty_result(text, reason, source_url=source_url)
    province, city, district = _infer_region(text)
    amount_text = _find_first([r"(?:中标金额|成交金额|投标报价|合同金额|金额)[：:]?\s*(?:人民币)?\s*([0-9.,，]+\s*(?:亿元|万元|元))"], text)
    project_name = _find_first([
        r"(?:项目名称|工程名称)[：:]\s*([^\n。；;]+)",
        r"([^。\n]{6,80}?(?:脚手架|盘扣|周转材料)(?:租赁|采购|专业分包|工程)?)\s*(?:中标公告|招标公告|采购公告|成交公告)",
    ], text)
    publish_date = _find_first([r"(?:公告发布日期|发布日期|发布时间)[：:]?\s*(\d{4}[-年/]\d{1,2}[-月/]\d{1,2})"], text)
    if publish_date:
        publish_date = publish_date.replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-")
    rental_days_text = _find_first([r"(?:租期|工期|服务期)[约为\s：:]*(\d+)\s*天"], text)

    result.update(
        {
            "announcement_type": "中标公告" if "中标" in text or "成交" in text else ("招标公告" if "招标" in text else None),
            "project_name": project_name,
            "province": province,
            "city": city,
            "district": district,
            "buyer": _find_first([r"(?:采购人|招标人|建设单位)[：:]\s*([^，,。；;\n]+)"], text),
            "agency": _find_first([r"(?:代理机构|招标代理)[：:]\s*([^，,。；;\n]+)"], text),
            "winner": _find_first([r"(?:中标人|成交供应商|供应商)[：:]\s*([^，,。；;\n]+)"], text),
            "bid_amount": _amount_to_decimal(amount_text),
            "publish_date": publish_date,
            "scaffold_type": "盘扣式脚手架" if "盘扣" in text else ("扣件式脚手架" if "扣件" in text else ("脚手架" if "脚手架" in text else None)),
            "procurement_type": "租赁" if "租赁" in text else ("包工包料" if "包工包料" in text else ("采购" if "采购" in text else None)),
            "service_scope": _find_first([r"(?:服务范围|采购内容|招标范围)[：:]\s*([^\n]+)"], text),
            "duration_text": _find_first([r"((?:租期|工期|服务期)[^，,。；;\n]{1,40})"], text),
            "quantity_text": _find_first([r"((?:约\s*)?\d+(?:\.\d+)?\s*(?:吨|平方米|㎡|m2|天)[^，,。；;\n]{0,30})"], text),
            "area_m2": _decimal_from_text([r"(?:工程面积|建筑面积|面积)约?\s*([0-9.,，]+)\s*(?:平方米|㎡|m2)"], text),
            "tonnage": _decimal_from_text([r"(?:脚手架)?约?\s*([0-9.,，]+)\s*吨"], text),
            "rental_days": int(rental_days_text) if rental_days_text else None,
            "pricing_method": "包工包料综合单价" if "包工包料" in text and "综合单价" in text else ("综合单价" if "综合单价" in text else None),
            "source_url": source_url,
        }
    )
    result["missing_fields"] = [field for field in REQUIRED_FIELDS if result.get(field) in (None, "", [])]
    found = len(REQUIRED_FIELDS) - len(result["missing_fields"])
    related_bonus = Decimal("0.15") if result["is_scaffold_related"] else Decimal("0.0")
    confidence = min(Decimal("0.95"), Decimal(found) / Decimal(len(REQUIRED_FIELDS)) + related_bonus)
    result["confidence"] = confidence.quantize(Decimal("0.01"))
    result["extraction_confidence"] = result["confidence"]
    evidence_terms = [term for term in ["项目", "采购人", "代理", "中标人", "金额", "面积", "吨", "租期", "脚手架", "盘扣"] if term in text]
    result["raw_evidence_snippets"] = _evidence(text, evidence_terms or SCAFFOLD_KEYWORDS)
    result["ai_summary"] = _build_case_summary(result)
    return _coerce_numbers(result)


def _build_case_summary(data: dict[str, Any]) -> str:
    name = data.get("project_name") or "未命名项目"
    region = "".join(part for part in [data.get("province"), data.get("city"), data.get("district")] if part)
    winner = data.get("winner") or "中标人未披露"
    amount = data.get("bid_amount")
    amount_text = f"，金额约 {Decimal(str(amount)) / Decimal('10000'):.2f} 万元" if amount else "，金额未披露"
    return f"{region or '未知地区'}{name}，{winner}{amount_text}。"


async def extract_scaffold_bid(text: str, source_url: str | None = None, use_vllm: bool = True) -> dict[str, Any]:
    if not use_vllm:
        return rule_based_extract_scaffold_bid(text, source_url=source_url)
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
            merged = {**rule_based_extract_scaffold_bid(text, source_url=source_url, reason="missing defaults"), **data}
            if source_url and not merged.get("source_url"):
                merged["source_url"] = source_url
            return _coerce_numbers(merged)
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("vLLM extraction request failed; returning offline fallback", exc_info=exc)
        return rule_based_extract_scaffold_bid(text, source_url=source_url, reason=f"vLLM request failed: {exc}")
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("vLLM extraction response was not valid JSON; returning offline fallback", exc_info=exc)
        return rule_based_extract_scaffold_bid(text, source_url=source_url, reason=f"vLLM JSON parse failed: {exc}")
    except Exception as exc:
        logger.exception("Unexpected vLLM extraction failure; returning offline fallback")
        return rule_based_extract_scaffold_bid(text, source_url=source_url, reason=f"unexpected extraction failure: {exc}")


def extract_scaffold_bid_sync(text: str, source_url: str | None = None, use_vllm: bool = True) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(extract_scaffold_bid(text, source_url=source_url, use_vllm=use_vllm))
    if use_vllm:
        logger.warning("Running event loop detected; using offline extractor instead of blocking vLLM call")
    return rule_based_extract_scaffold_bid(text, source_url=source_url)
