import discord
from redbot.core import commands, Config
import aiohttp
import xml.etree.ElementTree as ET
import difflib
import os
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime

class AiDm(commands.Cog):
    """SRD Dungeon Master with ChatGPT fallback for D&D 5e."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890)
        # per-channel context + shared API key pool and selected model
        self.config.register_global(api_keys=[])
        self.config.register_global(model="deepseek/deepseek-chat-v3.1:free")
        self.config.register_channel(context=[])
        self.key_index = 0  # For round-robin rotation
        self.srd_index = self.load_compendium("C:/redbot/cogs/AiDm/SelfSRD.xml")  # Adjust path for Docker mount

    async def get_next_key(self):
        """Return next API key from pool or fall back to OPENROUTER_API_KEY env var."""
        keys = await self.config.api_keys()
        if keys:
            key = keys[self.key_index % len(keys)]
            self.key_index += 1
            return key
        return os.environ.get("OPENROUTER_API_KEY")

    # Load SRD from XML
    def load_compendium(self, xml_path):
        index = {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for entry in root:
                name_tag = entry.find("name")
                text_tag = entry.find("text")
                if name_tag is not None and text_tag is not None:
                    name = name_tag.text.strip().lower()
                    text = text_tag.text.strip()
                    index[name] = text
        except Exception as e:
            print(f"Failed to load SRD compendium: {e}")
        return index

    # Fuzzy keyword match
    def extract_keyword_fuzzy(self, text: str, cutoff=0.8):
        words = text.lower().split()
        for word in words:
            matches = difflib.get_close_matches(word, self.srd_index.keys(), n=1, cutoff=cutoff)
            if matches:
                return matches[0]
        return None

    # Build ChatGPT prompt with context
    async def build_prompt(self, channel, new_question: str):
        context = await self.config.channel(channel).context()
        messages = [{"role": "system", "content": "You are a helpful Dungeon Master for D&D 5e."}]
        messages.extend(context)
        messages.append({"role": "user", "content": new_question})
        return messages

    # Update context memory
    async def update_context(self, channel, user_input, bot_reply):
        context = await self.config.channel(channel).context()
        context.append({"role": "user", "content": user_input})
        context.append({"role": "assistant", "content": bot_reply})
        context = context[-12:]  # Keep last 12 turns
        await self.config.channel(channel).context.set(context)

    async def summarize_context(self, channel):
        context = await self.config.channel(channel).context()
        if len(context) < 6:
            return None

        messages = [
            {"role": "system", "content": "Summarize this D&D conversation in under 500 characters."},
            {"role": "user", "content": "\n".join([msg["content"] for msg in context if msg["role"] == "user"])}
        ]

        summary = await self.query_ai(messages)
        cleaned = summary.replace("<｜begin▁of▁sentence｜>", "").strip()

        # Replace context with a short session summary
        await self.config.channel(channel).context.set([
            {"role": "system", "content": "Session summary: " + cleaned}
        ])

        # Send a recap message to the channel
        try:
            await channel.send(f"📝 **Session recap:** {cleaned}")
        except Exception:
            # best-effort: ignore send failures (e.g., missing permissions)
            pass

        return cleaned

    def append_to_srd_xml(self, keyword: str, description: str, xml_path="C:/redbot/cogs/AiDm/SelfSRD.xml"):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            new_entry = ET.Element("entry")
            name_tag = ET.SubElement(new_entry, "name")
            name_tag.text = keyword.strip()

            text_tag = ET.SubElement(new_entry, "text")
            text_tag.text = description.strip()

            root.append(new_entry)
            tree.write(xml_path, encoding="utf-8", xml_declaration=True)
            print(f"✅ SRD entry for '{keyword}' added to XML.")
        except Exception as e:
            print(f"❌ Failed to append SRD entry: {e}")

    async def query_ai(self, messages):
        """Single consolidated query function with rotation/backoff and better error surfacing."""
        # Build payload
        model = await self.config.model() or "deepseek/deepseek-chat-v3.1:free"
        payload = {"model": model, "messages": messages, "temperature": 0.7}
        headers_base = {"Content-Type": "application/json"}

        # If we have keys configured, try each with backoff; otherwise try env var once
        keys = await self.config.api_keys()
        attempts = max(1, len(keys))

        for attempt in range(attempts):
            api_key = await self.get_next_key()
            if not api_key:
                raise RuntimeError("No OpenRouter API key available (set with addkey/setapikey or OPENROUTER_API_KEY).")

            headers = {**headers_base, "Authorization": f"Bearer {api_key}"}

            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as resp:
                    text = await resp.text()
                    # Try to decode JSON for diagnostic info
                    try:
                        data = await resp.json()
                    except Exception:
                        raise RuntimeError(f"OpenRouter HTTP {resp.status}, non-json response: {text}")

                    if resp.status == 429:
                        # exponential backoff and try next key
                        await asyncio.sleep(min(10, 2 ** attempt))
                        continue

                    if resp.status >= 400:
                        # surface provider message if present
                        err_msg = None
                        if isinstance(data, dict):
                            err_msg = data.get("error") or data.get("message") or data.get("detail")
                            if isinstance(err_msg, dict):
                                err_msg = err_msg.get("message") or str(err_msg)
                        raise RuntimeError(f"OpenRouter returned HTTP {resp.status}: {err_msg or text}")

                    # success expected shape
                    if isinstance(data, dict) and "choices" in data and data["choices"]:
                        choice = data["choices"][0]
                        # common shapes
                        if isinstance(choice.get("message"), dict) and "content" in choice["message"]:
                            return choice["message"]["content"]
                        if "text" in choice:
                            return choice["text"]
                        raise RuntimeError(f"OpenRouter returned unexpected structure: {data}")

                    # no choices provided
                    error_msg = data.get("error") if isinstance(data, dict) else None
                    raise RuntimeError(f"OpenRouter error: {error_msg or text}")

        raise RuntimeError("All OpenRouter keys exhausted or rate-limited.")

    async def summarize_text(self, long_text: str):
        messages = [
            {"role": "system", "content": "You are a helpful Dungeon Master for D&D 5e."},
            {"role": "user", "content": f"Summarize the following in under 1000 characters:\n\n{long_text}"}
        ]
        summary = await self.query_ai(messages)
        return summary.replace("<｜begin▁of▁sentence｜>", "").strip()

    async def send_long_message(self, channel, text):
        chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        for chunk in chunks:
            await channel.send(chunk)
 
    # Main handler
    async def handle_dnd_query(self, message: discord.Message):
        user_id = message.author.id
        raw_text = message.content.replace("@dm", "").strip()

        if not raw_text:
            return await message.channel.send("What would you like to ask the DM?")

        keyword = self.extract_keyword_fuzzy(raw_text)

        # SRD lookup
        if keyword and keyword in self.srd_index:
            entry = self.srd_index[keyword]
            # If stored as dict with usage tracking
            if isinstance(entry, dict):
                entry["last_used"] = datetime.now(datetime.timezone.utc).isoformat()
                await message.channel.send(f"📘 SRD entry for **{keyword}**:\n{entry['text']}")
            else:
                await message.channel.send(f"📘 SRD entry for **{keyword}**:\n{entry}")
            return

        # Context prep
        context = await self.config.channel(message.channel).context()
        if len(context) > 12:
            await self.summarize_context(message.channel)

        # AI fallback
        messages = await self.build_prompt(message.channel, raw_text)
        try:
            reply = await self.query_ai(messages)
            reply = reply.replace("<｜begin▁of▁sentence｜>", "").strip()

            if len(reply) > 2000:
                reply = await self.summarize_text(reply)

            await self.send_long_message(message.channel, f"DM Says: {reply}")
            await self.update_context(message.channel, raw_text, reply)

            # Normalize keyword
            keyword = raw_text.lower().strip()

            # Store in SRD index with usage tracking
            self.srd_index[keyword] = {
                "text": reply,
                "last_used": datetime.utcnow().isoformat()
            }

            # Append to XML
            self.append_to_srd_xml(keyword, reply)

        except Exception as e:
            await message.channel.send(f"Something went wrong: {e}")

    # Trigger on @dm
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
            # If you have a configured guild role id, prefer that
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
                # Remove leading role mention token if it's the first token
                parts = content.split(maxsplit=1)
                remainder = ""
                if parts:
                    first = parts[0]
                    if first.startswith("<@&") and first.endswith(">"):
                        remainder = parts[1] if len(parts) > 1 else ""
                    else:
                        # role mention might not be at start; keep full content
                        remainder = content
                # rewrite to form your handler expects
                message.content = f"@dm {remainder}".strip()
                await self.handle_dnd_query(message)
                return

            # ensure commands still process
            await self.bot.process_commands(message)


    # Reset context
    @commands.command()
    async def resetcontext(self, ctx):
        """Reset this channel's DM conversation history."""
        await self.config.channel(ctx.channel).context.set([])
        await ctx.send("This channel's DM context has been reset.")
    
    @commands.command()
    async def uploadcompendium(self, ctx):
        """Upload an XML compendium file to update the SRD index."""
        if not ctx.message.attachments:
            return await ctx.send("Please attach an XML file with your command.")

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".xml"):
            return await ctx.send("Only .xml files are supported.")

        file_path = "C:/redbot/cogs/AiDm/Compendium.xml"
        await attachment.save(file_path)

        try:
            self.srd_index = self.load_compendium(file_path)
            await ctx.send(f"SRD compendium updated from `{attachment.filename}`.")
        except Exception as e:
            await ctx.send(f"Failed to parse XML: {e}")

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
                        limit = data.get("rate_limit", "N/A")
                        embed.add_field(
                            name=f"Key {i}",
                            value=f"```\nKey: {masked_key}\nRate Limit Remaining: {limit}\n```",
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
    
    #add item to SRD
    @commands.hybrid_command(name="addsrd", description="Add a new SRD entry to the XML file.")
    async def addsrd(self, ctx: commands.Context, title: str, description: str):
        self.append_to_srd_xml(title, description)
        await ctx.reply(f"✅ SRD entry for **{title}** added.", ephemeral=True)


       