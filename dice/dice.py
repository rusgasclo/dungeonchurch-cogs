"""
Dice cog for Red-DiscordBot by PhasecoreX.
Modified by DM Brad of WWW.DUNGEON.CHURCH for use with RPGs
"""

import asyncio
import re
from contextlib import suppress
from typing import ClassVar

import pyhedrals
from redbot.core import Config, checks, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import error, question, success
from redbot.core.utils.predicates import MessagePredicate

from .pcx_lib import SettingDisplay
from .dm_lib import emojis, prepend_emoji

MAX_ROLLS_NOTIFY = 1000000
MAX_MESSAGE_LENGTH = 2000

class Dice(commands.Cog):
    """Perform complex dice rolling."""

    __author__ = "PhasecoreX & DM Brad"
    __version__ = "2.1.0.1"

    default_global_settings: ClassVar[dict[str, int]] = {
        "max_dice_rolls": 10000,
        "max_die_sides": 10000,
        "randstats_max": 78,
        "randstats_min": 66
    }
    DROPPED_EXPLODED_RE = re.compile(r"-\*(\d+)\*-")
    EXPLODED_RE = re.compile(r"\*(\d+)\*")
    DROPPED_RE = re.compile(r"-(\d+)-")

    def __init__(self, bot: Red) -> None:
        """Set up the cog."""
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=1224364861, force_registration=True
        )
        self.config.register_global(**self.default_global_settings)

    #
    # Red methods
    #

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Show version in help."""
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n\nCog Version: {self.__version__}"

    async def red_delete_data_for_user(self, *, _requester: str, _user_id: int) -> None:
        """Nothing to delete."""
        return

    #
    # Command methods: diceset
    #

    @commands.group()
    @checks.is_owner()
    async def diceset(self, ctx: commands.Context) -> None:
        """Manage Dice settings."""

    @diceset.command()
    async def settings(self, ctx: commands.Context) -> None:
        """Display current settings."""
        global_section = SettingDisplay("Global Settings")
        global_section.add(
            "Maximum number of dice to roll at once", await self.config.max_dice_rolls()
        )
        global_section.add("Maximum sides per die", await self.config.max_die_sides())
        await ctx.send(str(global_section))

    @diceset.command()
    async def rolls(self, ctx: commands.Context, maximum: int) -> None:
        """Set the maximum number of dice a user can roll at one time.

        More formally, the maximum number of random numbers the bot will generate for any one dice calculation.

        Warning:
        -------
        Setting this too high will allow other users to slow down/freeze/crash your bot!
        Generating random numbers is easily the most CPU consuming process here,
        so keep this number low (less than one million, and way less than that on a Pi)

        """
        action = "is already set at"
        if maximum == await self.config.max_dice_rolls():
            pass
        elif maximum > MAX_ROLLS_NOTIFY:
            pred = MessagePredicate.yes_or_no(ctx)
            await ctx.send(
                question(
                    f"Are you **sure** you want to set the maximum rolls to {maximum}? (yes/no)\n"
                    "Setting this over one million will allow other users to slow down/freeze/crash your bot!"
                )
            )
            with suppress(asyncio.TimeoutError):
                await ctx.bot.wait_for("message", check=pred, timeout=30)
            if pred.result:
                await self.config.max_dice_rolls.set(maximum)
                action = "is now set to"
            else:
                await ctx.send(
                    error(
                        f"Maximum dice rolls per user has been left at {await self.config.max_dice_rolls()}"
                    )
                )
                return
        else:
            await self.config.max_dice_rolls.set(maximum)
            action = "is now set to"

        await ctx.send(
            success(
                f"Maximum dice rolls per user {action} {await self.config.max_dice_rolls()}"
            )
        )

    @diceset.command()
    async def sides(self, ctx: commands.Context, maximum: int) -> None:
        """Set the maximum number of sides a die can have.

        Python seems to be pretty good at generating huge random numbers and doing math on them.
        There should be sufficient safety checks in place to mitigate anything getting too crazy.
        But be honest, do you really need to roll multiple five trillion sided dice at once?
        """
        await self.config.max_die_sides.set(maximum)
        await ctx.send(
            success(
                f"Maximum die sides is now set to {await self.config.max_die_sides()}"
            )
        )
    
    @diceset.command(name="randstats_max")
    async def randstats_max(self, ctx: commands.Context, new_value: int = None):
        """Define maximum total value of randstats array.
        
        A standard array is 72 total points. This defines the upper limit of the range that is allowed to be rolled.
        """   
        current_max = await self.config.randstats_max()
        current_min = await self.config.randstats_min()
        if new_value < current_min:
            await ctx.send(f"You have to set the new max to be greater than the current min of `{current_min}`.")
            return
        else:
            await self.config.randstats_max.set(new_value)
            await ctx.send(f"The maximum for randstats has been changed from `{current_max}` to `{new_value}`")

    @diceset.command(name="randstats_min")
    async def randstats_min(self, ctx: commands.Context, new_value: int = None):
        """Define minimum total value of randstats array.
        
        A standard array is 72 total points. This defines the lower limit of the range that is allowed to be rolled.
        """   
        current_max = await self.config.randstats_max()
        current_min = await self.config.randstats_min()
        if new_value > current_max:
            await ctx.send(f"You have to set the new min to be greater than the current max of `{current_max}`.")
            return
        else:
            await self.config.randstats_min.set(new_value)
            await ctx.send(f"The minimum for randstats has been changed from `{current_min}` to `{new_value}`")

    #
    # Command methods
    #

    @commands.hybrid_command()
    async def qr(self, ctx: commands.Context) -> None:
        """ Quick roll 1d20 """
        dice_roller = pyhedrals.DiceRoller(
                maxDice=await self.config.max_dice_rolls(),
                maxSides=await self.config.max_die_sides(),
            )
        result = dice_roller.parse("1d20").result
        roll_message = f"{emojis['d20']} {ctx.message.author.mention} rolled **1d20** and got `{result}`"
        await ctx.send(roll_message)

    @commands.hybrid_command()
    async def dis(self, ctx: commands.Context) -> None:
        """ Roll 2d20 with disadvantage """
        dice_roller = pyhedrals.DiceRoller(
            maxDice=await self.config.max_dice_rolls(),
            maxSides=await self.config.max_die_sides(),
        )  
        roll = dice_roller.parse("2d20dh")
        first_roll, second_roll = [die.value for die in roll.rolls[0].rolls]
        if first_roll == roll.result:
            first_roll = str(f"`{first_roll}`")
            second_roll = str(f"~~ {second_roll} ~~")
        else:
            second_roll = str(f"`{second_roll}`")
            first_roll = str(f"~~ {first_roll} ~~")         
        roll_message = f"{emojis['fail']} {ctx.message.author.mention} rolled **2d20dh** and got {first_roll} {second_roll}"
        await ctx.send(roll_message)

    @commands.hybrid_command()
    async def adv(self, ctx: commands.Context) -> None:
        """ Roll 2d20 with advantage """
        dice_roller = pyhedrals.DiceRoller(
            maxDice=await self.config.max_dice_rolls(),
            maxSides=await self.config.max_die_sides(),
        )  
        roll = dice_roller.parse("2d20dl")
        first_roll, second_roll = [die.value for die in roll.rolls[0].rolls]
        if first_roll == roll.result:
            first_roll = str(f"`{first_roll}`")
            second_roll = str(f"~~ {second_roll} ~~")
        else:
            second_roll = str(f"`{second_roll}`")
            first_roll = str(f"~~ {first_roll} ~~")         
        roll_message = f"{emojis['crit']} {ctx.message.author.mention} rolled **2d20dl** and got {first_roll} {second_roll}"
        await ctx.send(roll_message)

    @commands.hybrid_command()
    async def randstats(self, ctx: commands.Context) -> None:
        """ Roll random Ability Scores
        Roll 4d6 six times, drop the lowest, and sum each.
        """
        try:
            dice_roller = pyhedrals.DiceRoller(
                maxDice=await self.config.max_dice_rolls(),
                maxSides=await self.config.max_die_sides(),
            )
            min_total = await self.config.randstats_min()
            max_total = await self.config.randstats_max()
            total = 0
            roll_message = ""
            # Roll until the total is within the min and max range
            while total <= min_total or total >= max_total:
                total = 0
                roll_message = ""
                for _ in range(6):
                    result = dice_roller.parse("4d6dl")
                    roll_message += f"> {emojis['d6']} {list(result.rolls)[0]}\n"
                    total += result.result

                # Format the roll message for readability
                roll_message = roll_message.replace(",", ", ")  # fix commas
                roll_message = re.sub(r'(\b\d+d(20|12|10|8|6|4)):', r'**\1**:', roll_message)  # bold dice notation
                roll_message = self.DROPPED_RE.sub(r"~~\1~~", roll_message)  # strike dropped
                roll_message = re.sub(r'\((\d+)\)', r'= `\1`', roll_message)  # = result
        
            # Prepend provenance if using text command
            if not ctx.interaction: 
                await ctx.message.delete()
                roll_message = f":crossed_swords: {ctx.message.author.mention} rolled Ability Scores:\n" + roll_message
            roll_message += f"**=** `{total}`"  # append total
            
            await ctx.send(roll_message)
        except (
            ValueError,
            NotImplementedError,
            pyhedrals.InvalidOperandsException,
            pyhedrals.SyntaxErrorException,
            pyhedrals.UnknownCharacterException,
        ) as exception:
            error_message = (
                f"{ctx.author.mention}, something went wrong:\n`{exception!s}`"
            )
            if ctx.interaction:
                await ctx.send(error_message, ephemeral=True)
            else:
                await ctx.send(error_message)

    @commands.hybrid_command()
    async def roll(self, ctx: commands.Context, *, roll: str) -> None:
        """Perform die roll based on a dice formula.

        The [PyHedrals](https://github.com/StarlitGhost/pyhedrals) library is used for dice formula parsing.
        Use the link above to learn the notation allowed. Below are a few examples:

        `2d20kh` - Roll 2d20, keep highest die (e.g. initiative advantage)
        `4d4!+2` - Roll 4d4, explode on any 4s, add 2 to result
        `4d6rdl` - Roll 4d6, reroll all 1s, then drop the lowest die
        `6d6c>4` - Roll 6d6, count all dice greater than 4 as successes
        `10d10r<=2kh6` - Roll 10d10, reroll all dice less than or equal to 2, then keep the highest 6 dice

        Modifier order does matter, and usually they allow for specifying a specific number or number ranges after them.
        """
        try:
            dice_roller = pyhedrals.DiceRoller(
                maxDice=await self.config.max_dice_rolls(),
                maxSides=await self.config.max_die_sides(),
            )
            result = dice_roller.parse(roll)
            # Roll Message
            roll_message = f"{ctx.message.author.mention} rolled `{roll}`" # prepend provenance
            if not ctx.interaction: # if using [p] text command
                await ctx.message.delete() # delete triggering message
            if len(roll_message) > MAX_MESSAGE_LENGTH:
                roll_message = f"{ctx.message.author.mention} roll = `{result.result}`"
            if len(roll_message) > MAX_MESSAGE_LENGTH:
                await ctx.send(
                    error(
                        f"{ctx.message.author.mention}, I can't give you the result of that roll as it doesn't fit in a Discord message"
                    )
                )
                return
            # Format roll log
            roll_log = "\n ".join(list(result.strings()))
            roll_log = self.DROPPED_EXPLODED_RE.sub(r"~~**\1!**~~", roll_log)
            roll_log = self.EXPLODED_RE.sub(r"**\1!**", roll_log)
            roll_log = self.DROPPED_RE.sub(r"~~\1~~", roll_log)
            roll_log = roll_log.replace(",", "+")
            roll_log = re.sub(r'(\b\d+d(20|12|10|8|6|4|2)):', r'**\1**:', roll_log) # bold dice notation
            roll_log = re.sub(r'\((\d+)\)', r'= \1', roll_log) # = result
            # emojis at beginning of line
            roll_log = re.sub(r'\*\*(\d+(d(20|12|10|8|6|4|2)))\*\*:', prepend_emoji, roll_log)
            # format into quotes
            roll_log = roll_log.replace("\n","\n>")
            roll_log = "\n> " + roll_log # add quote to beginning
            # result line
            result_string = f"\n** = `{result.result}`**"
            if len(roll_message) + len(roll_log) > MAX_MESSAGE_LENGTH:
                roll_log = "> *(Roll log too long to display)*"
            await ctx.send(f"{roll_message} {roll_log} {result_string}")
        except (
            ValueError,
            NotImplementedError,
            pyhedrals.InvalidOperandsException,
            pyhedrals.SyntaxErrorException,
            pyhedrals.UnknownCharacterException,
        ) as exception:
            # Check if the context is from an interaction (slash command)
            if ctx.interaction:
                await ctx.send(
                    error(
                        f"{ctx.author.mention}, I couldn't parse your [dice formula](<https://pypi.org/project/pyhedrals/>):\n`{exception!s}`"
                    ),
                    ephemeral=True
                )
            else:
                await ctx.send(
                    error(
                        f"{ctx.author.mention}, I couldn't parse your [dice formula](<https://pypi.org/project/pyhedrals/>):\n`{exception!s}`"
                    )
                )