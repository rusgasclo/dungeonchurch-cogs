"""
DUNGEON CHURCH

Onboarding functions
"""
from .dm_lib import emojis
import discord

async def hail(self, member: discord.Member) -> None:
    """Send a public welcome message to new members."""
    channel = member.guild.get_channel(_channel("chat"))
    if channel:
        await channel.send(f"# {emojis['beers']} Hail and well met, {member.mention}!")