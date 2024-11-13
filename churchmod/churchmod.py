from redbot.core import commands, Config, checks
import discord
from .dm_lib import church_channels

class ChurchMod(commands.Cog):
    """Moderation and automation for WWW.DUNGEON.CHURCH role playing group"""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.server_id = [1190404189214494800, 828777456898277396] # [dev, prod]
        default_guild_settings = {
            "debug_mode": False,
        }
    #
    # Bot functions
    #
    async def cog_check(self, ctx: commands.Context) -> bool:
        """Restrict cog commands to our servers."""
        if ctx.guild is not None and ctx.guild.id in self.server_id:
            return True
        await ctx.send("> *This accursed place is not my [home](https://www.dungeon.church)!*\n--**The Deacon**")
        return False
    
    async def _channel(self, channel_name: str, ctx) -> int:
        """Returns the channel ID based on the environment and debug mode."""
        if ctx.guild.id == self.server_id[0]:
            return church_channels["dev-server"]
        debug_mode = await self.config.debug_mode() 
        if not debug_mode:
            return church_channels.get(channel_name, church_channels["server-log"])
        return church_channels["server-log"]
    
    # 
    # churchmod command group
    #
    @commands.group()
    @checks.is_owner()
    async def churchmod(self, ctx: commands.Context):
        """Commands for managing churchmod automation."""
        pass

    @churchmod.command()
    async def debug(self, ctx: commands.Context, state: bool) -> None:
        """Toggle debug mode on or off in prod. Dev server, do nothing."""
        if ctx.guild.id == self.server_id[0]:
            await ctx.send("`You can't do that here.`")
            return
        current_state = await self.config.debug_mode()
        if state == current_state:
            await ctx.send(f"`Debug mode is already {'on' if current_state else 'off'}.`")
            return
        await self.config.debug_mode.set(state)
        await ctx.send(f"`Debug mode was turned {'on' if state else 'off'}.`")
        return
    
