"""reserved removed acquisition migration

Revision ID: 202605180006
Revises: 202605180005
Create Date: 2026-05-18 22:30:00
"""
from typing import Sequence, Union


revision: str = "202605180006"
down_revision: Union[str, None] = "202605180005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
