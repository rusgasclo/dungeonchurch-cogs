"""
DUNGEON CHURCH

Classes for interactive elements of contests.
"""

from discord.ui import Button, View, Modal, TextInput
from redbot.core.utils.chat_formatting import error, question, success
from .dm_lib import emojis
import discord

class ContestedRollModal(Modal):
    def __init__(self, challenger, challenged, ctx, dice_roller, initial_result, total, message):
        super().__init__(title="Submit Your Modifier")
        self.challenger = challenger
        self.challenged = challenged
        self.ctx = ctx
        self.dice_roller = dice_roller
        self.initial_result = initial_result
        self.total = total
        self.message = message

        self.modifier = TextInput(
            label="Enter modifier:",
            placeholder="0",
            required=False,
            style=discord.TextStyle.short
        )
        self.add_item(self.modifier)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mod_input = self.children[0].value
            modifier = int(mod_input) if mod_input else 0 # default to 0 if left blank in modal
            challenger_modifier = self.total - self.initial_result
            # Parse and roll for the challenged user
            challenged_result = self.dice_roller.parse("1d20").result
            challenged_total = challenged_result + modifier
            
            # Update the message with both results
            new_content = (
                f"### {self.challenger.mention} vs {interaction.user.mention}!\n\n"
                f"> ✅ **{self.challenger.display_name}** rolled **1d20{f'+{challenger_modifier}' if challenger_modifier != 0 else ''}** and got `{self.total}`.\n"
                f"> ❌ **{interaction.user.display_name}** rolled **1d20{f'+{modifier}' if modifier != 0 else ''}** and got `{challenged_total}`.\n"
                f"## {'🤝 Draw!' if self.total == challenged_total else (f'👑 {self.challenger.display_name} Won!' if self.total > challenged_total else f'👑 {self.challenged.display_name} Won!')}"
            )
            await self.message.edit(content=new_content, view=None)  # Remove the button
            await interaction.response.defer() # Acknowledge submission
        except Exception as e:
            await interaction.response.send_message(error(f"Error: {str(e)}", ephemeral=True))

class ContestedRollButton(Button):
    def __init__(self, challenger, challenged, ctx, dice_roller, initial_result, total):
        super().__init__(label=f"{challenged.nick}'s Roll!", style=discord.ButtonStyle.primary)
        self.challenger = challenger
        self.challenged = challenged
        self.ctx = ctx
        self.dice_roller = dice_roller
        self.initial_result = initial_result
        self.total = total

    async def callback(self, interaction: discord.Interaction):
        # Ensure only the challenged user can press the button
        if interaction.user.id != self.challenged.id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return

        # Open the modal for the challenged user
        modal = ContestedRollModal(
            challenger=self.challenger,
            challenged=self.challenged,
            ctx=self.ctx,
            dice_roller=self.dice_roller,
            initial_result=self.initial_result,
            total=self.total,
            message=self.view.message,
        )
        await interaction.response.send_modal(modal)

class ContestedRollView(View):
    def __init__(self, challenger, challenged, ctx, dice_roller, initial_result, total):
        super().__init__(timeout=None)
        self.message = None
        self.add_item(ContestedRollButton(challenger, challenged, ctx, dice_roller, initial_result, total))

    def set_message(self, message):
        self.message = message