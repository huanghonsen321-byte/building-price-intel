"""add ai extraction evidence fields

Revision ID: 202605180002
Revises: 202605180001
Create Date: 2026-05-18 10:50:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202605180002"
down_revision: Union[str, None] = "202605180001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scaffold_bid_cases", sa.Column("missing_fields", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("scaffold_bid_cases", sa.Column("raw_evidence_snippets", sa.JSON(), server_default="[]", nullable=False))


def downgrade() -> None:
    op.drop_column("scaffold_bid_cases", "raw_evidence_snippets")
    op.drop_column("scaffold_bid_cases", "missing_fields")
