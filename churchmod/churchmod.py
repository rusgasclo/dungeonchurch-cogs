from redbot.core import commands, Config, checks  
from redbot.core.utils.chat_formatting import error, question, success
import discord
from .dm_lib import church_channels, emojis, church_roles
from . import mod

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
        # Send welcome message
        await member.guild.get_channel(await self._channel("chat", member.guild)).send(f"{emojis['beers']} Hail and well met, {member.mention}!")
        # Make NPC
        await mod.make_npc(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Listen for role changes to trigger mod actions."""
        # NPC ROLE
        target_role = after.guild.get_role(church_roles["npcs"])
        if target_role not in before.roles and target_role in after.roles:
            await mod.name_npc(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """React with a beer emoji to messages containing certain keywords."""
        debug = await self.config.guild(message.guild).debug_mode()
        if debug:
            return
        keywords = {"beer", "cheers", "beers", "tavern", "ghost town"}
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

    @churchmod.command()
    async def test(self, ctx: commands.Context) -> None:
        """Test a function"""
        pass
    
    #
    # Internal functions
    #
    async def _channel(self, channel_name: str, guild: discord.Guild) -> int:
        """Returns the channel ID based on the environment and debug mode."""
        if guild.id == self.server_id[0]: # dev server
            return church_channels["dev-server"]
        debug = await self.config.guild(guild).debug_mode() 
        if not debug:
            return church_channels.get(channel_name, church_channels["server-log"])
        return church_channels["server-log"]