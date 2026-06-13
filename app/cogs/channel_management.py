"""User management"""

import discord
from discord import User
from app.bot import VoiceBot

from app.services.voice_channels import (
    get_voice_channel,
    update_voice_channel,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def channel_permision_check(
    session: AsyncSession,
    interaction: discord.Interaction,
):
    if isinstance(interaction.user, User) or interaction.guild_id is None:
        await interaction.response.send_message(
            "The commands can only be used in a guild", ephemeral=True
        )
        return False

    voice = interaction.user.voice
    if voice is None or voice.channel is None:
        await interaction.response.send_message(
            "You are not part of a voice channel", ephemeral=True
        )
        return False

    db_voice_channel = await get_voice_channel(
        session, interaction.guild_id, voice.channel.id
    )
    if db_voice_channel is None:
        await interaction.response.send_message(
            "You are not in a managed voice channel", ephemeral=True
        )
        return False

    if db_voice_channel.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "You are not the owner of this voice channel", ephemeral=True
        )
        return False

    return True


class RenameModal(discord.ui.Modal, title="Rename the squad voice channel"):
    def __init__(self, bot: VoiceBot):
        self.bot = bot
        super().__init__()

    name = discord.ui.TextInput(
        label="What do you want to name your voice channel?",
        style=discord.TextStyle.short,
        max_length=500,
        placeholder="test",
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction[VoiceBot]) -> None:
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                if len(self.name.value) < 3:
                    await interaction.response.send_message(
                        "Please pick a longer channel name", ephemeral=True
                    )
                    return

                await interaction.user.voice.channel.edit(name=self.name.value)
                await interaction.response.send_message(
                    "Channel name has been updated!", ephemeral=True
                )


