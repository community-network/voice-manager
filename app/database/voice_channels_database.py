from __future__ import annotations

import logging
import time
from pathlib import Path

import psycopg2
from alembic import command
from alembic.config import Config as AlembicConfig
from psycopg2 import OperationalError
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import DbConfig

logger = logging.getLogger("migrations")


class VoiceChannelsDatabase:
    _MIGRATION_LOCK_KEY = 914382605
    _CONNECT_RETRIES = 30
    _CONNECT_RETRY_DELAY_SECONDS = 2

    def __init__(self, config: DbConfig):
        self.config = config
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

    def run_startup_migrations(self) -> None:
        with self._connect_with_retry() as connection:
            with connection.cursor() as cursor:
                logger.info("Waiting for migration lock")
                cursor.execute("SELECT pg_advisory_lock(%s)", (self._MIGRATION_LOCK_KEY,))

            try:
                logger.info("Applying database migrations")
                command.upgrade(self._build_alembic_config(), "head")
            finally:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_advisory_unlock(%s)", (self._MIGRATION_LOCK_KEY,)
                    )

    async def init_db(self) -> None:
        self.engine = create_async_engine(self.dburl)

    async def close_async(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()

    def create_session(self) -> AsyncSession:
        session_maker = async_sessionmaker(bind=self.engine, expire_on_commit=False)
        return session_maker()

    def _connect_with_retry(self):
        last_error: OperationalError | None = None
        for attempt in range(1, self._CONNECT_RETRIES + 1):
            try:
                connection = psycopg2.connect(
                    dbname=self.config.postgres_db,
                    user=self.config.postgres_user,
                    password=self.config.postgres_password,
                    host=self.config.db_host,
                    port=self.config.db_port,
                    connect_timeout=5,
                )
                connection.autocommit = True
                return connection
            except OperationalError as error:
                last_error = error
                if attempt == self._CONNECT_RETRIES:
                    break
                logger.info(
                    "Database not ready for migrations yet (%s/%s): %s",
                    attempt,
                    self._CONNECT_RETRIES,
                    error,
                )
                time.sleep(self._CONNECT_RETRY_DELAY_SECONDS)

        assert last_error is not None
        raise last_error

    @staticmethod
    def _build_alembic_config() -> AlembicConfig:
        root_dir = Path(__file__).resolve().parents[2]
        alembic_config = AlembicConfig(str(root_dir / "alembic.ini"))
        alembic_config.set_main_option(
            "script_location",
            str(root_dir / "app" / "database" / "migrations"),
        )
        alembic_config.set_main_option("prepend_sys_path", str(root_dir))
        return alembic_config
