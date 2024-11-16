"""
DUNGEON CHURCH

Moderation actions
"""

import discord 
from discord import Embed
from redbot.core.utils.chat_formatting import error, question, success
from . import embeds

async def make_offering(ctx) -> None:
        """Send donations and tips link as embed"""
        logo_emoji = discord.utils.get(ctx.guild.emojis, name="dungeonchurch")
        embed = embeds.offering
        embed.set_thumbnail(url="https://www.dungeon.church/content/images/2024/09/offering.png")
        embed.title = f"{ctx.author.nick if ctx.author.nick else ctx.author.display_name} passes around the..."
        button1 = embeds.donation_button
        button2 = embeds.tithe_button

        view = discord.ui.View()
        view.add_item(button1)
        view.add_item(button2)
        await ctx.send(embed=embed, view=view)

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