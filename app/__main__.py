from __future__ import annotations

import asyncio
import logging

from app.bot import VoiceBot, create_bot

logger = logging.getLogger("bot")


async def run_bot(bot: VoiceBot) -> None:
    async with bot:
        await bot.start(bot.config.bot.discord_bot_token)


def main() -> None:
    bot = create_bot()
    bot.db.run_startup_migrations()
    try:
        asyncio.run(run_bot(bot))
    except Exception:
        logger.exception("Application startup failed")
        raise
    finally:
        asyncio.run(bot.db.close_async())


if __name__ == "__main__":
    main()
