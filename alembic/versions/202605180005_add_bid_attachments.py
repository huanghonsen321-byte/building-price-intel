"""add bid_attachments table

Revision ID: 202605180005
Revises: 202605180004
Create Date: 2026-05-18 17:40:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605180005"
down_revision: Union[str, None] = "202605180004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bid_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("raw_document_id", sa.Integer(), sa.ForeignKey("bid_raw_documents.id"), nullable=True, index=True),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("parse_status", sa.String(length=32), server_default="pending", nullable=False, index=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("bid_attachments")
