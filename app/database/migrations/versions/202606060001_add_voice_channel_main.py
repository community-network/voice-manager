"""add voice channel main flag

Revision ID: 202606060001
Revises:
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202606060001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = inspector.get_table_names()

    if "voice_channels" not in table_names:
        op.create_table(
            "voice_channels",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("server_id", sa.BigInteger(), nullable=False),
            sa.Column("main", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_voice_channels_server_id", "voice_channels", ["server_id"])
        return

    column_names = {column["name"] for column in inspector.get_columns("voice_channels")}
    if "main" not in column_names:
        op.add_column(
            "voice_channels",
            sa.Column("main", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        )


def downgrade() -> None:
    op.execute("ALTER TABLE voice_channels DROP COLUMN IF EXISTS main")