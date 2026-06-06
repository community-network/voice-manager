from dataclasses import dataclass
from environs import Env


@dataclass(slots=True)
class DiscordBotConfig:
    discord_bot_token: str

    @staticmethod
    def from_env(env: Env) -> "DiscordBotConfig":
        return DiscordBotConfig(discord_bot_token=env.str("DISCORD_BOT_TOKEN"))


@dataclass(slots=True)
class DbConfig:
    postgres_user: str
    postgres_password: str
    postgres_db: str
    db_host: str
    db_port: int = 5432

    @staticmethod
    def from_env(env: Env) -> "DbConfig":
        db_host = env.str("POSTGRES_HOST", None)
        db_port = env.int("POSTGRES_PORT", None)
        return DbConfig(
            postgres_user=env.str("POSTGRES_USER"),
            postgres_password=env.str("POSTGRES_PASSWORD"),
            postgres_db=env.str("POSTGRES_DB"),
            db_host=db_host or env.str("DB_HOST"),
            db_port=db_port if db_port is not None else env.int("DB_PORT", 5432),
        )


@dataclass(slots=True)
class Config:
    bot: DiscordBotConfig
    db: DbConfig


def load_config() -> Config:
    env = Env()
    env.read_env()

    return Config(
        bot=DiscordBotConfig.from_env(env),
        db=DbConfig.from_env(env),
    )
