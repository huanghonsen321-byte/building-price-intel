"""add compliant source registry fields

Revision ID: 202605180004
Revises: 202605180003
Create Date: 2026-05-18 15:50:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605180004"
down_revision: Union[str, None] = "202605180003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("crawl_sources", sa.Column("reliability_score", sa.Float(), server_default="0", nullable=False))
    op.add_column("crawl_sources", sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crawl_sources", sa.Column("last_blocked_reason", sa.String(length=64), nullable=True))
    op.add_column("crawl_sources", sa.Column("parser_status", sa.String(length=64), server_default="unknown", nullable=False))
    op.add_column("crawl_sources", sa.Column("requires_browser", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("crawl_sources", sa.Column("requires_manual_review", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("crawl_sources", sa.Column("public_page_reachable", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("crawl_sources", sa.Column("public_api_found", sa.Boolean(), server_default="false", nullable=False))
    op.create_index(op.f("ix_crawl_sources_last_blocked_reason"), "crawl_sources", ["last_blocked_reason"], unique=False)
    op.create_index(op.f("ix_crawl_sources_parser_status"), "crawl_sources", ["parser_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_crawl_sources_parser_status"), table_name="crawl_sources")
    op.drop_index(op.f("ix_crawl_sources_last_blocked_reason"), table_name="crawl_sources")
    op.drop_column("crawl_sources", "public_api_found")
    op.drop_column("crawl_sources", "public_page_reachable")
    op.drop_column("crawl_sources", "requires_manual_review")
    op.drop_column("crawl_sources", "requires_browser")
    op.drop_column("crawl_sources", "parser_status")
    op.drop_column("crawl_sources", "last_blocked_reason")
    op.drop_column("crawl_sources", "last_success_at")
    op.drop_column("crawl_sources", "reliability_score")
