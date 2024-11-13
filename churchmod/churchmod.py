from redbot.core import commands, Config, checks  
from redbot.core.utils.chat_formatting import error, question, success
import discord
from .dm_lib import church_channels, emojis
from . import rolemod, onboarding

class ChurchMod(commands.Cog):
    """Moderation and automation for WWW.DUNGEON.CHURCH role playing group"""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.server_id = [1190404189214494800, 828777456898277396] # [dev, prod]
        self.config = Config.get_conf(
            self, identifier=4206661045, force_registration=True
        )
        default_guild = {
            "debug_mode": False,
        }
        self.config.register_guild(**default_guild)

    #
    # Bot functions
    #
    async def cog_check(self, ctx: commands.Context) -> bool:
        """Restrict cog commands to our servers."""
        if ctx.guild is not None and ctx.guild.id in self.server_id:
            return True
        await ctx.send(error("*This accursed place is not my [home](https://www.dungeon.church)!*\n--**The Deacon**"))
        return False
    
    #
    # Bot Moderation
    #
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """When a new member joins the server..."""
        await onboarding.hail(member)
        await rolemod.make_npc(member)

    #
    # For fun
    #
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """React with a beer emoji to messages containing certain keywords."""
        debug = self.config.guild(message.guild).debug_mode()
        if not debug:
            return
        keywords = {"beer", "cheers", "beers", "tavern", "hail", "well met"}
        emoji = emojis["beers"]
        if any(keyword in message.content.lower() for keyword in keywords):
            await message.add_reaction(emoji)

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
        """Toggle debug mode on or off in prod. """
        if ctx.guild.id == self.server_id[0]:
            await ctx.send(error("`You can't do that here.`"))
            return
        current_state = await self.config.guild(ctx.guild).debug_mode()
        if state == current_state:
            await ctx.send(error(f"`Debug mode is already {'on' if current_state else 'off'}.`"))
            return
        await self.config.guild(ctx.guild).debug_mode.set(state)
        await ctx.send(success(f"`Debug mode was turned {'on' if state else 'off'}.`"))
        return
    
    #
    # Internal functions
    #
    async def _channel(self, channel_name: str, ctx) -> int:
        """Returns the channel ID based on the environment and debug mode."""
        if ctx.guild.id == self.server_id[0]:
            return church_channels["dev-server"]
        debug_mode = await self.config.guild.debug_mode() 
        if not debug_mode:
            return church_channels.get(channel_name, church_channels["server-log"])
        return church_channels["server-log"]