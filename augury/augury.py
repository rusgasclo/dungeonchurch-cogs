from redbot.core import commands, checks, Config
from redbot.core.utils.chat_formatting import error, question, success
import pyhedrals
from openai import OpenAI
import discord
from discord import Embed
import re
import textwrap

class Augury(commands.Cog):
    """Perform augury ritual."""

    __author__ = "DM Brad"
    __version__ = "0.2"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=4206661044, force_registration=True
        )
        default_guild = {
            "npc": "A mysterious Deacon with burn marks all over their body and a long black robe who leads a dark cult watching over the fate of Pyora",
            "tools": "A black candle and bones carved with runes",
            "ritual": "Light the candle & roll the bones - the shadows they cast will reveal the answers",
            "vibe": "ominous dark fantasy",
            "temp": 0.7
        }
        self.config.register_guild(**default_guild)

    #
    # Command methods
    #
    @commands.hybrid_command()
    async def augury(self, ctx: commands.Context, *, question: str = None) -> None:
        """Cast augury as a ritual, get an answer from the gods
        
        A simple 1d4 roll to get the answer. Add an OpenAI API key and it transforms into an NPC who performs a ritual.
        """
        augury_answers: list[str] = [ # Possible answers from the gods
            "Woe",
            "Weal",
            "Woe & Weal",
            "No Response"
        ]
        dice_roller = pyhedrals.DiceRoller(
                maxDice=1,
                maxSides=4,
            )
        result = dice_roller.parse("1d4").result
        answer = augury_answers[result-1]
        key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")
        if key:
            prompt = f"""
            You will role play as a seer, a conduit to the gods for important questions:

            * You are: {await self.config.guild(ctx.guild).npc() }
            * Your divination tools: {await self.config.guild(ctx.guild).tools()}
            * The ritual: {await self.config.guild(ctx.guild).ritual()} 
            {'* The important question: ' + question if question else ''}
            * The god's answer: {answer}

            Return 2-3 sentences (present tense, third person) in a {await self.config.guild(ctx.guild).vibe()} style: role playing as this character & describing the ritualistic behavior that delivers the god's answer{' to the question ' + question if question else ""}.
            """
            prompt = textwrap.dedent(prompt).strip()
            client = OpenAI(api_key=key)
            completion = client.chat.completions.create(
                messages = [{"role":"user", "content": prompt}],
                model = "gpt-3.5-turbo",
                temperature = await self.config.guild(ctx.guild).temp()
            )
            pattern = re.compile(r'\b(Woe(?: &| and) Weal|' + '|'.join(map(re.escape, sorted(augury_answers, key=len, reverse=True))) + r')\b', re.IGNORECASE)
            text = pattern.sub(r'`\1`', completion.choices[0].message.content)
            text =  "\n".join(f"> {line}" for line in text.strip().splitlines())
            text = f"*{text}*"
            text += f"```The gods answered: {answer}```"

            embed = Embed(
                description = text,
                title = f":crystal_ball: {ctx.message.author.nick} asks: " + question.capitalize() if question else ":crystal_ball: Augury",
                color = 0xff0000
            )
            await ctx.send(embed=embed)
        else:
            roll_message = f":crystal_ball: {ctx.message.author.mention} appealed to the gods and they answered: `{answer}`"
            await ctx.send(roll_message)

    #
    # 
    #
    @commands.group()
    @checks.is_owner()
    async def augur(self, ctx: commands.Context):
        """Commands for changing the prompts used by augury."""
        pass

    @augur.command()
    async def settings(self, ctx: commands.Context) -> None:
        """Display the augur's current prompts."""
        key = (await self.bot.get_shared_api_tokens("openai")).get("api_key")
        setting_list = {
            "NPC Description": await self.config.guild(ctx.guild).npc(),
            "Divination Tools": await self.config.guild(ctx.guild).tools(),
            "The Ritual": await self.config.guild(ctx.guild).ritual(),
            "Vibe": await self.config.guild(ctx.guild).vibe(),
            "OpenAI API Key": "Yes" if {key} else "Not Set",
            "Prompt Temperature": await self.config.guild(ctx.guild).temp()
        }
        
        embed = discord.Embed(
            title = ":crystal_ball: Augury Settings",
            color = 0xff0000
        )
        for setting, value in setting_list.items():
            embed.add_field(name=setting, value=f"```{value}```", inline=False)
        await ctx.send(embed=embed)

    @augur.command()
    async def npc(self, ctx: commands.Context, *, prompt:str = None) -> None:
        """Change description of your augur NPC."""
        if prompt is not None:
            await self.config.guild(ctx.guild).npc.set(prompt)
            await ctx.send(success("The augur's NPC prompt was updated."))
        else:
            await ctx.send(question("Describe your augur NPC."))

    @augur.command()
    async def tools(self, ctx: commands.Context, *, prompt:str = None) -> None:
        """Change description of augur's divination tools"""
        if prompt is not None:
            await self.config.guild(ctx.guild).tools.set(prompt)
            await ctx.send(success("The augur's divination tool prompt was updated."))
        else:
            await ctx.send(question("Describe divination tools your augur uses for the ritual."))

    @augur.command()
    async def ritual(self, ctx: commands.Context, *, prompt:str = None) -> None:
        """Change description of augur's ritual"""
        if prompt is not None:
            await self.config.guild(ctx.guild).ritual.set(prompt)
            await ctx.send(success("The augur's ritual prompt was updated."))
        else:
            await ctx.send(question("Describe the ritual your augur performs."))

    @augur.command()
    async def vibe(self, ctx: commands.Context, *, prompt:str = None) -> None:
        """Change description of augur's vibe"""
        if prompt is not None:
            await self.config.guild(ctx.guild).vibe.set(prompt)
            await ctx.send(success("The augur's vibe was updated."))
        else:
            await ctx.send(question("Describe the vibe of the response you want."))

    @augur.command()
    async def temp(self, ctx: commands.Context, temperature:float) -> None:
        """Change the temperature of the response."""
        temperature = round(temperature, 1)
        if isinstance(temperature, float) and temperature >= 0.0 and temperature <= 1.0:
            await self.config.guild(ctx.guild).temp.set(temperature)
            await ctx.send(success(f"The prompt temperature was set to `{temperature}`"))
        else:
            await ctx.send(error("The temperature must be set to a float (decimal) between `0.0` and `1.0`"))