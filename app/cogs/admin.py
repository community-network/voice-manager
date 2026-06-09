"""User management"""

import logging
import discord
from discord.ext import commands
from discord import app_commands

from app.bot import VoiceBot
from app.services.voice_channels import (
    add_voice_channel,
    get_parent_voice_channel_ids,
    get_voice_channel_ids,
    get_voice_channel,
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
        name="voice-channels", description="Manage parent voice channels", parent=group
    )

    async def channel_name_autocomplete_parents(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete channel names"""
        async with self.bot.db.create_session() as session:
            if interaction.guild is None:
                return []
            voice_channel_ids = await get_parent_voice_channel_ids(
                session, interaction.guild.id
            )
            return [
                app_commands.Choice(name=channel.name, value=str(channel.id))
                for channel in interaction.guild.voice_channels
                if channel.id in voice_channel_ids
                and channel.name.lower().startswith(current.lower())
            ][:25]

    async def channel_name_autocomplete_unmanaged(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete unmanaged channel names"""
        async with self.bot.db.create_session() as session:
            if interaction.guild is None:
                return []
            voice_channel_ids = await get_voice_channel_ids(
                session, interaction.guild.id
            )
            return [
                app_commands.Choice(name=channel.name, value=str(channel.id))
                for channel in interaction.guild.voice_channels
                if channel.id not in voice_channel_ids
                and channel.name.lower().startswith(current.lower())
            ][:25]

    @voice_group.command(name="add", description="Add a tracked channel")
    @app_commands.guild_only()
    @app_commands.autocomplete(channel=channel_name_autocomplete_unmanaged)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_tracked_channel(
        self, interaction: discord.Interaction, channel: str
    ) -> None:
        """Add a tracked channel"""
        await interaction.response.defer()
        if interaction.guild_id is None:
            return  # is already set to guild_only
        try:
            channel_id = int(channel)
        except ValueError:
            await interaction.followup.send("Voice channel wasn't found", ephemeral=True)
            return

        if interaction.guild is None:
            return  # is already set to guild_only
        voice_channel = interaction.guild.get_channel(channel_id)
        if not isinstance(voice_channel, discord.VoiceChannel):
            await interaction.followup.send("Voice channel wasn't found", ephemeral=True)
            return

        async with self.bot.db.create_session() as session:
            existing_channel = await get_voice_channel(
                session, interaction.guild_id, channel_id=channel_id
            )
            if existing_channel is not None:
                await interaction.followup.send(
                    "Channel is already added", ephemeral=True
                )
                return

            await add_voice_channel(session, interaction.guild_id, channel_id)
            await interaction.followup.send("Added the voice channel", ephemeral=True)

    @voice_group.command(name="list", description="List parent channels")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def list_tracked_channels(self, interaction: discord.Interaction) -> None:
        """List parent channels"""
        await interaction.response.defer()
        if interaction.guild_id is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            description = ""
            channel_ids = await get_parent_voice_channel_ids(
                session, interaction.guild_id
            )
            for channel_id in channel_ids:
                description += f"<#{channel_id}>\n"

            if len(channel_ids) <= 0:
                await interaction.followup.send(
                    "No parent channels are tracked", ephemeral=True
                )
                return

            embed = discord.Embed(
                title="Current parent channels:", description=description
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @voice_group.command(name="remove", description="Remove a parent channel")
    @app_commands.guild_only()
    @app_commands.autocomplete(channel=channel_name_autocomplete_parents)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_tracked_channel(
        self, interaction: discord.Interaction, channel: str
    ) -> None:
        """Remove a parent channel"""
        await interaction.response.defer()
        if interaction.guild_id is None:
            return  # is already set to guild_only
        async with self.bot.db.create_session() as session:
            existing_channel = await get_voice_channel(
                session, interaction.guild_id, channel_id=int(channel)
            )
            if existing_channel is not None:
                await remove_voice_channel(session, interaction.guild_id, int(channel))

                await interaction.followup.send(
                    "Removed the parent channel", ephemeral=True
                )
                return

            await interaction.followup.send(
                "Parent channel wasn't tracked", ephemeral=True
            )


async def setup(bot: VoiceBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(Admin(bot))
