"""Non-grouped commands"""

import discord
from discord import app_commands
from discord.ext import commands

from app.bot import VoiceBot


class OtherCommands(commands.Cog):
    """Other commands"""

    def __init__(self, bot: VoiceBot):
        self.bot = bot

    @app_commands.command(name="help", description="See more info about the bot")
    async def help_command(self, interaction: discord.Interaction):
        """Main help command"""
        await interaction.response.defer()
        embed = discord.Embed(
            color=0xFFA500,
            title="Help for the Channel Manager bot",
            description="This bot will automatically make child channels, based on the parent channel it is keeping track of. "
            "It will always leave 1 empty channel, for players to join. "
            'To setup the bot, use "/admin voice-channels add" to add a parent channel. ',
        )
        await interaction.followup.send(embed=embed)


async def setup(bot: VoiceBot) -> None:
    """Setup the cog within discord.py lib"""
    await bot.add_cog(OtherCommands(bot))
