import discord
from redbot.core import commands, Config
from discord.ext import tasks
import random 

class RandomStatus(commands.Cog):
    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=4206661091)
        # default settings
        default_global = {
            "status_messages": [
                ("playing", "D&D"),
                ("watching", "Pyora grow"),
                ("listening", "fiendish whispers"),
                ("competing", "dice rolling"),
            ],
            "random_order": True,
            "interval": 900 # fifteen minutes
        }
        self.config.register_global(**default_global)

        self.status_messages = []
        self.interval = 900  # Default value until loaded
        self.update_status.start()  # Start the background task

    async def cog_load(self):
        # Load status messages from config
        self.status_messages = await self.config.status_messages()
        self.interval = await self.config.interval()
        # Restart the loop with the new interval
        self.update_status.change_interval(seconds=self.interval)
    
    def cog_unload(self):
        # Stop the background task when the cog is unloaded
        self.update_status.cancel()
        self.bot.loop.create_task(self.bot.change_presence(activity=None))

    @tasks.loop(seconds=900)  # Initial interval, but will be updated in cog_load
    async def update_status(self):
        # Randomly select an activity from the stored list
        activity_type_str, message = random.choice(self.status_messages)
        # Map activity type string to discord.ActivityType
        activity_type = getattr(discord.ActivityType, activity_type_str, discord.ActivityType.playing)
        # Set the activity presence
        activity = discord.Activity(type=activity_type, name=message)
        await self.bot.change_presence(activity=activity)

    @update_status.before_loop
    async def before_update_status(self):
        # Wait until the bot is fully ready before starting the task
        await self.bot.wait_until_ready()

    # COMMANDS
    # Define command group
    @commands.group(name="randomstatus")
    async def randomstatus(self, ctx):
        """Commands for managing random status updates."""

    @randomstatus.command(name="interval")
    async def interval(self, ctx, seconds: int = None):
        """Set interval for status update (in seconds)"""
        if seconds is None:
            current_interval = await self.config.interval()
            await ctx.send(f"The current interval is set to `{current_interval}`")
            return
        if seconds < 60:
            await ctx.send("Please choose an interval of at least 60 seconds.")
            return
        # Save the new interval to config and update the loop interval
        await self.config.interval.set(seconds)
        self.update_status.change_interval(seconds=seconds)
        await ctx.send(f"Status update interval set to {seconds} seconds.")

    @randomstatus.command(name="list")
    async def list(self, ctx):
        """List all status activities"""
        status_messages = await self.config.status_messages()
        if not status_messages:
            await ctx.send("There are no status messages configured.")
            return        
        # Format each message with a number and display it
        formatted_list = "\n".join(
            f"{i + 1}. `{self._format_activity_type(activity_type)}` {message}"
            for i, (activity_type, message) in enumerate(status_messages)
        )
        await ctx.send(f"## Configured Status Messages:\n{formatted_list}")

    @randomstatus.command(name="remove")
    async def remove(self, ctx, index: int):
        """Remove status by list number"""
        status_messages = await self.config.status_messages()
        if index < 1 or index > len(status_messages):
            await ctx.send("Invalid number. Choose one from `[p]randomstatus list`")
            return
        removed_message = status_messages.pop(index - 1) # Account for zero index
        await self.config.status_messages.set(status_messages)
        await ctx.send(f"Removed status `{self._format_activity_type(removed_message[0])} {removed_message[1]}`.")

    @randomstatus.command(name="add")
    async def add(self, ctx, activity: str, *, message: str):
        """Add a new status activity"""
        valid_activities = {"playing", "watching", "listening", "competing"}
        if activity.lower() not in valid_activities:
            await ctx.send(f"Invalid activity type. Choose from: {', '.join(f'`{activity}`' for activity in valid_activities)}")
            return
        message = message[:128] # maximum status length
        async with self.config.status_messages() as status_messages:
            status_messages.append((activity.lower(), message))
        # Confirm the addition to the user
        await ctx.send(f"Added new status: `{self._format_activity_type(activity)}` {message}")

    @randomstatus.command(name="order")
    async def order(self, ctx, set: bool = None):
        """Toggle/set random or sequential order"""
        if set is not None:
            await self.config.random_order.set(set)
            order_type = "random" if set else "sequential"
            await ctx.send(f"Status updates order set to `{order_type}` order.")
        else:
            current_setting = await self.config.random_order()
            new_setting = not current_setting
            await self.config.random_order.set(new_setting)
            order_type = "random" if new_setting else "sequential"
            await ctx.send(f"Status updates will now follow `{order_type}` order.")

    def _format_activity_type(self, activity_type):
        """Format the activity type to reflect displayed"""
        if activity_type == "listening":
            return "Listening to"
        elif activity_type == "competing":
            return "Competing in"
        else:
            return activity_type.capitalize()