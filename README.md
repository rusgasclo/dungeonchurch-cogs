<p align="center">
    <img width="650" src="logo-chrome-red.png">
</p>

# Dungeon Church Cogs
[Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot/releases) cogs for [Dungeon Church](https://www.dungeon.church).

Focused on RPG & D&D related things, ideas or pull requests welcome.

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
## augury
A simple fortune teller roller that transforms into a customizable NPC ritual when you add an OpenAI API key.
* `/augury` make an appeal to the gods
## 🔒 churchmod
Automation and moderation for our private server.
## dice
Forked from [PCXCogs](https://github.com/PhasecoreX/PCXCogs). I added better formatting, emojis, and some extra commands for RPG players.
* `/roll` roll complicated [dice formulas](https://github.com/StarlitGhost/pyhedrals)
* `/qr [mod]` quick roll 1d20
* `/adv [mod]` quick roll 2d20dl
* `/dis [mod]` quick roll 2d20dh
* `/randstats` roll ability scores within a set range
* `/flipcoin` flip a coin, get heads or tails
* `/eightball` ask the Magic 8 Ball
* `/diceset` to change settings
## randomstatus
Make a list of status activities, then cycle through them randomly or sequentially at a set interval.
* `/randomstatus` to change settings