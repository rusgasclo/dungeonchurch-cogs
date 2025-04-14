from redbot.core import commands, app_commands, Config, checks 
from redbot.core.utils.chat_formatting import error, question, success
import discord
from discord.ext import tasks
import aiohttp
import asyncio
import logging
import json
from datetime import datetime
import io

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
            "match_channel": None,                                              # [int] Channel ID for matchmaking messages
            "match_embed_id": None,                                             # [int] Message ID for server info embed
            "match_embed_channel": None,                                        # [int] Channel ID for server info embed
            "match_thread": None,                                               # [int] Thread ID for the match_embed_id message
            "noti_role": None,                                                  # [int] Role ID to give players
            "match_cleanup": True,                                              # [bool] Delete matchmaking messages when players
            "previous_state": {},                                               # [dict] Previous JSON state
            "current_state": {},                                                # [dict] Current JSON state
            "previous_players": [],                                             # [list] Player state from last check
            "nicks": [],                                                        # [list[dict{}]] Map DiscordID:Nickname
            "join_messages": {}                                                 # [dict] Mapping of player names to join message IDs
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

    #### FETCH JSON & VALIDATE JSON

    async def fetch_guild_data(self, guild: discord.Guild):
        """Background task to fetch server stats and post matchmaking messages for a guild."""
        while True:
            try:
                # Retrieve guild-specific configurations
                json_url = await self.config.guild(guild).json_url()
                match_channel = await self.config.guild(guild).match_channel()
                match_thread = await self.config.guild(guild).match_thread()
                match_embed_id = await self.config.guild(guild).match_embed_id()
                json_interval = await self.config.guild(guild).json_interval()
                # REFACTOR THIS INTO send_player_update
                previous_players = await self.config.guild(guild).previous_players()
                log.debug(f"Fetched previous_players for guild '{guild.name}': {previous_players}")

                if not json_url:
                    log.warning(f"Guild '{guild.name}' is missing q3stat JSON URL.")
                    await asyncio.sleep(json_interval)
                    continue

                if match_thread:
                    target_channel = match_thread
                elif match_channel:
                    target_channel = match_channel
                else:
                    log.error(f"Neither thread nor channel is set.")
                    break

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
                    break

                # Save State
                current_state = data[0] # assumes first server in qstat.json
                previous_state = await self.config.guild(guild).current_state()
                # Set previous state
                await self.config.guild(guild).previous_state.set(previous_state)
                # Set current state
                await self.config.guild(guild).current_state.set(current_state)

                # CALL OTHER FUNCTIONS
                # Send or remove player messages
                await self.send_player_update(guild, current_state, previous_players, target_channel)

                # Call update embed function
                await self.update_server_embed(guild, current_state)

                # Wait for the next interval
                await asyncio.sleep(json_interval)

            except asyncio.CancelledError:
                log.info(f"Fetch task for guild '{guild.name}' has been cancelled.")
                break
            except Exception as e:
                log.error(f"Unexpected error in fetch task for guild '{guild.name}': {e}")
                await asyncio.sleep(60)  # Wait before retrying after unexpected errors

    ### SEND/REMOVE MESSAGES

    async def send_player_update(self, guild: discord.Guild, current_state: dict, previous_players: list, match_channel: int):
        """
        Process the JSON data to determine player join/leave events and send notifications.
        This function filters out players with a ping of 0, compares current and previous states,
        sends notifications to the designated thread (if set) or channel, and updates the previous player list.
        """
        players = current_state.get("players", [])
        # Filter out players with ping = 0 (bots)
        human_players = [player["name"] for player in players if player.get("ping", 0) > 0]
        log.debug(f"Human players for guild '{guild.name}': {human_players}")

        # Sort lists for consistent comparison
        human_players_sorted = sorted(human_players)
        previous_players_sorted = sorted(previous_players)
        log.debug(f"Sorted human_players_sorted: {human_players_sorted}")
        log.debug(f"Sorted previous_players_sorted: {previous_players_sorted}")

        # Detect new and old players
        new_players = list(set(human_players_sorted) - set(previous_players_sorted))
        old_players = list(set(previous_players_sorted) - set(human_players_sorted))
        log.debug(f"New players: {new_players}")
        log.debug(f"Old players: {old_players}")

        # Determine target channel or thread
        target_channel = guild.get_thread(match_channel)
        if not target_channel:
            # Fall back to the channel configured in match_channel.
            target_channel = guild.get_channel(match_channel)
            if not target_channel:
                log.error(f"Neither a valid thread nor a text channel found in guild '{guild.name}'.")
                return

        # Retrieve the join_messages mapping & cleanup setting from the guild config
        join_messages = await self.config.guild(guild).join_messages()
        match_cleanup = await self.config.guild(guild).match_cleanup()

        # Retrieve the role to mention (if any)
        noti_role = await self.config.guild(guild).noti_role()
        role_mention = ""
        if noti_role:
            role_obj = guild.get_role(noti_role)
            if role_obj:
                role_mention = f"{role_obj.mention} "

        # Send notifications for new players and save the join message ID in config
        if new_players:
            for player in new_players:
                try:
                    msg = await target_channel.send(f"{role_mention} 🔫 **{player}** has entered the arena!")
                    join_messages[player] = msg.id
                except discord.Forbidden:
                    log.error(f"Missing permissions to send messages in {target_channel} for guild '{guild.name}'.")
                except discord.HTTPException as http_exc:
                    log.error(f"HTTP error occurred while sending message in guild '{guild.name}': {http_exc}")
            # Save the updated join_messages mapping
            await self.config.guild(guild).join_messages.set(join_messages)

        # Process old players: if match_cleanup is enabled, delete their join message.
        if old_players:
            for player in old_players:
                if match_cleanup:
                    if player in join_messages:
                        msg_id = join_messages.pop(player)
                        try:
                            msg = await target_channel.fetch_message(msg_id)
                            await msg.delete()
                        except discord.NotFound:
                            log.error(f"Join message for player {player} not found in guild '{guild.name}'.")
                        except discord.Forbidden:
                            log.error(f"Missing permissions to delete message in {target_channel} for guild '{guild.name}'.")
                        except discord.HTTPException as http_exc:
                            log.error(f"HTTP error occurred while deleting message for player {player} in guild '{guild.name}': {http_exc}")
                    else:
                        log.warning(f"No join message recorded for player {player} in guild '{guild.name}'.")
                else:
                    try:
                        await target_channel.send(f"{role_mention} 🚫 **{player}** has left the arena!")
                    except discord.Forbidden:
                        log.error(f"Missing permissions to send exit message in {target_channel} for guild '{guild.name}'.")
                    except discord.HTTPException as http_exc:
                        log.error(f"HTTP error occurred while sending exit message for player {player} in guild '{guild.name}': {http_exc}")
            if match_cleanup:
                await self.config.guild(guild).join_messages.set(join_messages)

        # Update the previous players list
        await self.config.guild(guild).previous_players.set(human_players)
        log.debug(f"UPDATED player list: {human_players}")


    ### RETURN A SERVER EMBED BASED ON CURRENT STATE
    async def generate_server_embed(self, current_state: dict) -> discord.Embed:
        """Helper: Build and return an embed based on the current state data."""
        status_raw = current_state.get("status", "offline").lower()
        emoji = "🟢" if status_raw == "online" else "🔴"

        embed = discord.Embed(
            title=current_state.get("name", "Unknown Server"),
            description=f"{emoji} `{current_state.get('address', 'N/A')}`",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Players",
            value=f"{current_state.get('numplayers', 0)} / {current_state.get('maxplayers', 'N/A')}",
            inline=True
        )
        # Add Map in description if desired; here we use a field.
        embed.add_field(name="Map", value=current_state.get("map", "Unknown"), inline=True)
        embed.add_field(name="",value="",inline=True)

        # Build a ranked list of players (sorted by score)
        players = current_state.get("players", [])
        if players:
            sorted_players = sorted(players, key=lambda p: p.get("score", 0), reverse=True)
            score_lines = []
            player_lines = []
            for player in sorted_players:
                score = player.get("score", 0)
                name = player.get("name", "Unknown")
                if player.get("ping", 0) == 0:
                    # Format bot names in italics
                    name = f"_{name}_"
                else:
                    name = f"👤 **{name}**"
                    score = f"  **{str(score)}**"
                score_lines.append(str(score))
                player_lines.append(f"{name}")
            embed.add_field(name="Score", value="\n".join(score_lines), inline=True)
            embed.add_field(name="Name", value="\n".join(player_lines), inline=True)
            embed.add_field(name="",value="",inline=True)
        return embed
    
    ### UPDATE AN EXISTING SERVER EMBED
    async def update_server_embed(self, guild: discord.Guild, current_state: dict) -> None:
        """
        If a match_embed exists (message and channel IDs) in the guild config, update that message.
        If the message does not exist, reset match_embed_id and match_embed_channel in config to None.
        """
        match_embed_id = await self.config.guild(guild).match_embed_id()
        match_embed_channel = await self.config.guild(guild).match_embed_channel()
        if match_embed_id and match_embed_channel:
            channel = guild.get_channel(match_embed_channel)
            if not channel:
                log.warning(f"Channel with ID {match_embed_channel} not found in guild '{guild.name}'. Resetting embed config.")
                await self.config.guild(guild).match_embed_id.set(None)
                await self.config.guild(guild).match_embed_channel.set(None)
                return
            try:
                msg = await channel.fetch_message(match_embed_id)
                new_embed = await self.generate_server_embed(current_state)
                await msg.edit(embed=new_embed)
            except discord.NotFound:
                log.warning(f"Server info embed not found for guild '{guild.name}' (ID: {match_embed_id}). Resetting embed config.")
                await self.config.guild(guild).match_embed_id.set(None)
                await self.config.guild(guild).match_embed_channel.set(None)
            except Exception as e:
                log.error(f"Error updating server info embed in guild '{guild.name}': {e}")

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
            "qstat JSON URL": await self.config.guild(ctx.guild).json_url(),
            "Refresh Interval (in seconds)": await self.config.guild(ctx.guild).json_interval(),
            "Channel": ctx.guild.get_channel(await self.config.guild(ctx.guild).match_channel()),
            "Thread (Overrides Channel)": ctx.guild.get_thread(await self.config.guild(ctx.guild).match_thread()),
            "Minimum Players": await self.config.guild(ctx.guild).min_players(),
            "Notification Role": ctx.guild.get_role(await self.config.guild(ctx.guild).noti_role()),
            "Cleanup Messages": await self.config.guild(ctx.guild).match_cleanup(),
            "Nicks Registered": len(await self.config.guild(ctx.guild).nicks()),
        }
        
        embed = discord.Embed(
            title = ":pistol: q3stat Settings",
            color = 0xff2600
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
    async def role(self, ctx: commands.Context, role: discord.Role = None) -> None:
        """Mention a role in the notifications."""
        if role is not None:
            await self.config.guild(ctx.guild).noti_role.set(role.id)
            await ctx.send(success(f"`The notification role has been set to {role.name}.`"))
        else:
            await ctx.send(question("`Please mention a role or enter the Role ID.`"))

    @q3stat.command()
    async def channel(self, ctx: commands.Context, *, channel:discord.TextChannel = None) -> None:
        """Set channel where the messages are posted."""
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

    @q3stat.command()
    async def thread(self, ctx: commands.Context, *, thread: discord.Thread = None) -> None:
        """Set thread where the messages are posted. Overrides channel."""
        if thread:
            # Check if the bot has permission to send messages in the specified thread.
            permissions = thread.permissions_for(ctx.guild.me)
            if not permissions.send_messages:
                await ctx.send(error(f"`I don't have permission to send messages in {thread.mention}. Please adjust the thread permissions and try again.`"))
                return
            
            # Save the thread ID to the config
            await self.config.guild(ctx.guild).match_thread.set(thread.id)
            await ctx.send(success(f"`The matchmaking thread has been set to {thread}.`"))
        else:
            # if current thread exists, reset
            current_thread = await self.config.guild(ctx.guild).match_thread()
            if current_thread:
                await self.config.guild(ctx.guild).match_thread.set(None)
                await ctx.send(success("`The thread was reset to none.`"))
            else:
                await ctx.send(question("`Please mention a thread or enter the Thread ID.`"))

    @q3stat.command()
    async def cleanup(self, ctx: commands.Context, state: bool = None) -> None:
        """Toggle whether messages should be deleted when player leaves."""
        current_state = await self.config.guild(ctx.guild).match_cleanup()
        if state is None:
            new_state = not current_state
        else:
            new_state = state
        if new_state == current_state:
            await ctx.send(error(f"`Message cleanup is already {'on' if current_state else 'off'}.`"))
            return
        await self.config.guild(ctx.guild).match_cleanup.set(new_state)
        await ctx.send(success(f"`Message cleanup was turned {'on' if new_state else 'off'}.`"))
        return
    
    @commands.hybrid_command()
    async def q3info(self, ctx: commands.Context) -> None:
        """Display the server info embed."""
        current_state = await self.config.guild(ctx.guild).current_state()
        if not current_state:
            await ctx.send("No current state is set in the config!")
            return
        
        embed = await self.generate_server_embed(current_state)
        msg = await ctx.send(embed=embed)
        # Save both message ID and channel ID to config for later editing.
        await self.config.guild(ctx.guild).match_embed_id.set(msg.id)
        await self.config.guild(ctx.guild).match_embed_channel.set(ctx.channel.id)