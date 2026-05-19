"""Orchestrator schemas."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlanConfig:
    plan: str = "daily"  # daily | guangdong | national | retry_failed
    max_sources: int = 10
    max_keywords: int = 8
    sleep_seconds: float = 2.0
    no_wecom: bool = False
    use_vllm: bool = False


@dataclass
class SourcePlan:
    source_name: str
    source_url: str = ""
    province: str | None = None
    city: str | None = None
    parser_name: str | None = None
    parser_status: str = "parser_ready"
    source_level: str = "national"
    source_type: str = "bid"
    requires_browser: bool = False


@dataclass
class SourceResult:
    source_name: str
    status: str = "pending"  # pending|running|success|no_match|blocked|failed|skipped
    blocked_reason: str | None = None
    total_found: int = 0
    total_saved: int = 0
    error_message: str | None = None
    duration_ms: int = 0


@dataclass
class RunReport:
    run_id: int = 0
    plan: str = "daily"
    status: str = "running"
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0
    keywords: list[str] = field(default_factory=list)
    sources_selected: int = 0
    sources_success: int = 0
    sources_no_match: int = 0
    sources_blocked: int = 0
    sources_failed: int = 0
    total_found: int = 0
    total_saved: int = 0
    total_duplicates: int = 0
    attachments_found: int = 0
    attachments_parsed: int = 0
    ai_extracted: int = 0
    review_tasks_created: int = 0
    notification_channel: str = ""
    notification_status: str = "skipped"
    report_path: str = ""
    errors: list[str] = field(default_factory=list)
    source_results: list[SourceResult] = field(default_factory=list)
