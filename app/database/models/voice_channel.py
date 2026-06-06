from sqlalchemy import BigInteger, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.models.base import Base


class VoiceChannel(Base):
    __tablename__ = "voice_channels"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    server_id: Mapped[int] = mapped_column(BigInteger, index=True)
    main: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
