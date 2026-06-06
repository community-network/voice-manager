import asyncio

import discord
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.voice_channel import VoiceChannel


voice_channel_update_lock = asyncio.Lock()


async def get_voice_channel_ids(session: AsyncSession, server_id: int) -> set[int]:
    voice_channels = await get_voice_channels(session, server_id)
    return {channel.id for channel in voice_channels}


async def get_voice_channels(session: AsyncSession, server_id: int) -> list[VoiceChannel]:
    stmt = select(VoiceChannel).filter(VoiceChannel.server_id == server_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_voice_channel(
    session: AsyncSession, server_id: int, channel_id: int
) -> VoiceChannel | None:
    stmt = (
        select(VoiceChannel)
        .filter(VoiceChannel.id == channel_id)
        .filter(VoiceChannel.server_id == server_id)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def add_voice_channel(
    session: AsyncSession, server_id: int, channel_id: int, main: bool = False
) -> None:
    channel = dict(server_id=server_id, id=channel_id, main=main)
    stmt = insert(VoiceChannel).values(channel).on_conflict_do_nothing(
        index_elements=[VoiceChannel.id]
    )
    await session.execute(stmt)
    await session.commit()


async def remove_voice_channel(
    session: AsyncSession, server_id: int, channel_id: int
) -> None:
    voice_channel = await get_voice_channel(session, server_id, channel_id)
    if voice_channel is None:
        return
    await session.delete(voice_channel)
    await session.commit()


async def update_voice_channels(
    session: AsyncSession,
    member: discord.Member,
    channel: discord.abc.GuildChannel,
) -> None:
    if not isinstance(channel, discord.VoiceChannel):
        return

    async with voice_channel_update_lock:
        db_voice_channels = await get_voice_channels(session, member.guild.id)
        db_voice_channel_by_id = {voice_channel.id: voice_channel for voice_channel in db_voice_channels}

        # Skip if changed channel is not managed.
        if channel.id not in db_voice_channel_by_id or channel.category is None:
            return

        # Get empty channels of discord server
        empty_channels = [vc for vc in channel.guild.voice_channels if vc.id in db_voice_channel_by_id and not vc.members]

        # Create empty channel if not empty channels exist
        if not empty_channels:
            # Create voice channel on discord server
            new_channel = await channel.category.create_voice_channel(
                channel.name,
                position=channel.position,
                overwrites=_get_child_channel_overwrites(channel),
            )
            # Add channel to the database
            await add_voice_channel(session, member.guild.id, new_channel.id)
            return

        empty_main_channel_exists = any(db_voice_channel_by_id[empty_channel.id].main for empty_channel in empty_channels)
        empty_extra_channels = [empty_channel for empty_channel in empty_channels if not db_voice_channel_by_id[empty_channel.id].main]

        # Keep the main channel, and keep one generated empty channel if needed.
        channels_to_delete = empty_extra_channels if empty_main_channel_exists else empty_extra_channels[:-1]
        for extra_channel in channels_to_delete:
            # Delete voice channel from discord server
            await extra_channel.delete()
            # Delete channel from database
            await remove_voice_channel(session, member.guild.id, extra_channel.id)


def _get_child_channel_overwrites(
    channel: discord.VoiceChannel
) -> dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]:
    # Copy permissions from the main channel
    overwrites = dict(channel.overwrites)

    # Make sure the bot doesnt loose access to the channel
    overwrites[channel.guild.me] = discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)

    return overwrites
