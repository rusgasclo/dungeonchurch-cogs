"""
DUNGEON CHURCH

Moderation actions
"""

import discord  
from .dm_lib import church_roles, church_channels

async def name_npc(member: discord.Member) -> None:
    """Append ` || NPC` to server nickname"""
    if "||" not in (member.nick or member.display_name):
        # Update the nickname to "Name || NPC"
        new_nickname = f"{member.display_name} || NPC"
        await member.edit(nick=new_nickname)