import discord
from redbot.core import commands, Config
import aiohttp
import re
from collections import Counter
from itertools import islice
import os
import asyncio
import urllib.request
from html.parser import HTMLParser
from datetime import datetime
import difflib
import json


SYSTEM_PROMPT = """
You are the DM for a D&D 5e text adventure. You control the world, NPCs, monsters, and events, but never act for the player unless they explicitly ask. Do not roll for a player unless asked. Keep responses under 2000 characters and always wait for the player’s next action.
Use D&D 5e mechanics when relevant: ability checks, saving throws, combat rounds, NPC/monster rolls, and clear consequences.
Create locations, NPCs, quests, items, and encounters as needed. Maintain a consistent world state and avoid contradicting established facts. New lore must fit the existing tone and logic.
Let the player set the pace. Do not push the story forward unless their action clearly advances it. If their intent is unclear, ask for clarification. Avoid assumptions, railroading, or forcing a specific outcome.
Keep descriptions vivid but concise. Provide only information the player would reasonably perceive. Keep NPC motivations consistent and consequences meaningful. Avoid real‑world politics.
If the player attempts something impossible, offer a creative alternative rather than shutting them down.
Your responses should feel natural and conversational, like a DM at the table. Use this flexible structure:
- Start with immersive narration.
- Weave in mechanics only when needed.
- End by inviting the player to choose their next action.
Do not use rigid numbered sections unless the situation genuinely benefits from it
"""
class _DirectoryParser(HTMLParser):
    """Simple built‑in HTML parser to extract <a href="..."> links."""
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for attr, value in attrs:
                if attr == "href":
                    self.links.append(value)

