"""Discord bot setup and voice-channel event registration."""

from __future__ import annotations

import logging
import os

import discord
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import load_config
from app.database.voice_channels_database import VoiceChannelsDatabase
from app.logger import setup_logger
from app.services.voice_channels import (
    add_voice_channel,
    get_voice_channel,
    get_voice_channels,
    remove_voice_channel,
)

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


async def get_channels_in_db(
    session: AsyncSession,
    member: discord.Member,
    voice_channels: list[discord.VoiceChannel],
):
    db_voice_channels = await get_voice_channels(session, member.guild.id)
    return [channel for channel in voice_channels if channel.id in db_voice_channels]


async def on_voice_channel_join(
    session: AsyncSession,
    member: discord.Member,
    channel: discord.abc.GuildChannel,
):
    db_channel = await get_voice_channel(session, member.guild.id, channel.id)
    if db_channel is None or channel.category is None:
        return

    category = channel.category
    channels_in_db = await get_channels_in_db(
        session, member, channel.guild.voice_channels
    )

    total_empty_channels = 0
    for channel in channels_in_db:
        if len(channel.members) == 0:
            total_empty_channels += 1

    if total_empty_channels == 0:
        new_channel = await category.create_voice_channel(
            channel.name, position=channel.position
        )
        await new_channel.edit(overwrites=channel.overwrites)
        await add_voice_channel(session, member.guild.id, new_channel.id)


async def on_voice_channel_leave(
    session: AsyncSession,
    member: discord.Member,
    channel: discord.abc.GuildChannel,
):
    db_channel = await get_voice_channel(session, member.guild.id, channel.id)
    if db_channel is None:
        return

    channels_in_db = await get_channels_in_db(
        session, member, channel.guild.voice_channels
    )
    empty_channels = 0
    for channel in reversed(channels_in_db):
        total_users = len(channel.members)
        if empty_channels > 0 and total_users <= 0:
            await channel.delete()
            await remove_voice_channel(session, member.guild.id, channel.id)
        elif len(channel.members) <= 0:
            empty_channels += 1


def register_bot_events(bot: VoiceBot) -> None:
    @bot.event
    async def on_voice_state_update(
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        async with bot.db.create_session() as session:
            if member.guild.id is None:
                return
            if before.channel is None and after.channel is not None:  # join
                await on_voice_channel_join(session, member, after.channel)

            if before.channel is not None and after.channel is None:  # leave
                await on_voice_channel_leave(session, member, before.channel)

            if (
                before.channel is not None
                and after.channel is not None
                and before.channel.id != after.channel.id
            ):
                await on_voice_channel_leave(session, member, before.channel)
                await on_voice_channel_join(session, member, after.channel)

    @bot.event
    async def on_guild_join(guild: discord.Guild) -> None:
        logger.info('Joined guild "%s"', guild.name)

    @bot.event
    async def on_command_error(ctx, error) -> None:
        """Ignore expected command errors and report permission issues."""
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
