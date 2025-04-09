<p align="center">
    <img width="650" src="logo-chrome-red.png"><br>
    <a href=https://github.com/oakbrad/dungeonchurch>
        <img src=https://img.shields.io/github/last-commit/oakbrad/dungeonchurch?label=dungeonchurch&color=gray&labelColor=ff2600&logo=github>
    </a>
    <a href=https://github.com/oakbrad/dungeonchurch-pyora>
        <img src=https://img.shields.io/github/last-commit/oakbrad/dungeonchurch-pyora?label=dungeonchurch-pyora&color=gray&labelColor=ff2600&logo=github>
    </a>
    <a href=https://github.com/oakbrad/dungeonchurch-cogs>
        <img src=https://img.shields.io/github/last-commit/oakbrad/dungeonchurch-cogs?label=dungeonchurch-cogs&color=gray&labelColor=ff2600&logo=github>
    </a>
</p>

# Dungeon Church Cogs
[Red-DiscordBot](https://github.com/Cog-Creators/Red-DiscordBot/releases) cogs by the [Dungeon Church](https://www.dungeon.church) RPG group.

Focused on making RPG, D&D, & game related cogs - ideas or pull requests welcome.

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

For cogs that have LLM integration, set the OpenAPI key in Red:

```
[p]set api openai api_key,<paste here>
```

# Cogs
Current cogs and their commands. `[p]` is your bot prefix, `/` slash commands indicate a hybrid command. To register slash commands, first load the cog, then list the commands available. Enable the commands you want to register, then sync them with Discord.
```
[p]slash list
[p]slash enable <command>
[p]slash sync
```
## augury
A simple roller that transforms into a customizable NPC when you add an OpenAI API key.
* `/augury` make an appeal to the gods
* `[p]augur` to change settings
## dice
Forked from [PCXCogs](https://github.com/PhasecoreX/PCXCogs). I added better formatting and commands useful for RPG players, including contested rolls.
* `/roll` roll complicated [dice formulas](https://github.com/StarlitGhost/pyhedrals)
* `/qr [mod] [@challenge]` quick roll 1d20
* `/adv [mod]` quick roll 2d20dl
* `/dis [mod]` quick roll 2d20dh
* `/randstats` roll ability scores within a set range
* `/flipcoin` flip a coin, get heads or tails
* `/eightball` ask the Magic 8 Ball
* `[p]diceset` to change settings
## q3stat
Quake III Arena [server](https://quake.dungeon.church) notifications with [qstat](https://github.com/Unity-Technologies/qstat). Run qstat via crontab on your server to output JSON to a publicly accessible file:
```
qstat -json -P -q3s dungeon.church:27960 > /var/www/html/qstat.json
```
* `[p]q3stat` to set the URL of that file & notification options.
## randomstatus
Make a list of status activities, then cycle through them randomly or sequentially at a set interval.
* `[p]randomstatus` to change settings 