"""
DUNGEON CHURCH

Moderation actions
"""

import discord 
from discord import Embed
from redbot.core.utils.chat_formatting import error, question, success
from . import embeds
from openai import OpenAI

async def make_offering(ctx, config) -> None:
        """Send donations and tips link as embed"""
        if not ctx.interaction: # delete prefix trigger messages
            await ctx.message.delete() 
        llm = await config.guild(ctx.guild).openai_api()
        if llm:
            prompt = "Generate a single direct quote no longer than a sentence or two for a church Deacon asking for contributions or tips as they pass the offertory basket to a group of adventurers or participants in a shared storytelling game as the congregation. The tone should be mysterious and ominous, with a subtle emphasis on the importance of these contributions in furthering the group's journey or story and how the group is a collective effort. Each sentence should evoke a sense of immersion in the fantasy world."
            client = OpenAI(api_key=llm)
            completion = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-3.5-turbo",
                temperature=0.5
            )
            answer = f"*{completion.choices[0].message.content}*"
        embed = embeds.offering
        embed.set_thumbnail(url="https://www.dungeon.church/content/images/2024/09/offering.png")
        embed.title = f"{ctx.author.nick if ctx.author.nick else ctx.author.display_name} passes around the..."
        button1 = embeds.donation_button
        button2 = embeds.tithe_button

        view = discord.ui.View()
        view.add_item(button1)
        view.add_item(button2)
        if llm:
             await ctx.send(answer, embed=embed, view=view)
        else:
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