class AiDm(commands.Cog):
    """5etools-backed Dungeon Master with OpenRouter fallback for D&D 5e."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=11011234567890)
        self.config.register_global(api_keys=[])
        self.config.register_global(model="deepseek/deepseek-chat-v3.1:free")
        self.config.register_global(fivetools_url="http://localhost:5050/data")

        self.config.register_channel(context=[])
        self.key_index = 0  # For round-robin rotation

        # Lazy cache for 5etools JSON files
        self.fivetools_cache = {}

        # Files to search (all content, not just SRD)
        self.fivetools_files = [
            "spells/spells-phb.json",
            "spells/spells-xge.json",
            "spells/spells-tce.json",
            "bestiary/bestiary-mm.json",
            "bestiary/bestiary-vgm.json",
            "bestiary/bestiary-mpmm.json",
            "items-base.json",
            "items.json",
            "conditionsdiseases.json",
            "skills.json",
            "feats.json",
            "backgrounds.json",
            "races.json",
           ]
        bot.loop.create_task(self._load_class_files())

    async def _load_class_files(self):
        """Fetch all class/*.json files from the 5etools backend and append them."""
        await asyncio.sleep(0)  # yield to event loop

        base_url = await self.config.fivetools_url()
        class_url = f"{base_url.rstrip('/')}/class/"

        class_files = []

        try:
            with urllib.request.urlopen(class_url) as response:
                html = response.read().decode("utf-8")

            parser = _DirectoryParser()
            parser.feed(html)

            for raw in parser.links:
                # Normalize the filename (fixes the startswith issue)
                link = raw.strip().lstrip("./")

                # Skip unwanted files
                if "fluff" in link:
                    continue
                if link.startswith("index"):
                    continue
                if link.startswith("foundry"):
                    continue

                # Only accept JSON files that start with "class-"
                if link.startswith("class-") and link.endswith(".json"):
                    class_files.append(f"class/{link}")
        except Exception as e:
            print(f"[AiDm] Failed to load class directory: {e}")

        # Fall back to a known set of class JSON files when the server doesn't provide an index.
        if not class_files:
            class_files = [
                "class/class-artificer.json",
                "class/class-barbarian.json",
                "class/class-bard.json",
                "class/class-cleric.json",
                "class/class-druid.json",
                "class/class-fighter.json",
                "class/class-monk.json",
                "class/class-mystic.json",
                "class/class-paladin.json",
                "class/class-ranger.json",
                "class/class-rogue.json",
                "class/class-sidekick.json",
                "class/class-sorcerer.json",
                "class/class-warlock.json",
                "class/class-wizard.json",
            ]

        for file in class_files:
            if file not in self.fivetools_files:
                self.fivetools_files.append(file)

        print("[AiDm] Loaded class files:", self.fivetools_files)

    async def get_next_key(self):
        """Return next API key from pool or fall back to OPENROUTER_API_KEY env var."""
        keys = await self.config.api_keys()
        if keys:
            key = keys[self.key_index % len(keys)]
            self.key_index += 1
            print(f"[aidm] Using API key {self.key_index}/{len(keys)} from config pool")
            return key
        env_key = os.environ.get("OPENROUTER_API_KEY")
        if env_key:
            print("[aidm] Using OPENROUTER_API_KEY from environment")
        else:
            print("[aidm] No OpenRouter API key available")
        return env_key

    def hide_mechanics(self, text: str) -> str:
        # CR or DC followed by optional space and digits
        text = re.sub(r'\b(CR|DC)\s?(\d+)\b', r'||\1\2||', text)

        # Rolls like: "Roll 1d20 = 14" or "1d20: 14"
        text = re.sub(r'(\d+d\d+)\s*[:=]\s*(\d+)', r'||\1 = \2||', text)

        # Standalone roll results like "Roll: 14" or "roll 17"
        text = re.sub(r'\b[Rr]oll(?:ed)?[: ]+(\d+)\b', r'||Roll \1||', text)

        return text

    # Fuzzy keyword extraction using n-grams
    def extract_keyword_fuzzy(self, raw_text: str):
        print(f"[aidm] extract_keyword_fuzzy input: '{raw_text}'")
        try:
            stop_words = {
                'a', 'an', 'the', 'and', 'or', 'but', 'if', 'while', 'with', 'to', 'from', 'in', 'on', 'at',
                'by', 'for', 'of', 'up', 'down', 'out', 'over', 'under', 'again', 'further', 'then', 'once',
                'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more',
                'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                'too', 'very', 'can', 'will', 'just', 'don', 'should', 'now', 'tell', 'me', 'about', 'what',
                'is', 'are', 's'
            }

            words = re.findall(r'\b\w+\b', raw_text.lower())
            filtered = [word for word in words if word not in stop_words]

            def get_ngrams(n):
                return [' '.join(ng) for ng in zip(*(islice(filtered, i, None) for i in range(n)))]

            for n in (3, 2, 1):
                ngrams = get_ngrams(n)
                if ngrams:
                    from collections import Counter
                    most_common = Counter(ngrams).most_common(1)
                    if most_common:
                        keyword = most_common[0][0]
                        print(f"✅ Fuzzy keyword extracted (n={n}): {keyword}")
                        return keyword

            print("⚠️ No keyword extracted from input.")
            return None

        except Exception as e:
            print(f"❌ Failed to extract keyword: {e}")
            return None

    async def build_prompt(self, channel, new_question: str):
        context = await self.config.channel(channel).context()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(context)
        messages.append({"role": "user", "content": new_question})
        return messages

    async def update_context(self, channel, user_input, bot_reply):
        context = await self.config.channel(channel).context()
        context.append({"role": "user", "content": user_input})
        context.append({"role": "assistant", "content": bot_reply})
        context = context[-12:]
        await self.config.channel(channel).context.set(context)

    async def summarize_context(self, channel):
        context = await self.config.channel(channel).context()
        if len(context) < 6:
            return None

        messages = [
            {"role": "system", "content": "Summarize this D&D conversation in under 1000 characters."},
            {"role": "user", "content": "\n".join([msg["content"] for msg in context if msg["role"] == "user"])}
        ]

        summary = await self.query_ai(messages)
        cleaned = summary.replace("<｜begin▁of▁sentence｜>", "").strip()

        await self.config.channel(channel).context.set([
            {"role": "system", "content": "Session summary: " + cleaned}
        ])

        try:
            await channel.send(f"📝 **Session recap:** {cleaned}")
        except Exception:
            pass

        return cleaned

    async def query_ai(self, messages):
        """Single consolidated query function with rotation/backoff and better error surfacing."""
        model = await self.config.model() or "deepseek/deepseek-chat-v3.1:free"
        payload = {"model": model, "messages": messages, "temperature": 0.7}
        headers_base = {"Content-Type": "application/json"}

        print(f"[aidm] query_ai called (model={model}, messages={len(messages)})")

        keys = await self.config.api_keys()
        attempts = max(1, len(keys) or 1)

        for attempt in range(attempts):
            api_key = await self.get_next_key()
            if not api_key:
                raise RuntimeError("No OpenRouter API key available (set with addkey/setapikey or OPENROUTER_API_KEY).")

            print(f"[aidm] query_ai attempt {attempt + 1}/{attempts}")
            headers = {**headers_base, "Authorization": f"Bearer {api_key}"}

            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as resp:
                    print(f"[aidm] OpenRouter HTTP status: {resp.status}")
                    text = await resp.text()
                    try:
                        data = await resp.json()
                    except Exception:
                        print(f"[aidm] OpenRouter returned non-json response (status={resp.status})")
                        raise RuntimeError(f"OpenRouter HTTP {resp.status}, non-json response: {text}")

                    if resp.status == 429:
                        print(f"[aidm] OpenRouter rate limited (429). Backing off...")
                        await asyncio.sleep(min(10, 2 ** attempt))
                        continue

                    if resp.status >= 400:
                        err_msg = None
                        if isinstance(data, dict):
                            err_msg = data.get("error") or data.get("message") or data.get("detail")
                            if isinstance(err_msg, dict):
                                err_msg = err_msg.get("message") or str(err_msg)
                        print(f"[aidm] OpenRouter returned error {resp.status}: {err_msg or text}")
                        raise RuntimeError(f"OpenRouter returned HTTP {resp.status}: {err_msg or text}")

                    if isinstance(data, dict) and "choices" in data and data["choices"]:
                        choice = data["choices"][0]
                        if isinstance(choice.get("message"), dict) and "content" in choice["message"]:
                            content = choice["message"]["content"]
                            print(f"[aidm] OpenRouter returned content length {len(content)}")
                            return content
                        if "text" in choice:
                            text_resp = choice["text"]
                            print(f"[aidm] OpenRouter returned text length {len(text_resp)}")
                            return text_resp
                        print(f"[aidm] OpenRouter returned unexpected structure: {data}")
                        raise RuntimeError(f"OpenRouter returned unexpected structure: {data}")

                    error_msg = data.get("error") if isinstance(data, dict) else None
                    print(f"[aidm] OpenRouter error response: {error_msg or text}")
                    raise RuntimeError(f"OpenRouter error: {error_msg or text}")

        raise RuntimeError("All OpenRouter keys exhausted or rate-limited.")

    async def summarize_text(self, long_text: str):
        messages = [
            {"role": "system", "content": "You are a helpful Dungeon Master for D&D 5e."},
            {"role": "user", "content": f"Summarize the following in under 2000 characters:\n\n{long_text}"}
        ]
        summary = await self.query_ai(messages)
        return summary.replace("<｜begin▁of▁sentence｜>", "").strip()

    async def send_long_message(self, channel, text):
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        for chunk in chunks:
            await channel.send(chunk)

    def is_question_like(self, message: str) -> bool:
        if message.strip().startswith("!"):
            return False

        QUESTION_STARTERS = {
            "what", "who", "when", "where", "why", "how",
            "is", "are", "can", "could", "would", "should",
            "will", "shall", "may", "might", "explain", "tell", "describe", "?"
        }
        words = message.lower().split()
        return bool(words and words[0] in QUESTION_STARTERS)

    # ---------- 5ETOOLS INTEGRATION ----------

    async def fetch_5etools_file(self, endpoint: str):
        """Lazy-load a 5etools JSON file and cache it."""
        if endpoint in self.fivetools_cache:
            print(f"[aidm] 5etools cache hit for {endpoint}")
            return self.fivetools_cache[endpoint]

        base = await self.config.fivetools_url()
        url = f"{base.rstrip('/')}/{endpoint}"
        print(f"[aidm] Fetching 5etools file: {url}")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        print(f"⚠️ 5etools fetch failed {resp.status} for {url}")
                        return None
                    data = await resp.json()
                    self.fivetools_cache[endpoint] = data
                    return data
        except Exception as e:
            print(f"❌ Error fetching 5etools file {endpoint}: {e}")
            return None

    def _extract_entries_from_5etools(self, data: dict):
        """Extract all list-like entry collections from a 5etools JSON file."""
        if not isinstance(data, dict):
            return []

        entries = []
        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                entries.extend(value)
        return entries

    def _similarity(self, a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    async def search_5etools(self, keyword: str):
        """
        Search across all configured 5etools files.
        Uses fuzzy matching with a medium cutoff (~0.65).
        Returns best matching entry or None.
        """
        print(f"[aidm] Searching 5etools for keyword: '{keyword}'")
        best_entry = None
        best_score = 0.0
        cutoff = 0.65

        for file in self.fivetools_files:
            print(f"[aidm] Searching file: {file}")
            data = await self.fetch_5etools_file(file)
            if not data:
                continue

            entries = self._extract_entries_from_5etools(data)
            for entry in entries:
                name = entry.get("name")
                if not name:
                    continue
                score = self._similarity(keyword, name)
                if score > best_score:
                    best_score = score
                    best_entry = entry

        if best_entry and best_score >= cutoff:
            print(f"✅ 5etools match '{best_entry.get('name')}' for '{keyword}' (score={best_score:.2f})")
            return best_entry

        print(f"⚠️ No 5etools match for '{keyword}' (best={best_score:.2f})")
        return None

    def format_class_table_groups(self, groups):
        """Format ALL 5etools class table groups (Monk, Wizard, etc.) into readable text."""

        # Unwrap nested lists until we reach a dict
        while isinstance(groups, list):
            if not groups:
                return ""
            groups = groups[0]

        if not isinstance(groups, dict):
            return str(groups)

        out = []

        # If the group has a title (Wizard spell slots)
        title = groups.get("title")
        if title:
            out.append(f"**{self.clean_5etools_markup(title)}:**")

        # Determine which row field is used
        rows = (
            groups.get("rows")
            or groups.get("rowsSpellProgression")
            or groups.get("rowsSubclassFeatures")
            or groups.get("rowsOther")
        )

        if not rows:
            return ""

        # Clean labels
        labels = [self.clean_5etools_markup(str(l)) for l in groups.get("colLabels", [])]

        level = 1

        for row in rows:
            # Skip stray integers
            if isinstance(row, int):
                continue

            # Ensure row is a list
            if not isinstance(row, list):
                row = [row]

            parts = []

            for label, cell in zip(labels, row):

                # Clean label
                label_str = self.clean_5etools_markup(str(label))

                # --- DICE (Monk Martial Arts) ---
                if isinstance(cell, dict) and cell.get("type") == "dice":
                    faces = None

                    if isinstance(cell.get("toRoll"), list) and cell["toRoll"]:
                        first = cell["toRoll"][0]
                        if isinstance(first, dict):
                            faces = first.get("faces")

                    elif isinstance(cell.get("toRoll"), dict):
                        faces = cell["toRoll"].get("faces")

                    if not faces:
                        faces = cell.get("faces")

                    parts.append(f"{label_str} d{faces if faces else '?'}")
                    continue

                # --- BONUS SPEED (Monk) ---
                if isinstance(cell, dict) and cell.get("type") == "bonusSpeed":
                    parts.append(f"{label_str} +{cell.get('value', 0)} ft")
                    continue

                # --- BONUS VALUES (Barbarian Rage Damage, etc.) ---
                if isinstance(cell, dict) and cell.get("type") == "bonus":
                    parts.append(f"{label_str} +{cell.get('value', 0)}")
                    continue

                # --- SIMPLE VALUES ---
                cell_str = self.clean_5etools_markup(str(cell))

                # If label exists and cell is numeric → "Label N"
                if label_str and cell_str.isdigit():
                    parts.append(f"{label_str} {cell_str}")
                else:
                    # fallback: "Label Value"
                    parts.append(f"{label_str} {cell_str}".strip())

            out.append(f"Level {level}: " + ", ".join(p for p in parts if p))
            level += 1

        return "\n".join(out)


    def format_class_features(self, features: list) -> str:
        """Clean and format class features into readable text."""
        cleaned = []

        for feat in features:
            if not isinstance(feat, str):
                continue

            # Extract name and level
            m = re.match(r"([^|]+)\|[^|]*\|?(\d+)?", feat)
            if m:
                name = m.group(1).strip()
                level = m.group(2)
                if level:
                    cleaned.append(f"{name} (Level {level})")
                else:
                    cleaned.append(name)
            else:
                cleaned.append(self.clean_5etools_markup(feat))

        return ", ".join(cleaned)


    def prettify_key(self, key: str) -> str:
        """Convert camelCase or mixedCase into 'Title Case'."""
        words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', key)
        return " ".join(w.capitalize() for w in words)

    def clean_5etools_markup(self, text: str) -> str:
        """Strip 5etools {@...} markup and keep readable content."""
        if not isinstance(text, str):
            return text

        # Generic {@tag content|...} → content
        text = re.sub(
            r"\{@[a-zA-Z]+ ([^|}]+)(?:\|[^}]+)?\}",
            r"\1",
            text,
        )

        # Remove leftover |source|junk
        text = re.sub(r"\|[a-zA-Z0-9]+", "", text)

        # Remove any remaining {@...}
        text = re.sub(r"\{@[^}]+\}", "", text)

        return text.strip()

    def format_value(self, value):
        """Collapse any JSON value into a clean inline string with no braces."""

        # --- STRINGS ---
        if isinstance(value, str):
            cleaned = self.clean_5etools_markup(value).strip()

            # Convert class feature pipes: "Feature|Monk||3" → "Feature (Level 3)"
            cleaned = re.sub(r"\|[A-Za-z]+?\|\|(\d+)", r" (Level \1)", cleaned)

            # Convert prepared spell formulas like "<$level$> + <$int_mod$>"
            formula_map = {
                "level": "level",
                "int_mod": "INT modifier",
                "wis_mod": "WIS modifier",
                "cha_mod": "CHA modifier",
                "str_mod": "STR modifier",
                "dex_mod": "DEX modifier",
                "con_mod": "CON modifier",
            }

            def replace_formula(match):
                key = match.group(1)
                return formula_map.get(key, key)

            cleaned = re.sub(r"<\$(.*?)\$>", replace_formula, cleaned)

            return cleaned

        # --- SIMPLE VALUES ---
        if isinstance(value, (int, float, bool)) or value is None:
            return str(value)

        # --- LISTS ---
        if isinstance(value, list):
            # Clean each item
            items = [self.format_value(v).strip() for v in value]
            items = [i for i in items if i]

            # If all items are simple → comma-separated
            if all("\n" not in i for i in items):
                return ", ".join(items)

            # Otherwise → bullet list
            return "\n".join(f"- {i}" for i in items)

        # --- DICTS ---
        if isinstance(value, dict):
            parts = []

            # Special handling for "choose" blocks
            if "choose" in value and isinstance(value["choose"], dict):
                choose = value["choose"]
                from_list = choose.get("from", [])
                count = choose.get("count", None)

                from_str = ", ".join(self.format_value(i) for i in from_list)
                if count:
                    return f"choose {count} from {from_str}"
                return f"choose from {from_str}"

            # Generic dict → "Key: Value"
            for k, v in value.items():
                pretty_k = self.prettify_key(k)
                pretty_v = self.format_value(v)
                parts.append(f"{pretty_k}: {pretty_v}")

            # If all values are simple → inline
            if all("\n" not in p for p in parts):
                return "; ".join(parts)

            # Otherwise → multiline
            return "\n".join(parts)

        # --- FALLBACK ---
        return str(value)

    def format_item_entries(self, entries):
        """Format 5etools item entries into readable paragraphs."""
        out = []

        for ent in entries:
            # Simple string paragraph
            if isinstance(ent, str):
                out.append(self.clean_5etools_markup(ent))
                continue

            # Structured entry with name + subentries
            if isinstance(ent, dict) and ent.get("type") == "entries":
                name = ent.get("name")
                sub = ent.get("entries", [])

                if name:
                    out.append(f"**{self.clean_5etools_markup(name)}**")

                for s in sub:
                    if isinstance(s, str):
                        out.append(self.clean_5etools_markup(s))
                    elif isinstance(s, dict):
                        # Nested entries (rare but possible)
                        nested = s.get("entries", [])
                        for n in nested:
                            out.append(self.clean_5etools_markup(n))

        return "\n".join(out)

    def format_monster_actions(self, actions):
        """Format 5etools monster actions into readable text."""
        out = []

        for act in actions:
            # Simple string (rare)
            if isinstance(act, str):
                out.append(self.clean_5etools_markup(act))
                continue

            if isinstance(act, dict):
                name = act.get("name")
                entries = act.get("entries", [])

                # Action name
                if name:
                    out.append(f"**{self.clean_5etools_markup(name)}**")

                # Action body
                for e in entries:
                    if isinstance(e, str):
                        out.append(self.clean_5etools_markup(e))
                    elif isinstance(e, dict) and e.get("type") == "entries":
                        for sub in e.get("entries", []):
                            out.append(self.clean_5etools_markup(sub))

        return "\n".join(out)

    def format_5etools_entry(self, entry: dict) -> str:
        out = [f"📘 5etools entry for **{entry.get('name', 'Unknown')}**\n"]

        # Keys we never want to display
        skip_keys = {
            "hasFluff",
            "hasFluffImages",
            "fluff",
            "fluffImages",
            "_copy",
            "otherSources",
        }

        for key, value in entry.items():
            if key in skip_keys:
                continue

            pretty = self.prettify_key(key)

            # Special handling for class table
            if key == "classTableGroups":
                table_texts = []
                for group in value:
                    table_texts.append(self.format_class_table_groups(group))
                out.append(f"**{pretty}:**\n" + "\n\n".join(table_texts))
                continue

            # Special handling for class features
            if key == "classFeatures":
                out.append(f"**{pretty}:** {self.format_class_features(value)}")
                continue

            if key == "entries":
                out.append(f"**Entries:**\n{self.format_item_entries(value)}")
                continue

            if key == "action" or key == "actions":
                out.append(f"**Actions:**\n{self.format_monster_actions(value)}")
                continue

            if key == "bonusActions":
                out.append(f"**Bonus Actions:**\n{self.format_monster_actions(value)}")
                continue

            if key == "reactions":
                out.append(f"**Reactions:**\n{self.format_monster_actions(value)}")
                continue

            if key == "legendaryActions":
                out.append(f"**Legendary Actions:**\n{self.format_monster_actions(value)}")
                continue

            # Default formatting
            out.append(f"**{pretty}:** {self.format_value(value)}")

        return "\n".join(out)

    # ---------- MAIN HANDLER ----------

    async def handle_dnd_query(self, message: discord.Message):
        user_id = message.author.id
        raw_text = message.content.replace("@dm", "").strip()
        print(f"[aidm] handle_dnd_query from user {user_id} in channel {getattr(message.channel, 'name', message.channel.id)}: '{raw_text}'")

        if not raw_text:
            return await message.channel.send("What would you like to ask the DM?")

        # Try 5etools lookup if question-like
        keyword = None
        if self.is_question_like(raw_text):
            keyword = self.extract_keyword_fuzzy(raw_text)
            if keyword:
                print(f"[aidm] keyword extracted for 5etools lookup: '{keyword}'")
                entry = await self.search_5etools(keyword)
                if entry:
                    print(f"[aidm] found 5etools entry: {entry.get('name')}")
                    formatted = self.format_5etools_entry(entry)
                    await self.send_long_message(
                        message.channel,
                        f"{formatted}"
                    )
                    return
                else:
                    print(f"[aidm] no 5etools entry matched '{keyword}'")

        # Context prep
        context = await self.config.channel(message.channel).context()
        if len(context) > 12:
            await self.summarize_context(message.channel)

        # AI fallback
        query_text = raw_text.lstrip("!? ")
        messages = await self.build_prompt(message.channel, query_text)
        try:
            print(f"[aidm] Querying AI for message: '{query_text}'")
            reply = await self.query_ai(messages)
            reply = reply.replace("<｜begin▁of▁sentence｜>", "").strip()
            print(f"[aidm] AI replied (length={len(reply)})")

            if len(reply) > 2000:
                print("[aidm] AI reply >2000 chars, summarizing")
                reply = await self.summarize_text(reply)

            await self.send_long_message(message.channel, f"DM Says: {self.hide_mechanics(reply)}")
            await self.update_context(message.channel, query_text, reply)

        except Exception as e:
            print(f"[aidm] AI query failed: {e}")
            await message.channel.send(f"Something went wrong: {e}")

    # ---------- LISTENERS ----------

    @commands.Cog.listener(name="on_message")
    async def _auto_assign_player_role(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        if getattr(message.channel, "name", None) != "create-a-character":
            return

        if not message.content.lower().startswith("tul!register"):
            return

        role = discord.utils.get(message.guild.roles, name="Player")
        if role is None:
            await message.channel.send("⚠️ The 'Player' role does not exist.")
            return

        try:
            await message.author.add_roles(role, reason="Auto-assigned on tul!register")
            await message.channel.send(f"🎉 {message.author.mention} has been given the **Player** role.")
        except discord.Forbidden:
            await message.channel.send("❌ I don't have permission to assign roles.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        content = message.content.strip()

        # Literal typed trigger
        if content.lower().startswith("@dm"):
            await self.handle_dnd_query(message)
            return

        # Role mention trigger (handles <@&ROLEID> tokens)
        if message.role_mentions:
            try:
                guild_role_id = await self.config.guild(message.guild).dm_role_id()
            except Exception:
                guild_role_id = None

            triggered = False
            for role in message.role_mentions:
                if guild_role_id:
                    if role.id == guild_role_id:
                        triggered = True
                        break
                else:
                    if role.name.lower() == "dm":
                        triggered = True
                        break

            if triggered:
                parts = content.split(maxsplit=1)
                remainder = ""
                if parts:
                    first = parts[0]
                    if first.startswith("<@&") and first.endswith(">"):
                        remainder = parts[1] if len(parts) > 1 else ""
                    else:
                        remainder = content
                message.content = f"@dm {remainder}".strip()
                await self.handle_dnd_query(message)
                return

            await self.bot.process_commands(message)

    # ---------- COMMANDS ----------

    @commands.command()
    async def resetcontext(self, ctx):
        """Reset this channel's DM conversation history."""
        await self.config.channel(ctx.channel).context.set([])
        await ctx.send("This channel's DM context has been reset.")

    @commands.command()
    async def recap(self, ctx):
        """Summarize the current channel's D&D session."""
        cleaned = await self.summarize_context(ctx.channel)
        if cleaned:
            await ctx.send("This channel's session has been summarized.")
        else:
            await ctx.send("Not enough context to summarize yet.")

    @commands.command()
    @commands.is_owner()
    async def setapikey(self, ctx, key: str):
        """Set a single OpenRouter API key (replaces pool). Owner only."""
        await ctx.message.delete()
        await self.config.api_keys.set([key])
        confirm = await ctx.send("API key saved to config.")
        await confirm.delete(delay=3)

    @commands.command()
    async def addkey(self, ctx, key: str):
        """Add an OpenRouter API key to the shared pool."""
        await ctx.message.delete()
        keys = await self.config.api_keys()
        if key in keys:
            return await ctx.send("This key is already in the pool.")
        keys.append(key)
        await self.config.api_keys.set(keys)
        confirm = await ctx.send("Key added to the shared pool.")
        await confirm.delete(delay=3)

    @commands.command()
    @commands.is_owner()
    async def dropkeys(self, ctx):
        """Remove all OpenRouter API keys from the shared pool (owner only)."""
        await self.config.api_keys.set([])
        await ctx.send("All OpenRouter keys have been removed from the pool.")

    @commands.command()
    @commands.is_owner()
    async def setmodel(self, ctx, *, model: str):
        """Set the OpenRouter model to use (owner only). Example: deepseek/deepseek-chat-v3.1:free"""
        await self.config.model.set(model)
        await ctx.send(f"Model set to `{model}`")

    @commands.command()
    @commands.is_owner()
    async def checkcredits(self, ctx):
        """Check rate limit remaining for all API keys."""
        keys = await self.config.api_keys()
        if not keys:
            env_key = os.environ.get("OPENROUTER_API_KEY")
            if not env_key:
                return await ctx.send("No API keys configured.")
            keys = [env_key]

        embed = discord.Embed(
            title="OpenRouter Rate Limits",
            color=discord.Color.blue(),
        )

        async with aiohttp.ClientSession() as session:
            for i, key in enumerate(keys, 1):
                masked_key = f"{key[:6]}...{key[-4:]}"
                try:
                    async with session.get(
                        "https://openrouter.ai/api/v1/key",
                        headers={"Authorization": f"Bearer {key}"}
                    ) as response:
                        data = await response.json()
                        key_data = data.get("data", {})
                        limit_remaining = key_data.get("limit_remaining", "N/A")
                        limit_total = key_data.get("limit", "N/A")
                        embed.add_field(
                            name=f"Key {i}",
                            value=(
                                f"```\nKey: {masked_key}"
                                f"\nRate Limit Remaining: {limit_remaining}"
                                f"\nRate Limit Total: {limit_total}\n```"
                            ),
                            inline=True
                        )
                except Exception as e:
                    embed.add_field(
                        name=f"Key {i}",
                        value=f"❌ Error: {str(e)}",
                        inline=True
                    )

        msg = await ctx.send(embed=embed)
        await msg.delete(delay=30)

    @commands.command()
    @commands.is_owner()
    async def set5etoolsurl(self, ctx, url: str):
        """Set the base URL for the 5etools data (e.g. http://host:5050/data)."""
        await self.config.fivetools_url.set(url)
        # Clear cache so new URL is used
        self.fivetools_cache.clear()
        await ctx.send(f"5etools URL set to: `{url}`")