"""replace voice channel main flag with parent channel id

Revision ID: 202606060002
Revises: 202606060001
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202606060002"
down_revision: Union[str, Sequence[str], None] = "202606060001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_channels",
        sa.Column("parent_channel_id", sa.BigInteger(), nullable=True),
    )
    op.execute(
        """
        WITH single_parent_servers AS (
            SELECT server_id, min(id) AS parent_channel_id
            FROM voice_channels
            WHERE main = true
            GROUP BY server_id
            HAVING count(*) = 1
        )
        UPDATE voice_channels AS voice_channel
        SET parent_channel_id = CASE
            WHEN voice_channel.main = true THEN voice_channel.id
            ELSE COALESCE(single_parent_servers.parent_channel_id, voice_channel.id)
        END
        FROM single_parent_servers
        WHERE voice_channel.server_id = single_parent_servers.server_id
        """
    )
    op.execute(
        """
        UPDATE voice_channels
        SET parent_channel_id = id
        WHERE parent_channel_id IS NULL
        """
    )
    op.alter_column("voice_channels", "parent_channel_id", nullable=False)
    op.create_index(
        "ix_voice_channels_parent_channel_id",
        "voice_channels",
        ["parent_channel_id"],
    )
    op.drop_column("voice_channels", "main")


def downgrade() -> None:
    op.add_column(
        "voice_channels",
        sa.Column("main", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute("UPDATE voice_channels SET main = true WHERE id = parent_channel_id")
    op.drop_index("ix_voice_channels_parent_channel_id", table_name="voice_channels")
    op.drop_column("voice_channels", "parent_channel_id")