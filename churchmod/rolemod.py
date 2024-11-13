"""
DUNGEON CHURCH
Role moderation
"""

import discord  
from .dm_lib import church_roles, church_channels

async def make_npc(self, member: discord.Member) -> None:
    """Assign the NPC role to a member if they don't already have it."""
    guild = member.guild
    npc_role = guild.get_role(church_roles["npcs"]) # get role object from ID
    if npc_role and npc_role not in member.roles:
        await member.add_roles(npc_role)
    if "||" not in (member.nick or member.display_name):
            # Update the nickname to "Name || NPC"
            new_nickname = f"{member.display_name} || NPC"
            await member.edit(nick=new_nickname)

async def make_organizer(self, member: discord.Member) -> None:
    """Assign the dungeo organizer role to a member if they don't already have it."""
    guild = member.guild
    npc_role = guild.get_role(church_roles["dungeon organizer"]) # get role object from ID
    if npc_role and npc_role not in member.roles:
        await member.add_roles(npc_role)
