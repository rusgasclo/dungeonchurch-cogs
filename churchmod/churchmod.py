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
            "log_mode": True,
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
        await member.guild.get_channel(await self._channel("chat", member.guild)).send(f"{emojis['beers']} Hail and well met, {member.mention}!")
        await member.add_roles(member.guild.get_role(church_roles["npcs"]))

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Listen for role changes to trigger mod actions."""
        target_role = after.guild.get_role(church_roles["npcs"])
        if target_role not in before.roles and target_role in after.roles:
            await mod.name_npc(after)

        target_role = after.guild.get_role(church_roles["holding"])
        if target_role not in before.roles and target_role in after.roles:
            await after.guild.get_channel(await self._channel("campaign-planning", after.guild)).send(f"### {emojis['rsvpyes']} {after.mention} is <@&{church_roles['holding']}> the date for the next tentative game.")
        if target_role in before.roles and target_role not in after.roles: # not sent to public channel, so manually log
            await after.guild.get_channel(await self._channel("server-log", after.guild)).send(f"### {emojis['rsvpno']} {after.mention} is no longer <@&{church_roles['holding']}> the date for the next tentative game.")

        target_role = after.guild.get_role(church_roles["test"])
        if target_role not in before.roles and target_role in after.roles:
            await after.guild.get_channel(await self._channel("dnd-irl", after.guild)).send(f"### :bridge_at_night: {after.mention} has been added as a  <@&{church_roles['irl']}> Bay area player.")

        target_role = after.guild.get_role(church_roles["vtt"])
        if target_role not in before.roles and target_role in after.roles:
            await after.guild.get_channel(await self._channel("dnd-vtt", after.guild)).send(f"### <a:partyWizard:1239472274432720929> {after.mention} has been uploaded as a  <@&{church_roles['vtt']}> virtual player.")

        target_role = after.guild.get_role(church_roles["dungeon organizer"])
        if target_role not in before.roles and target_role in after.roles:
            await after.guild.get_channel(await self._channel("no-players-allowed", after.guild)).send(f"### {emojis['dm']} {after.mention} has ascended to  <@&{church_roles['dungeon organizer']}>.")
        

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Listen for when members join or leave a voice channel."""
        if before.channel is None and after.channel is not None:
            await member.add_roles(member.guild.get_role(church_roles["scrying"]))
        else:
            await member.remove_roles(member.guild.get_role(church_roles["scrying"]))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Forward bot messages that are not responses to a command to server-log"""
        if message.author.id == self.bot.user.id: # only messages from this bot
            ctx = await self.bot.get_context(message)
            if not ctx.valid: # exclude command responses & interactions
                if message.channel.id != await self._channel("server-log", message.guild): # exclude messages in server-log
                    if message.content: # exclude messages that are only embeds
                        await message.guild.get_channel(await self._channel("server-log", message.guild)).send(message.content)

        """React with a beer emoji to messages containing certain keywords."""
        debug = await self.config.guild(message.guild).debug_mode()
        if debug:
            return
        keywords = {"beer", "cheers", "tavern", "ghost town"}
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
    async def debug(self, ctx: commands.Context, state: bool = None) -> None:
        """Toggle debug mode: route bot messages to server-log"""
        if ctx.guild.id == self.server_id[0]:
            await ctx.send(error("`You can't do that here.`"))
            return
        current_state = await self.config.guild(ctx.guild).debug_mode()
        if state is None:
            new_state = not current_state
        else:
            new_state = state
        if new_state == current_state:
            await ctx.send(error(f"`Debug mode is already {'on' if current_state else 'off'}.`"))
            return
        await self.config.guild(ctx.guild).debug_mode.set(new_state)
        await ctx.send(success(f"`Debug mode was turned {'on' if new_state else 'off'}.`"))
        return

    @churchmod.command()
    async def logs(self, ctx: commands.Context, state: bool = None) -> None:
        """Toggle log mode: copy bot messages to server-log"""
        if ctx.guild.id == self.server_id[0]:
            await ctx.send(error("`You can't do that here.`"))
            return
        current_state = await self.config.guild(ctx.guild).log_mode()
        if state is None:
            new_state = not current_state
        else:
            new_state = state
        if new_state == current_state:
            await ctx.send(error(f"`Server log mode is already {'on' if current_state else 'off'}.`"))
            return
        await self.config.guild(ctx.guild).log_mode.set(new_state)
        await ctx.send(success(f"`Server log mode has been turned {'on' if new_state else 'off'}.`"))

    @churchmod.command()
    async def test(self, ctx: commands.Context) -> None:
        """Test a function"""
        channels = await self._voice_channels(ctx.guild)
        await ctx.send(f"CHANNELS: {channels}")

    
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