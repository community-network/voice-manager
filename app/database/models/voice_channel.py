from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models.base import Base


class VoiceChannel(Base):
    __tablename__ = "voice_channels"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[int] = mapped_column(BigInteger, index=True)
    parent_channel_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, index=True
    )
