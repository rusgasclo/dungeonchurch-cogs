import discord
import random
import re
import csv
from typing import List, Tuple, Dict, Any
from redbot.core import commands, Config

ENTRY_RE = re.compile(r'^\s*(?:"([^"]+)"|([^:]+))\s*(?::\s*([sS]?\s*[+-]?\d+))?\s*$')

class InitiativeTracker(commands.Cog):
    """Track initiative order for combat encounters."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        self.config.register_guild(init_order=[])

    # --- helpers ----------------------------------------------------------------

    def _require_guild(self, ctx) -> bool:
        if ctx.guild is None:
            return False
        return True

    def _format_line(self, e: Dict[str, Any]) -> str:
        if e.get("forced"):
            die = "?" if e.get("die") is None else str(e["die"])
            return f"{e['display']}: {e['total']} (S{die} forced, modifier ignored)"
        die = "?" if e.get("die") is None else str(e["die"])
        mod = f"+{e['mod']}" if e.get("mod", 0) >= 0 else str(e.get("mod", 0))
        return f"{e['display']}: {e['total']} (Dice:{die} Mod:{mod})"

    def _normalize_stored(self, stored: List[Any]) -> List[Dict[str, Any]]:
        normalized = []
        for e in stored:
            if isinstance(e, dict):
                name = e.get("name", re.sub(r'\*', '', str(e.get("display", ""))).strip())
                display = e.get("display", str(e.get("name", "")))
                normalized.append({
                    "name": name,
                    "base_name": re.sub(r'\s#\d+$', '', name),
                    "display": display,
                    "mod": e.get("mod", 0),
                    "die": e.get("die"),
                    "total": e.get("total"),
                    "forced": e.get("forced", False),
                })
            elif isinstance(e, (list, tuple)) and len(e) >= 2:
                name = re.sub(r'\*', '', str(e[0])).strip()
                normalized.append({
                    "name": name,
                    "base_name": re.sub(r'\s#\d+$', '', name),
                    "display": e[0],
                    "mod": 0,
                    "die": None,
                    "total": e[1],
                    "forced": False,
                })
        return normalized

    def _parse_value(self, raw_val: str) -> Tuple[int, bool, int]:
        """Return (mod, forced, numeric). forced True => numeric is final total."""
        if raw_val is None:
            return 0, False, -1
        v = raw_val.replace(" ", "")
        if not v:
            return 0, False, -1
        if v[0] in ("s", "S"):
            try:
                n = int(v[1:])
            except Exception:
                n = random.randint(1, 20)
            return 0, True, n
        try:
            return int(v), False, -1
        except Exception:
            return 0, False, -1

    def parse_combatants(self, raw: str, is_player: bool) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Expect comma-separated entries: Name: value, ...
        Value optional, defaults to 0. S<number> forces total. Quoted names allowed.
        Returns (combatants, warnings)
        """
        try:
            entries = next(csv.reader([raw], skipinitialspace=True))
        except Exception:
            entries = [e.strip() for e in raw.split(",")]

        combatants = []
        warnings: List[str] = []
        counts: Dict[str, int] = {}

        for entry in entries:
            if not entry:
                continue
            m = ENTRY_RE.match(entry)
            if not m:
                continue
            raw_name = (m.group(1) or m.group(2) or "").strip()
            val = m.group(3)
            norm = raw_name.lower()
            counts.setdefault(norm, 0)
            counts[norm] += 1
            suffix = f" #{counts[norm]}" if counts[norm] > 1 else ""
            if counts[norm] > 1:
                warnings.append(f"Duplicate name '{raw_name}' renamed to '{raw_name + suffix}'")
            name = raw_name + suffix

            mod, forced, forced_val = self._parse_value(val)
            if forced:
                total = forced_val
                die = forced_val
            else:
                die = random.randint(1, 20)
                total = die + mod

            display = f"**{name}**" if is_player else name
            combatants.append({
                "name": name,
                "display": display,
                "mod": mod,
                "die": die,
                "total": total,
                "forced": forced,
            })
        return combatants, warnings

    # --- commands ----------------------------------------------------------------

    @commands.hybrid_command()
    async def rollinit(self, ctx, *, args: str):
        """Roll initiative using 'Player: Dex mod, Player2: S20 (S sets roll result) | Enemy: +6' (commas required)."""
        if not self._require_guild(ctx):
            await ctx.send("❌ This command must be used in a server (not in DMs).")
            return

        try:
            players_raw, enemies_raw = args.split("|", 1)
        except ValueError:
            await ctx.send("❌ Please separate players and enemies with a '|'.")
            return

        players, pw = self.parse_combatants(players_raw, True)
        enemies, ew = self.parse_combatants(enemies_raw, False)
        warnings = pw + ew
        all_combatants = sorted(players + enemies, key=lambda x: x["total"], reverse=True)

        await self.config.guild(ctx.guild).init_order.set(all_combatants)
        if warnings:
            await ctx.send("⚠️ Duplicates handled:\n" + "\n".join(warnings))
        if not all_combatants:
            await ctx.send("⚠️ No valid combatants parsed. Check your input format.")
            return

        await ctx.send("🎲 **Initiative Order:**\n" + "\n".join(self._format_line(c) for c in all_combatants))

    @commands.hybrid_command()
    async def checkinit(self, ctx):
        """Show current initiative order."""
        if not self._require_guild(ctx):
            await ctx.send("❌ This command must be used in a server (not in DMs).")
            return
        stored = await self.config.guild(ctx.guild).init_order()
        normalized = self._normalize_stored(stored)
        if not normalized:
            await ctx.send("⚠️ No initiative order has been set.")
            return
        await ctx.send("📋 **Current Initiative Order:**\n" + "\n".join(self._format_line(c) for c in normalized))

    @commands.hybrid_command()
    async def clearinit(self, ctx):
        """Clear initiative order."""
        if not self._require_guild(ctx):
            await ctx.send("❌ This command must be used in a server (not in DMs).")
            return
        await self.config.guild(ctx.guild).init_order.set([])
        await ctx.send("🧹 Initiative order cleared.")

    @commands.hybrid_command()
    async def dropinit(self, ctx, *, name: str):
        """Remove a single combatant by exact or base name (first match)."""
        if not self._require_guild(ctx):
            await ctx.send("❌ This command must be used in a server (not in DMs).")
            return
        target = name.strip()
        if not target:
            await ctx.send("⚠️ Please provide a name to remove.")
            return

        stored = await self.config.guild(ctx.guild).init_order()
        normalized = self._normalize_stored(stored)

        target_lower = target.lower()
        idx = next((i for i, e in enumerate(normalized) if e["name"].lower() == target_lower), None)
        if idx is None:
            idx = next((i for i, e in enumerate(normalized) if e["base_name"].lower() == target_lower), None)
        if idx is None:
            await ctx.send(f"⚠️ No combatant found with name matching '{name}'.")
            return

        removed = normalized.pop(idx)
        to_store = [{k: e[k] for k in ("name","display","mod","die","total","forced")} for e in normalized]
        await self.config.guild(ctx.guild).init_order.set(to_store)

        await ctx.send(f"❌ Removed '{removed['name']}' from initiative.\n📋 Updated Order:\n" + "\n".join(self._format_line(c) for c in normalized))