from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import DbConfig
from app.database.models.base import Base


class VoiceChannelsDatabase:
    def __init__(self, config: DbConfig):
        uri = URL.create(
            drivername="postgresql+asyncpg",
            username=config.postgres_user,
            password=config.postgres_password,
            host=config.db_host,
            port=config.db_port,
            database=config.postgres_db,
        )
        self.dburl = uri.render_as_string(hide_password=False)
        self.engine = None

    async def init_db(self) -> None:
        self.engine = create_async_engine(self.dburl)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close_async(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()

    def create_session(self) -> AsyncSession:
        session_maker = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        return session_maker()
