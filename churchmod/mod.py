"""
DUNGEON CHURCH

Moderation actions
"""

import discord  
from .dm_lib import church_roles, church_channels

async def make_npc(member: discord.Member) -> None:
    """Assign the NPC role to a member if they don't already have it."""
    guild = member.guild
    npc_role = guild.get_role(church_roles["npcs"])
    if npc_role and npc_role not in member.roles:
        await member.add_roles(npc_role)
    if "||" not in (member.nick or member.display_name):
        # Update the nickname to "Name || NPC"
        new_nickname = f"{member.display_name} || NPC"
        await member.edit(nick=new_nickname)

async def name_npc(member: discord.Member) -> None:
    """Append ` || NPC` to server nickname"""
    if "||" not in (member.nick or member.display_name):
        # Update the nickname to "Name || NPC"
        new_nickname = f"{member.display_name} || NPC"
        await member.edit(nick=new_nickname)