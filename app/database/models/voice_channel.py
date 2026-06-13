from typing import Optional

from sqlalchemy import BigInteger, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models.base import Base
from sqlalchemy.sql import expression


class VoiceChannel(Base):
    __tablename__ = "voice_channels"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[int] = mapped_column(BigInteger, index=True)
    parent_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )
    owner_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)
    manage_permissions: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=expression.true(),
    )