class ChangeOwnerView(discord.ui.View):
    def __init__(self, bot: VoiceBot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.select(custom_id="voice_change_owner_2", cls=discord.ui.UserSelect)
    async def select_channels(
        self, interaction: discord.Interaction, select: discord.ui.UserSelect
    ):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                await update_voice_channel(
                    session,
                    interaction.user.voice.channel.id,
                    {"owner_id": select.values[0].id},
                )
                return await interaction.response.send_message(
                    f"{select.values[0].mention} is now the owner of this voice channel",
                    ephemeral=True,
                )


class VoiceRoleLockView(discord.ui.View):
    def __init__(self, bot: VoiceBot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="voice_role_lock_2",
        cls=discord.ui.RoleSelect,
        min_values=1,
        max_values=10,
    )
    async def select_channels(
        self, interaction: discord.Interaction, select: discord.ui.RoleSelect
    ):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                channel = interaction.user.voice.channel
                guild = interaction.guild

                overwrites = {
                    key: value
                    for key, value in channel.overwrites.items()
                    if not isinstance(key, discord.role)
                }
                overwrites[guild.default_role] = discord.PermissionOverwrite(
                    connect=False
                )

                for role in select.values:
                    overwrites[role] = discord.PermissionOverwrite(connect=True)

                await channel.edit(overwrites=overwrites)
                return await interaction.response.send_message(
                    "Allowed only the selected roles to join the channel",
                    ephemeral=True,
                )


class VoiceUserLockView(discord.ui.View):
    def __init__(self, bot: VoiceBot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="voice_role_lock_2",
        cls=discord.ui.UserSelect,
        min_values=1,
        max_values=10,
    )
    async def select_channels(
        self, interaction: discord.Interaction, select: discord.ui.UserSelect
    ):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                channel = interaction.user.voice.channel
                guild = interaction.guild

                overwrites = {
                    key: value
                    for key, value in channel.overwrites.items()
                    if not isinstance(key, discord.Member)
                }
                overwrites[guild.default_role] = discord.PermissionOverwrite(
                    connect=False
                )

                for member in select.values:
                    overwrites[member] = discord.PermissionOverwrite(connect=True)

                await channel.edit(overwrites=overwrites)
                return await interaction.response.send_message(
                    "Allowed only the selected users to join the channel",
                    ephemeral=True,
                )


class SetLimitView(discord.ui.View):
    def __init__(self, bot: VoiceBot):
        self.bot = bot
        super().__init__(timeout=None)

    async def change_voice_limit(self, interaction: discord.Interaction, amount: int):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                await interaction.user.voice.channel.edit(user_limit=amount)
                return await interaction.response.send_message(
                    "Voice channel limit set!", ephemeral=True
                )

    @discord.ui.button(
        label="2",
        custom_id="voice_limit_2",
        style=discord.ButtonStyle.secondary,
    )
    async def set_limit_callback_2(self, interaction: discord.Interaction, button):
        await self.change_voice_limit(interaction, 2)

    @discord.ui.button(
        label="3",
        custom_id="voice_limit_3",
        style=discord.ButtonStyle.secondary,
    )
    async def set_limit_callback_3(self, interaction: discord.Interaction, button):
        await self.change_voice_limit(interaction, 3)

    @discord.ui.button(
        label="4",
        custom_id="voice_limit_4",
        style=discord.ButtonStyle.secondary,
    )
    async def set_limit_callback_4(self, interaction: discord.Interaction, button):
        await self.change_voice_limit(interaction, 4)

    @discord.ui.button(
        label="5",
        custom_id="voice_limit_5",
        style=discord.ButtonStyle.secondary,
    )
    async def set_limit_callback_5(self, interaction: discord.Interaction, button):
        await self.change_voice_limit(interaction, 5)

    @discord.ui.button(
        label="6",
        custom_id="voice_limit_6",
        style=discord.ButtonStyle.secondary,
    )
    async def set_limit_callback_6(self, interaction: discord.Interaction, button):
        await self.change_voice_limit(interaction, 6)

    @discord.ui.button(
        label="Unlimited",
        custom_id="voice_limit_unlimited",
        style=discord.ButtonStyle.success,
    )
    async def set_limit_callback_unlimited(
        self, interaction: discord.Interaction, button
    ):
        await self.change_voice_limit(interaction, 0)


class VoiceManagementView(discord.ui.View):
    def __init__(self, bot: VoiceBot):
        self.bot = bot
        super().__init__(timeout=None)

    # @discord.ui.button(
    #     label="📝 rename",
    #     custom_id="voice_rename",
    #     style=discord.ButtonStyle.success,
    #     row=0,
    # )
    # async def rename_callback(self, interaction: discord.Interaction, button):
    #     async with self.bot.db.create_session() as session:
    #         if await channel_permision_check(session, interaction):
    #             await interaction.response.send_modal(RenameModal(self.bot))

    @discord.ui.button(
        label="📍 Set limit",
        custom_id="voice_set_limit",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def set_limit_callback(self, interaction: discord.Interaction, button):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                return await interaction.response.send_message(
                    "How many people are allowed in this voice channel?",
                    ephemeral=True,
                    view=SetLimitView(self.bot),
                )

    @discord.ui.button(
        label="🔓 Remove restrictions",
        custom_id="voice_unlock",
        style=discord.ButtonStyle.secondary,
        row=0,
    )
    async def voice_unlock_callback(self, interaction: discord.Interaction, button):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                await interaction.user.voice.channel.edit(user_limit=0)
                channel = interaction.user.voice.channel
                await channel.edit(overwrites={})
                return await interaction.response.send_message(
                    "Voice channel unlocked!", ephemeral=True
                )

    @discord.ui.button(
        label="👑 Change owner",
        custom_id="voice_change_owner",
        style=discord.ButtonStyle.danger,
        row=0,
    )
    async def change_owner_callback(self, interaction: discord.Interaction, button):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                return await interaction.response.send_message(
                    "Who do you want as the new owner of the channel?",
                    ephemeral=True,
                    view=ChangeOwnerView(self.bot),
                )

    @discord.ui.button(
        label="🔐 Lock by role",
        custom_id="voice_role_lock",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def role_lock_callback(self, interaction: discord.Interaction, button):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                return await interaction.response.send_message(
                    "Which roles do you want to allow?",
                    ephemeral=True,
                    view=VoiceRoleLockView(self.bot),
                )

    @discord.ui.button(
        label="🔒 Lock by current users",
        custom_id="voice_current_users_lock",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def current_users_lock_callback(
        self, interaction: discord.Interaction, button
    ):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                channel = interaction.user.voice.channel
                guild = interaction.guild

                overwrites = {
                    key: value
                    for key, value in channel.overwrites.items()
                    if not isinstance(key, discord.Member)
                }
                overwrites[guild.default_role] = discord.PermissionOverwrite(
                    connect=False
                )

                for member in channel.members:
                    overwrites[member] = discord.PermissionOverwrite(connect=True)

                await channel.edit(overwrites=overwrites)
                return await interaction.response.send_message(
                    "Allowed only the current users to join the channel", ephemeral=True
                )

    @discord.ui.button(
        label="🔒 Lock by selected users",
        custom_id="voice_select_users_lock",
        style=discord.ButtonStyle.secondary,
        row=1,
    )
    async def select_users_lock_callback(
        self, interaction: discord.Interaction, button
    ):
        async with self.bot.db.create_session() as session:
            if await channel_permision_check(session, interaction):
                return await interaction.response.send_message(
                    "Which users do you want to allow?",
                    ephemeral=True,
                    view=VoiceUserLockView(self.bot),
                )


async def setup(bot: VoiceBot) -> None:
    """Setup the cog within discord.py lib"""
    bot.add_view(VoiceManagementView(bot))
    bot.add_view(ChangeOwnerView(bot))
    bot.add_view(SetLimitView(bot))
    bot.add_view(VoiceRoleLockView(bot))
    bot.add_view(VoiceUserLockView(bot))
