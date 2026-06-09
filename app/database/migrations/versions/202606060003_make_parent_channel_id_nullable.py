"""make parent channel id nullable for parent channels

Revision ID: 202606060003
Revises: 202606060002
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202606060003"
down_revision: Union[str, Sequence[str], None] = "202606060002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "voice_channels",
        "parent_channel_id",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.execute(
        """
        UPDATE voice_channels
        SET parent_channel_id = NULL
        WHERE parent_channel_id = id
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE voice_channels
        SET parent_channel_id = id
        WHERE parent_channel_id IS NULL
        """
    )
    op.alter_column(
        "voice_channels",
        "parent_channel_id",
        existing_type=sa.BigInteger(),
        nullable=False,
    )