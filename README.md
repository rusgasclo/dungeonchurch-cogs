<p align="center">
    <img width="650" src="https://raw.githubusercontent.com/oakbrad/dungeonchurch/refs/heads/main/logo-chrome.png">
</p>

[Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot/releases) cogs for my D&D [RPG group](https://www.dungeon.church).

----
To add these cogs to your instance, run this command first (`[p]` is your bot prefix):

```
[p]repo add dungeonchurch https://github.com/oakbrad/dungeonchurch-cogs
```

Then install your cog(s) of choice:

```
[p]cog install dungeonchurch <cog_name>
```

Finally, load your cog(s):

```
[p]load <cog_name>
```

# Cogs
## dice
Forked from [PCXCogs](https://github.com/PhasecoreX/PCXCogs), I added better formatting, emojis, and some extra commands for RPG players.
* `/roll` roll complicated [dice formulas](https://github.com/StarlitGhost/pyhedrals)
* `/randstats` roll ability scores within a set range
* `/qr [mod]` quick roll 1d20
* `/adv [mod]` quick roll 2d20dl
* `/dis [mod]` quick roll 2d20dh
* `/flipcoin` roll 1d2, get heads or tails
## randomstatus
Make a list of status activities, then cycle through them randomly or sequentially at a set interval.