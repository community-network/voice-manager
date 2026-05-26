"""User management"""

import logging
import discord
from discord.ext import commands
from discord import app_commands

from bot import VoiceBot
from utils.voice_channels import (
    add_voice_channel,
    get_voice_channel,
    get_voice_channels,
    remove_voice_channel,
)


class Admin(commands.Cog):
    def __init__(self, bot: VoiceBot):
        self.bot = bot
        self.logger = logging.getLogger("admin")

    group = app_commands.Group(
        name="admin", description="Commands meant only for admins"
    )

    voice_group = app_commands.Group(
        name="voice-channels", description="Manage voice channels", parent=group
    )

    async def channel_name_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[int]]:
        """Autocomplete channel names"""
        async with self.bot.db.create_session() as session:
            if interaction.guild is None:
                return []
            voice_channel_ids = await get_voice_channels(session, interaction.guild.id)
            return [
                app_commands.Choice(name=channel.name, value=channel.id)
                for channel in interaction.guild.voice_channels
                if channel.id in voice_channel_ids
                and channel.name.lower().startswith(current.lower())
            ]

    @voice_group.command(name="add", description="Add a tracked channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_tracked_channel(
        self, interaction: discord.Interaction, channel: discord.VoiceChannel
    ) -> None:
        """Add a tracked channel"""
        await interaction.response.defer()
        if interaction.guild_id is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            existing_channel = await get_voice_channel(
                session, interaction.guild_id, channel_id=channel.id
            )
            if existing_channel is not None:
                await interaction.followup.send(
                    "Channel is already added", ephemeral=True
                )
                return

            await add_voice_channel(session, interaction.guild_id, channel.id)
            await interaction.followup.send("Added the voice channel", ephemeral=True)

    @voice_group.command(name="list", description="Add a tracked channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def list_tracked_channels(self, interaction: discord.Interaction) -> None:
        """List a tracked channel"""
        await interaction.response.defer()
        if interaction.guild_id is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            description = ""
            channel_ids = await get_voice_channels(session, interaction.guild_id)
            for channel_id in channel_ids:
                description += f"{channel_id}\n"

            if len(channel_ids) <= 0:
                await interaction.followup.send(
                    "No voice channels are tracked", ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Current tracked voice channels:", description=description
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @voice_group.command(name="remove", description="Remove a tracked channel")
    @app_commands.guild_only()
    @app_commands.autocomplete(channel=channel_name_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_tracked_channel(
        self, interaction: discord.Interaction, channel: int
    ) -> None:
        """Remove a tracked channel"""
        await interaction.response.defer()
        if interaction.guild_id is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            existing_channel = await get_voice_channel(
                session, interaction.guild_id, channel_id=channel
            )
            if existing_channel is not None:
                await remove_voice_channel(session, interaction.guild_id, channel)

                await interaction.followup.send(
                    "Removed the tracking of voice channel", ephemeral=True
                )
                return

            await interaction.followup.send(
                "Voice channel wasn't tracked", ephemeral=True
            )


async def setup(bot: VoiceBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(Admin(bot))
