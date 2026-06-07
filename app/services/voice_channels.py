import asyncio
import logging

import discord
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.voice_channel import VoiceChannel


voice_channel_update_lock = asyncio.Lock()
logger = logging.getLogger(__name__)


async def get_voice_channel_ids(session: AsyncSession, server_id: int) -> set[int]:
    voice_channels = await get_voice_channels(session, server_id)
    return {channel.id for channel in voice_channels}


async def get_parent_voice_channel_ids(
    session: AsyncSession, server_id: int
) -> set[int]:
    voice_channels = await get_voice_channels(session, server_id)
    return {
        channel.id
        for channel in voice_channels
        if channel.parent_channel_id is None
    }


async def get_voice_channels(session: AsyncSession, server_id: int) -> list[VoiceChannel]:
    stmt = select(VoiceChannel).filter(VoiceChannel.server_id == server_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_voice_channels_by_parent(
    session: AsyncSession, parent_channel_id: int
) -> list[VoiceChannel]:
    stmt = select(VoiceChannel).filter(VoiceChannel.parent_channel_id == parent_channel_id)
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
    session: AsyncSession,
    server_id: int,
    channel_id: int,
    parent_channel_id: int | None = None,
) -> None:
    channel = dict(
        server_id=server_id,
        id=channel_id,
        parent_channel_id=parent_channel_id,
    )
    stmt = insert(VoiceChannel).values(channel).on_conflict_do_nothing(
        index_elements=[VoiceChannel.id]
    )
    await session.execute(stmt)
    await session.commit()


async def remove_voice_channel(
    session: AsyncSession, server_id: int, channel_id: int
) -> VoiceChannel | None:
    voice_channel = await get_voice_channel(session, server_id, channel_id)
    if voice_channel is None:
        return None

    if voice_channel.parent_channel_id is None:
        stmt = (
            delete(VoiceChannel)
            .filter(VoiceChannel.server_id == server_id)
            .filter(
                (VoiceChannel.id == channel_id)
                | (VoiceChannel.parent_channel_id == channel_id)
            )
        )
        await session.execute(stmt)
    else:
        await session.delete(voice_channel)
    await session.commit()
    return voice_channel


async def update_voice_channels(session: AsyncSession, channel: discord.abc.GuildChannel) -> None:
    if not isinstance(channel, discord.VoiceChannel):
        return

    async with voice_channel_update_lock:
        # Get the database entry for the handled channel
        db_voice_channel = await get_voice_channel(session, channel.guild.id, channel.id)

        # Skip if changed channel is not managed.
        if db_voice_channel is None:
            return

        # Get the parent discord channel
        parent_channel = channel.guild.get_channel(db_voice_channel.parent_channel_id or db_voice_channel.id)
        if not isinstance(parent_channel, discord.VoiceChannel):
            return

        # Get managed channels by parent
        managed_db_voice_channels_by_parent = await get_voice_channels_by_parent(session, parent_channel.id)
        managed_channels = get_managed_dicord_voice_channels(parent_channel, managed_db_voice_channels_by_parent)

        # Get empty channels
        empty_channels = [vc for vc in [parent_channel, *managed_channels] if not vc.members]

        if any(empty_channels):
            # Delete empty managed channels except the first
            for empty_channel in empty_channels[1:]:
                # Database deletion is handled by discord event on_guild_channel_delete
                await empty_channel.delete()
            await move_voice_channel_to_group_top(managed_channels, empty_channels[0])
        else:
            # Create empty channel in discord
            new_channel = await parent_channel.guild.create_voice_channel(
                parent_channel.name,
                category=parent_channel.category,
                position=parent_channel.position,
                overwrites=_channel_permission_overwrites(parent_channel),
            )
            # Create channel in database
            await add_voice_channel(
                session,
                parent_channel.guild.id,
                new_channel.id,
                parent_channel_id=parent_channel.id,
            )
            await move_voice_channel_to_group_top([parent_channel, *managed_channels], new_channel)


async def ensure_channel_deleted_from_database(session: AsyncSession, channel: discord.VoiceChannel) -> None:
    async with voice_channel_update_lock:
        db_voice_channel = await get_voice_channel(session, channel.guild.id, channel.id)
        if db_voice_channel is None:
            return

        # Delete child channels from database
        if db_voice_channel.parent_channel_id is None:
            await get_voice_channels_by_parent(session, db_voice_channel.id)

        # Delete parent channel from database
        await remove_voice_channel(session, channel.guild.id, channel.id)


def get_managed_dicord_voice_channels(
    parent_channel: discord.VoiceChannel, db_voice_channels: list[VoiceChannel]
) -> list[discord.VoiceChannel]:
    return sorted(
        [
            voice_channel
            for db_voice_channel in db_voice_channels
            if isinstance(
                voice_channel := parent_channel.guild.get_channel(db_voice_channel.id),
                discord.VoiceChannel,
            )
        ],
        key=lambda voice_channel: voice_channel.position,
    )


async def move_voice_channel_to_group_top(group: list[discord.VoiceChannel], channel: discord.VoiceChannel) -> None:
    if channel.guild.get_channel(channel.id) is None:
        return

    existing_managed_channels = sorted(
        [
            managed_channel
            for managed_channel in group
            if channel.guild.get_channel(managed_channel.id) is not None
        ],
        key=lambda managed_channel: managed_channel.position,
    )
    if not existing_managed_channels:
        return

    top_channel = existing_managed_channels[0]
    try:
        await channel.move(before=top_channel)
    except:
        logger.exception("Failed to move voice channel %s before %s", channel.id, top_channel.id)


def _channel_permission_overwrites(
    channel: discord.VoiceChannel
) -> dict[discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite]:
    # Copy permissions from the parent channel
    overwrites = dict(channel.overwrites)

    # Make sure the bot doesn't lose access to the channel
    overwrites[channel.guild.me] = discord.PermissionOverwrite(
        view_channel=True, connect=True, manage_channels=True
    )

    return overwrites
