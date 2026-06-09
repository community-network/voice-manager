from __future__ import annotations

import asyncio
import logging

from app.bot import VoiceBot, create_bot

logger = logging.getLogger("bot")


async def run_bot(bot: VoiceBot) -> None:
    try:
        async with bot:
            logger.info("Starting Discord bot")
            await bot.start(bot.config.bot.discord_bot_token)
    finally:
        await bot.db.close_async()


def main() -> None:
    bot = create_bot()
    try:
        bot.db.run_startup_migrations()
        asyncio.run(run_bot(bot))
    except Exception:
        logger.exception("Application startup failed")
        raise


if __name__ == "__main__":
    main()
