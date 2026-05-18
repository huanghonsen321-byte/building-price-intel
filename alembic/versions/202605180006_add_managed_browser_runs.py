"""add managed_browser_runs table

Revision ID: 202605180006
Revises: 202605180005
Create Date: 2026-05-18 18:55:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605180006"
down_revision: Union[str, None] = "202605180005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "managed_browser_runs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("source_name", sa.String(length=128), nullable=False, index=True),
        sa.Column("keyword", sa.String(length=128), nullable=False, index=True),
        sa.Column("mode", sa.String(length=32), server_default="dry-run", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visited_urls", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("downloaded_files", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("records_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attachments_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blocked_reason", sa.String(length=128), nullable=True, index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("managed_browser_runs")
