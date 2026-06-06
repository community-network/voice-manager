"""Discord bot setup and voice-channel event registration."""

from __future__ import annotations

import logging
import os

import discord
from discord.ext import commands

from app.config import load_config
from app.database.voice_channels_database import VoiceChannelsDatabase
from app.logger import setup_logger
from app.services.voice_channels import update_voice_channels

env_config = load_config()

logger = logging.getLogger("bot")
setup_logger(logger)


class VoiceBot(commands.AutoShardedBot):
    """Main bot class."""

    def __init__(self, *args, **kwargs):
        self.logger = logger
        self.config = env_config
        self.db = VoiceChannelsDatabase(env_config.db)
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        await self.db.init_db()
        self.remove_command("help")
        await self.load_cogs()
        logger.info("Bot setup finished")

    async def load_cogs(self) -> None:
        cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
        for file_name in os.listdir(cogs_dir):
            if file_name.endswith(".py") and not file_name == "__init__.py":
                cog_name = file_name[:-3]
                await self.load_extension(f"app.cogs.{cog_name}")
                self.logger.info("Loaded cog: %s", cog_name)


def create_bot() -> VoiceBot:
    intents = discord.Intents.default()
    intents.voice_states = True
    bot = VoiceBot(command_prefix="!", intents=intents)
    register_bot_events(bot)
    return bot
def register_bot_events(bot: VoiceBot) -> None:
    @bot.event
    async def on_voice_state_update(
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Handle event when a member joins or leaves a channel"""
        async with bot.db.create_session() as session:
            if member.guild.id is None:
                return
            if before.channel is None and after.channel is not None:  # join
                await update_voice_channels(session, member, after.channel)

            if before.channel is not None and after.channel is None:  # leave
                await update_voice_channels(session, member, before.channel)

            if (
                before.channel is not None
                and after.channel is not None
                and before.channel.id != after.channel.id
            ):
                await update_voice_channels(session, member, before.channel)
                await update_voice_channels(session, member, after.channel)

    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        logger.info('Joined guild "%s"', guild.name)

    @bot.event
    async def on_command_error(ctx, error) -> None:
        """Ignore expected command errors and report permission issues"""
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            return
        if isinstance(error, commands.MissingRole):
            return
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=0xE74C3C, description="Your not allowed to use this command"
            )
            await ctx.send(embed=embed)
            return
        if isinstance(error, commands.NoPrivateMessage):
            embed = discord.Embed(
                color=0xE74C3C,
                description="This command can only be used within a community, not in DM",
            )
            await ctx.send(embed=embed)
            return
        raise error

    @bot.event
    async def on_ready() -> None:
        await bot.tree.sync()
