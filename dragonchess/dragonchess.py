import discord
from redbot.core import commands, Config
import pyhedrals

class DragonChess(commands.Cog):
    __author__ = "DM Brad"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot