"""add crawl_runs and crawl_run_sources tables

Revision ID: 202605180007
Revises: 202605180006
Create Date: 2026-05-18 23:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605180007"
down_revision: Union[str, None] = "202605180006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("run_type", sa.String(length=32), server_default="daily", nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="running", nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("keywords", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("source_filters", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("total_sources", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_keywords", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_saved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_duplicates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_attachments", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_ai_extracted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_review_tasks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notification_status", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("report_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "crawl_run_sources",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("crawl_run_id", sa.Integer(), nullable=False, index=True),
        sa.Column("source_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("province", sa.String(length=64), nullable=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("parser_name", sa.String(length=128), nullable=True),
        sa.Column("parser_status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False, index=True),
        sa.Column("blocked_reason", sa.String(length=64), nullable=True),
        sa.Column("total_found", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_saved", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("crawl_run_sources")
    op.drop_table("crawl_runs")
