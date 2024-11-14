"""
Define Emojis as dictionary - references are specific to bot
TODO - what is best way to share emojis between servers?
"""

church_channels: dict[str,int] = {
    "announcements":1153822115104051220,
    "chat":828777456898277399,
    "dnd-irl":838674459886878730,
    "dnd-vtt":1255609889535819826,
    "campign-planning":1200931885300330626,
    "bot-testing":841027677737189456,
    "server-log":1224934786234187776,
    "bot-spam":1252130121444360192,
    "no-players-allowed":1254210583818010816,
    "scrying-portal":1220458768647852213, # voice
    "vtt-session":1255751421005926482, # voice
    "dev-server":1305355121907073106
}

church_roles: dict[str,int] = {
    "dungeon master":828778265933643806,
    "dungeon organizer":1254211177571942481,
    "players":828778044767993868,
    "irl":1238600589164810240,
    "rsvp":1064993178471641138,
    "holding":1064993178471641138,
    "vtt":1238600715262234665,
    "vtt rsvp":1255726429010923530,
    "galmaarden":1302890296488628265,
    "scrying":1249115347651657728,
    "npcs":1280305840250818590,
    "mtg":1270544189246931038,
    "test":1306489682489511939 # dev server
}

emojis: dict[str,str] = {
    # on dev server
    "d20": "<:d20:1305725872346759238>",
    "d12": "<:d12:1305725832588820520>",
    "d10": "<:d10:1305725811797524561>",
    "d8": "<:d8:1305725772392042556>",
    "d6": "<:d6:1305725719652864030>",
    "d4": "<:d4:1305725696814878800>",
    "d2": "<:d2:1305725666649706537>",
    "crit": "<:critSuccess:1305725915854016512>",
    "fail": "<:critFail:1305725892965961799>",
    "eightball": ":8ball:",
    "beers": "<a:beerCheers:1306152939886481479>"
}

augury_answers: list[str] = [
    "Woe",
    "Weal",
    "Woe & Weal",
    "Nothing"
]

eightball_messages: list[str] = [
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

def prepend_emoji(match: str):
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
