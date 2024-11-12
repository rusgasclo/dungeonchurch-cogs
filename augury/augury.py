from redbot.core import commands
import pyhedrals
#from openai import OpenAI
from .dm_lib import augury_answers

class Augury(commands.Cog):
    """Perform augury ritual."""

    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot

    #
    # Command methods
    #
    @commands.hybrid_command()
    async def augury(self, ctx: commands.Context) -> None:
        """Cast augury as a ritual, get an answer from the gods"""
        dice_roller = pyhedrals.DiceRoller(
                maxDice=1,
                maxSides=4,
            )
        result = dice_roller.parse("1d4").result
        answer = augury_answers[result-1]
        roll_message = f":crystal_ball: {ctx.message.author.mention} appealed to the gods and they answered: `{answer}`"
        await ctx.send(roll_message)
        if not ctx.interaction: # if using [p] text command
            await ctx.message.delete() # delete triggering message