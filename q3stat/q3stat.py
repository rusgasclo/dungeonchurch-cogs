from redbot.core import commands, Config, checks 
from redbot.core.utils.chat_formatting import error, question, success
import discord
from discord.ext import tasks
import aiohttp
import asyncio
import logging
import json
from datetime import datetime

# Set up logging
log = logging.getLogger("red.q3stat")
log.setLevel(logging.DEBUG)

class Q3stat(commands.Cog):
    """Quake III Arena server info & matchmaking via qstat"""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=3202561001, force_registration=True
        )
        default_guild = {
            "min_players": 1,                                                   # [int]minimum number of players for matchmaking
            "json_url": "https://quake.dungeon.church/qstat.json",              # [str] URL of qstat json output
            "json_interval": 60,                                                # [int] in seconds, how often to check the qstat URL
            "match_channel": None,                                              # [int] Channel IDfor matchmaking messages
            "match_embed_id": None,                                             # [int] Message ID for matchmaking announcement
            "match_thread_id": None,                                            # [int] Thread ID for the match_embed message
            "match_role": None,                                                 # [int] Role ID to give players
            "match_cleanup": True,                                              # [bool] Delete matchmaking messages when active players drops below min_players
            "previous_players": [],                                             # [list] Player state from last check
            "nicks": []                                                         # [list[dict{}]] Map DiscordID:Nickname
        }
        self.config.register_guild(**default_guild)

        # Dict of tasks for each guild the bot is in
        self.guild_tasks = {}
        # Start tasks for existing guilds
        self.bot.loop.create_task(self.initialize_tasks())

    def cog_unload(self):
        """Cancel all background tasks when the cog is unloaded."""
        for task in self.guild_tasks.values():
            task.cancel()
        self.guild_tasks.clear()

    async def initialize_tasks(self):
        """Initialize background tasks for all guilds the bot is part of."""
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.start_guild_task(guild)

    ### TASK MANAGEMENT METHODS

    async def start_guild_task(self, guild: discord.Guild):
        """Start the background task for a specific guild."""
        if guild.id in self.guild_tasks:
            log.info(f"Task already running for guild '{guild.name}'.")
            return
        task = asyncio.create_task(self.fetch_guild_data(guild))
        self.guild_tasks[guild.id] = task
        log.info(f"Started fetch task for guild '{guild.name}'.")

    async def stop_guild_task(self, guild: discord.Guild):
        """Stop the background task for a specific guild."""
        task = self.guild_tasks.get(guild.id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.guild_tasks[guild.id]
            log.info(f"Stopped fetch task for guild '{guild.name}'.")

    async def fetch_guild_data(self, guild: discord.Guild):
        """Background task to fetch server stats and post matchmaking messages for a guild."""
        while True:
            try:
                # Retrieve guild-specific configurations
                json_url = await self.config.guild(guild).json_url()
                match_channel = await self.config.guild(guild).match_channel()
                json_interval = await self.config.guild(guild).json_interval()
                previous_players = await self.config.guild(guild).previous_players()
                log.debug(f"Fetched previous_players for guild '{guild.name}': {previous_players}")

                if not json_url or not match_channel:
                    log.warning(f"Guild '{guild.name}' is missing server URL or match channel configuration.")
                    await asyncio.sleep(json_interval)
                    continue

                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(json_url) as response:
                            if response.status != 200:
                                log.error(f"Failed to fetch stats for guild '{guild.name}': HTTP {response.status}")
                                await asyncio.sleep(json_interval)
                                continue
                            text_data = await response.text()
                            data = json.loads(text_data)
                    except json.JSONDecodeError as json_err:
                        log.error(f"JSON decoding failed for guild '{guild.name}': {json_err}")
                        await asyncio.sleep(json_interval)
                        continue
                    except Exception as e:
                        log.error(f"Error fetching stats for guild '{guild.name}': {e}")
                        await asyncio.sleep(json_interval)
                        continue

                # Validate JSON structure
                if not isinstance(data, list) or len(data) == 0:
                    log.error(f"Invalid JSON structure for guild '{guild.name}'. Expected a non-empty list.")
                    await asyncio.sleep(json_interval)
                    continue

                # Assuming monitoring the first server in the list
                server_data = data[0]
                players = server_data.get("players", [])

                # Filter out players with ping = 0 (bots)
                human_players = [player["name"] for player in players if player.get("ping", 0) > 0]
                log.debug(f"Human players for guild '{guild.name}': {human_players}")

                # Sort lists for consistent comparison
                human_players_sorted = sorted(human_players)
                previous_players_sorted = sorted(previous_players)
                log.debug(f"Sorted human_players_sorted: {human_players_sorted}")
                log.debug(f"Sorted previous_players_sorted: {previous_players_sorted}")

                # Detect new players
                new_players = list(set(human_players_sorted) - set(previous_players_sorted))
                old_players = list(set(previous_players_sorted) - set(human_players_sorted))
                log.debug(f"New players: {new_players}")
                log.debug(f"Old players: {old_players}")

                if new_players:
                    channel = guild.get_channel(match_channel)
                    if channel and isinstance(channel, discord.TextChannel):
                        for player in new_players:
                            try:
                                await channel.send(f"🟢 **{player}** has joined the Quake 3 server!")
                            except discord.Forbidden:
                                log.error(f"Missing permissions to send messages in channel '{channel.name}' for guild '{guild.name}'.")
                            except discord.HTTPException as http_exc:
                                log.error(f"HTTP error occurred while sending message in guild '{guild.name}': {http_exc}")
                    else:
                        log.error(f"Channel with ID {match_channel} not found or is not a text channel in guild '{guild.name}'.")
                if old_players:
                    channel = guild.get_channel(match_channel)
                    if channel and isinstance(channel, discord.TextChannel):
                        for player in old_players:
                            try:
                                await channel.send(f"🔴 **{player}** has left the Quake 3 server!")
                            except discord.Forbidden:
                                log.error(f"Missing permissions to send messages in channel '{channel.name}' for guild '{guild.name}'.")
                            except discord.HTTPException as http_exc:
                                log.error(f"HTTP error occurred while sending message in guild '{guild.name}': {http_exc}")
                    else:
                        log.error(f"Channel with ID {match_channel} not found or is not a text channel in guild '{guild.name}'.")


                # Update the previous players list
                await self.config.guild(guild).previous_players.set(human_players)
                log.debug(f"UPDATED player list: {human_players}")   

                # Wait for the next interval
                await asyncio.sleep(json_interval)

            except asyncio.CancelledError:
                log.info(f"Fetch task for guild '{guild.name}' has been cancelled.")
                break
            except Exception as e:
                log.error(f"Unexpected error in fetch task for guild '{guild.name}': {e}")
                await asyncio.sleep(60)  # Wait before retrying after unexpected errors

### LISTENERS FOR WHEN BOT IS ADDED TO OR LEFT FROM GUILD 

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Start a fetch task when the bot joins a new guild."""
        await self.start_guild_task(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Stop the fetch task when the bot is removed from a guild."""
        await self.stop_guild_task(guild)

#### COMMANDS!

#
# [p] command group
#
    @commands.group()
    @checks.is_owner()
    async def q3stat(self, ctx: commands.Context):
        """Commands for managing Quake III Arena qstat integration"""
        pass

    @q3stat.command()
    async def settings(self, ctx: commands.Context) -> None:
        """Display the current settings."""
        setting_list = {
            "URL of qstat JSON": await self.config.guild(ctx.guild).json_url(),
            "Refresh Interval (in seconds)": await self.config.guild(ctx.guild).json_interval(),
            "Matchmaking Channel": ctx.guild.get_channel(await self.config.guild(ctx.guild).match_channel()),
            "Matchmaking Minimum Players": await self.config.guild(ctx.guild).min_players(),
            "Matchmaking Role": await self.config.guild(ctx.guild).match_role(),
            "Cleanup Matchmaking Message": await self.config.guild(ctx.guild).match_cleanup(),
            "Nicks Registered": len(await self.config.guild(ctx.guild).nicks()),
        }
        
        embed = discord.Embed(
            title = ":pistol: q3stat Settings",
            color = 0xff0000
        )
        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)
        await ctx.send(embed=embed)

    @q3stat.command()
    async def minimum(self, ctx: commands.Context, *, min_players:int = None) -> None:
        """Set minimum number of players for matchmaking."""
        if min_players is not None and min_players > 0:
            await self.config.guild(ctx.guild).min_players.set(min_players)
            await ctx.send(success(f"`Matchmaking minimum player count has been set to {min_players}.`"))
        else:
            await ctx.send(question("`Please enter the number of players to start matchmaking.`"))

    @q3stat.command()
    async def refresh(self, ctx: commands.Context, *, interval:int = None) -> None:
        """Set the refresh interval for the JSON."""
        if interval is not None and interval > 0:
            await self.config.guild(ctx.guild).json_interval.set(interval)

            await ctx.send(success(f"`Refresh interval set to {interval}.`"))
        else:
            await ctx.send(question("`Please enter the number of seconds to refresh the JSON URL.`"))

    @q3stat.command()
    async def json(self, ctx: commands.Context, *, url:str = None) -> None:
        """Set the URL for the JSON output of qstat.

           Command: `qstat -json -P -q3s dungeon.church:27960 > qstat.json`
           Schedule with crontab and make the output file publicly accessible on your server.
        """
        if url is not None: # TODO: check if slice of url starts with 'http'
            await self.config.guild(ctx.guild).json_url.set(url)
            await ctx.send(success(f"`The qstat JSON URL has been set to {url}`"))
        else:
            await ctx.send(question("`Please enter a valid URL to the output of qstat JSON.`"))

    @q3stat.command()
    async def role(self, ctx: commands.Context, *, role:int = None) -> None:
        """Role given to Quake III Arena players with linked nicks while playing."""
        if role is not None:
            await self.config.guild(ctx.guild).match_role.set(role)
            await ctx.send(success(f"`The matchmaking role has been set to {role}.`"))
        else:
            await ctx.send(question("`Please mention a role or enter the Role ID.`"))

    @q3stat.command()
    async def channel(self, ctx: commands.Context, *, channel:discord.TextChannel = None) -> None:
        """Set channel where the matchmaking messages are posted."""
        if channel:
            # Check if the bot has permission to send messages in the specified channel
            permissions = channel.permissions_for(ctx.guild.me)
            if not permissions.send_messages:
                await ctx.send(error(f"`I don't have permission to send messages in {channel.mention}. Please adjust the channel permissions and try again.`"))
                return
            
            # Save the channel ID to the config
            await self.config.guild(ctx.guild).match_channel.set(channel.id)
            await ctx.send(success(f"`The matchmaking channel has been set to {channel}.`"))
        else:
            await ctx.send(question("`Please mention a channel or enter the Channel ID.`"))