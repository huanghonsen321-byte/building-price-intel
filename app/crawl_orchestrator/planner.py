"""Planner — select sources and keywords for each run plan."""

from __future__ import annotations

from app.crawl_orchestrator.schemas import PlanConfig, SourcePlan
from app.source_library.registry import get_sources, load_source_library
from app.source_library.schemas import SourceQuery

DEFAULT_DAILY_KEYWORDS = [
    "脚手架", "盘扣", "钢管", "钢管扣件租赁",
    "周转材料租赁", "模板脚手架", "废钢", "螺纹钢",
]

GUANGDONG_KEYWORDS = [
    "脚手架", "盘扣式脚手架", "扣件式脚手架",
    "钢管脚手架", "模板脚手架", "钢管扣件租赁",
    "周转材料租赁", "附着式升降脚手架",
]

NATIONAL_KEYWORDS = [
    "脚手架", "盘扣", "周转材料租赁",
    "模板脚手架", "钢管租赁",
]


def plan_daily(config: PlanConfig) -> tuple[list[SourcePlan], list[str]]:
    """Select enabled + parser_ready sources: national + guangdong + price."""
    load_source_library()

    nat = get_sources(SourceQuery(
        source_level="national", enabled=True, parser_status="parser_ready",
        limit=config.max_sources,
    ))
    gd = get_sources(SourceQuery(
        province="广东", enabled=True, parser_status="parser_ready",
        limit=config.max_sources,
    ))
    price = get_sources(SourceQuery(
        source_type="price", enabled=True, parser_status="parser_ready",
        limit=config.max_sources,
    ))

    seen: set[str] = set()
    sources: list[SourcePlan] = []
    for src in (nat + gd + price):
        if src.name in seen:
            continue
        seen.add(src.name)
        sources.append(SourcePlan(
            source_name=src.name,
            source_url=src.url,
            province=src.province,
            city=src.city,
            parser_name=src.parser_name,
            parser_status=src.parser_status,
            source_level=src.source_level,
            source_type=src.source_type,
            requires_browser=src.requires_browser,
        ))
        if len(sources) >= config.max_sources:
            break

    keywords = DEFAULT_DAILY_KEYWORDS[:config.max_keywords]
    return sources, keywords


def plan_guangdong(config: PlanConfig) -> tuple[list[SourcePlan], list[str]]:
    """Select Guangdong province + city parser_ready sources only."""
    load_source_library()

    gd = get_sources(SourceQuery(
        province="广东", enabled=True, parser_status="parser_ready",
        limit=config.max_sources,
    ))

    sources: list[SourcePlan] = []
    for src in gd:
        sources.append(SourcePlan(
            source_name=src.name,
            source_url=src.url,
            province=src.province,
            city=src.city,
            parser_name=src.parser_name,
            parser_status=src.parser_status,
            source_level=src.source_level,
            source_type=src.source_type,
            requires_browser=src.requires_browser,
        ))

    keywords = GUANGDONG_KEYWORDS[:config.max_keywords]
    return sources, keywords


def plan_national(config: PlanConfig) -> tuple[list[SourcePlan], list[str]]:
    """Select national bid sources only."""
    load_source_library()

    nat = get_sources(SourceQuery(
        source_level="national", source_type="bid",
        enabled=True, parser_status="parser_ready",
        limit=config.max_sources,
    ))

    sources: list[SourcePlan] = []
    for src in nat:
        sources.append(SourcePlan(
            source_name=src.name,
            source_url=src.url,
            province=src.province,
            city=src.city,
            parser_name=src.parser_name,
            parser_status=src.parser_status,
            source_level=src.source_level,
            source_type=src.source_type,
            requires_browser=src.requires_browser,
        ))

    keywords = NATIONAL_KEYWORDS[:config.max_keywords]
    return sources, keywords


def plan_retry_failed(config: PlanConfig) -> tuple[list[SourcePlan], list[str]]:
    """Select recently failed sources, skip permanent blocks."""
    from sqlalchemy import select
    from app.core.database import SessionLocal

    with SessionLocal() as db:
        from app.models.crawl import CrawlSource
        sources_rows = list(db.scalars(
            select(CrawlSource).where(
                CrawlSource.last_blocked_reason.is_not(None),
                CrawlSource.enabled.is_(True),
            ).limit(config.max_sources)
        ))

    sources: list[SourcePlan] = []
    skip_reasons = {"blocked_403", "captcha_required", "login_required", "paid_content"}
    for src in sources_rows:
        if src.last_blocked_reason in skip_reasons:
            continue
        sources.append(SourcePlan(
            source_name=src.name,
            source_url=src.base_url,
            parser_name=None,
            parser_status=src.parser_status or "unknown",
            source_level="national",
            source_type=src.source_type or "bid",
        ))

    keywords = DEFAULT_DAILY_KEYWORDS[:config.max_keywords]
    return sources, keywords


PLANNERS = {
    "daily": plan_daily,
    "guangdong": plan_guangdong,
    "national": plan_national,
    "retry_failed": plan_retry_failed,
    "retry-failed": plan_retry_failed,
}


def plan(config: PlanConfig) -> tuple[list[SourcePlan], list[str]]:
    """Dispatch to the appropriate planner."""
    planner_fn = PLANNERS.get(config.plan)
    if planner_fn is None:
        raise ValueError(f"Unknown plan: {config.plan}. Available: {list(PLANNERS.keys())}")
    return planner_fn(config)
