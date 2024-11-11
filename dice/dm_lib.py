"""
Define Emojis as dictionary - references are specific to bot
"""
emojis = {
    "d20": "<:d20:1305617914736545893>",
    "d12": "<:d12:1305619847350194276>",
    "d10": "<:d10:1305619865859653652>",
    "d8": "<:d8:1305619884918439988>",
    "d6": "<:d6:1305619906481491998>",
    "d4": "<:d4:1305619929390645288>",
    "crit": "<:critSuccess:1305619823828402219>",
    "fail": "<:critFail:1305619808506744923>"
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
