"""
DUNGEON CHURCH

Embeds for cog functions
"""
import discord
from discord import Embed
from .dm_lib import emojis

#
# Dynamic assets
#
async def settings(config, ctx) -> None: 
    """Returns an embed with a list of settings"""
    setting_list = {
            "Debug Mode": await config.guild(ctx.guild).debug_mode(),
            "Logging": await config.guild(ctx.guild).log_mode(),
            "Auto-kick NPCs": await config.guild(ctx.guild).autokick_npc(),
            "OpenAI API Key": "Yes" if await config.guild(ctx.guild).openai_api() else "Not Set"
    }
    embed = discord.Embed(
        title = "Current churchmod Settings",
        color = 0xff0000
    )
    for setting, value in setting_list.items():
        embed.add_field(name=setting, value=f"```{value}```", inline=False)
    await ctx.send(embed=embed)

#
# Static assets
#
offering = Embed(
    description = f"""
        # Offering Plate
        **Dungeon Church**'s purpose is to facilitate friendship and good times over some dice, and our games will always be free.

        If you'd like to contribute to the group's expenses or show your appreciation, your support is completely optional but very much appreciated.

        Thanks for being a part of our collective adventure.
    """,
    color=0xff0000
)
donation_button = discord.ui.Button(
        label = "Donations & Tips",
        emoji = "🙏",
        url = "https://www.dungeon.church/#/portal/support",
        style = discord.ButtonStyle.link
)
tithe_button = discord.ui.Button(
        label = "Become a Tithing Member",
        emoji = emojis["beers"],
        url = "https://www.dungeon.church/#/portal/signup",
        style = discord.ButtonStyle.link
)