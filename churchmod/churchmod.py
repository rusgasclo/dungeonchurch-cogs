from redbot.core import commands
import discord
from .dm_lib import church_channels

class ChurchMod(commands.Cog):
    """Moderation and automation for WWW.DUNGEON.CHURCH role playing group"""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.server_id = [1190404189214494800, 828777456898277396]

    # Cog check to make sure we only run on DC servers
    async def cog_check(self, ctx: commands.Context) -> bool:
        """Restrict cog commands to our servers."""
        if ctx.guild is not None and ctx.guild.id in self.server_id:
            return True
        await ctx.send("> *This accursed place is not my [home](https://www.dungeon.church)!*\n--**The Deacon**")
        return False
    
    # 
    # Command group for churchmod
    #
    @commands.group()
    async def churchmod(self, ctx):
        """Commands for managing churchmod automation."""
        pass

