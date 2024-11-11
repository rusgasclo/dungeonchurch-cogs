"""
Define Emojis as dictionary - references are specific to bot
TODO - what is best way to share emojis between servers?
"""
emojis = {
    "d20": "<:d20:1239474402526232657>",
    "d12": "<:d12:1239474400567234593>",
    "d10": "<:d10:1239474403721478205>",
    "d8": "<:d8:1239474399376183307",
    "d6": "<:d6:1239474405059465286>",
    "d4": "<:d4:1239474397392146483>",
    "crit": "<:critSuccess:1239474395865550888>",
    "fail": "<:critFail:1239474398579134535>"
}
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
