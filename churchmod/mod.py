"""
DUNGEON CHURCH

Moderation actions
"""

import discord  
from redbot.core.utils.chat_formatting import error, question, success

async def name_npc(member: discord.Member) -> None:
    """Append ` || NPC` to server nickname"""
    if "||" not in member.nick:
        await member.edit(nick=f"{member.display_name} || NPC")

async def kick_npc(member: discord.Member, config, log_channel) -> None:
    """Kick expired NPCs. 
    
    Expiration of roles is controlled by autotemproles cog"""
    autokick = await config.guild(member.guild).autokick_npc()
    if member.nick and "NPC" in member.nick:
        if autokick:
            try:
                await member.send(
                    f"Hail {member.display_name},\n\n"
                    "> *The ouroboros turns, and those without a name fade from the realm of Pyora.*"
                    "\nYou were automatically removed from **Dungeon Church** for being an NPC for 60+ days.\n"
                    "*Don't worry* - if you're still interested in playing with us, we'd still love to have you!\n"
                    "Join us again: [Invite Link]\n" # TODO
                    "If not, we wish you luck on your quest to find a gaming group. Thanks for stopping by."
                )
                await member.kick(reason="NPC expired, auto-kick enabled.")
                await log_channel.send(success(f"Auto-Kicked expired NPC **{member.display_name}**."))
            except discord.Forbidden:
                    await log_channel.send(error(f"Could not auto-kick expired NPC **{member.display_name}**: `Missing permissions`"))
            except discord.HTTPException as e:
                    await log_channel.send(question(f"Failed to auto-kick expired NPC **{member.display_name}**: `{e}`"))
        else:
            await log_channel.send(question(f"Expired NPC {member.display_name} was **NOT** auto-kicked because it's `off`"))