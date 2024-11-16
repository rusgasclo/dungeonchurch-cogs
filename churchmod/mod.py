"""
DUNGEON CHURCH

Moderation actions
"""

import discord 
from discord import Embed
from redbot.core.utils.chat_formatting import error, question, success

async def make_offering(ctx) -> None:
        """Send donations and tips link as embed
        
            TODO: this should swap out the author and the donation link depending on who is calling it."""
        logo_emoji = discord.utils.get(ctx.guild.emojis, name="dungeonchurch")
        embed = Embed(
            description = f"""
                # Offering Plate
                **Dungeon Church**'s purpose is to facilitate friendship and good times over some dice, and our games will always be free.

                If you'd like to contribute to the group's expenses or show your appreciation, your support is completely optional but very much appreciated.

                Thanks for being a part of our collective adventure.
            """,
            color=0xff0000
        )
        embed.set_thumbnail(url="https://www.dungeon.church/content/images/2024/09/offering.png")
        embed.set_author(name="DM Brad passes around the...",icon_url="https://www.gravatar.com/avatar/7e2d60eb1f322b4ad6040a746946a361?s=250&d=mm&r=x")
        donation_button = discord.ui.Button(
             label = "Donations & Tips",
             emoji = "🙏",
             url = "https://www.dungeon.church/#/portal/support",
             style = discord.ButtonStyle.link
        )
        tithe_button = discord.ui.Button(
             label = "Become a Tithing Member",
             emoji = logo_emoji,
             url = "https://www.dungeon.church/#/portal/signup",
             style = discord.ButtonStyle.link
        )

        view = discord.ui.View()
        view.add_item(donation_button)
        view.add_item(tithe_button)
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