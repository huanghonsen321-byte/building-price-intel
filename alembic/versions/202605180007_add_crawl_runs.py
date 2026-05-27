"""reserved removed run-history migration

Revision ID: 202605180007
Revises: 202605180006
Create Date: 2026-05-18 23:00:00
"""
from typing import Sequence, Union


revision: str = "202605180007"
down_revision: Union[str, None] = "202605180006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
