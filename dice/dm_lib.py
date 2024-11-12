"""
Define Emojis as dictionary - references are specific to bot
TODO - what is best way to share emojis between servers?
"""
emojis = {
    "d20": "<:d20:1305725872346759238>",
    "d12": "<:d12:1305725832588820520>",
    "d10": "<:d10:1305725811797524561>",
    "d8": "<:d8:1305725772392042556>",
    "d6": "<:d6:1305725719652864030>",
    "d4": "<:d4:1305725696814878800>",
    "d2": "<:d2:1305725666649706537>",
    "crit": "<:critSuccess:1305725915854016512>",
    "fail": "<:critFail:1305725892965961799>",
    "eightball": ":8ball:"
}

eightball_messages = [
    "It is certain",
    "It is decidely so",
    "Without a doubt",
    "Yes, definitely",
    "You may rely on it",
    "As I see it, yes",
    "Most likely",
    "Outlook good",
    "Yes",
    "Signs point to yes",
    "Reply hazy, try again",
    "Ask again later",
    "Better not tell you",
    "Cannot predict now",
    "Concentrate and ask again",
    "Don't count on it",
    "My reply is no",
    "My sources say no",
    "Outlook not so good",
    "Very doubtful"
]

def prepend_emoji(match):
    """
    Prepend dice emoji to a string
    match needs to be a die, ie: d20, d10
    """
    # Extract the full dice notation (e.g., "2d10" or "1d6") and the dice type
    full_notation = match.group(1)  # e.g., "2d10" or "1d6"
    dice_type = match.group(2)      # e.g., "d10" or "d6"
    # Look up the emoji based on the dice type
    emoji = emojis.get(dice_type, "")
    # Return the line with the emoji prepended
    return f"{emoji} **{full_notation}**:"
