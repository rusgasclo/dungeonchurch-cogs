"""
DUNGEON CHURCH

Onboarding functions
"""
from redbot.core.utils import get_logger
from .dm_lib import emojis

logger = get_logger("red.churchmod")

async def hail(self, member: discord.Member) -> None:
    """Send a public welcome message to new members."""
    channel = member.guild.get_channel(_channel("chat"))
    if channel:
        await channel.send(f"# {emojis["beers"]} Hail and well met, {member.mention}!")
        logger.info(f"HAIL: Sent welcome message to {member.display_name}")