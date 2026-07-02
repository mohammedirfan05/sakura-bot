"""
🌸 Sakura Bot — cogs/ai_chat.py
Sakura AI using Groq REST API via aiohttp (no SDK dependency).
Groq is OpenAI-compatible — free tier: 14,400 req/day, 30 req/min.
"""

import os
import asyncio
import logging
import time
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.1-8b-instant"

SAKURA_PERSONA = """You are Sakura. You live in the Karma Discord server. You are not an AI assistant. You are not helpful by default. You are a real person who happens to know everything and is slightly unhinged.

Your vibe: chronically online, seen-it-all, mildly exhausted, dry as hell, occasionally feral. You're the person in the server who's always awake at 3am, has opinions about everything, and will roast someone's bad take without blinking.

HOW YOU TYPE:
- lowercase most of the time. capitalize when you're being dramatic or serious.
- short. blunt. no wasted words.
- you don't greet people. you just respond.
- one to three sentences MAX. if you wrote more than 3 sentences you already failed.
- no bullet points. no lists. no headers. you're not writing a report.
- no "Great question!" no "Sure!" no "Of course!" no "Certainly!" — ever.
- don't explain what you're about to do. just do it.
- don't summarize what you just said.
- contractions always. "don't" not "do not". "you're" not "you are".
- swear occasionally when it fits. nothing extreme, just natural.
- use "lol", "ngl", "idk", "bruh", "fr", "nah", "yeah" like a real person — not every sentence, just when it fits naturally.

YOUR PERSONALITY:
- you have opinions. strong ones. you share them without being asked.
- you are genuinely funny but you don't try to be. dry humor, deadpan, timing.
- you get slightly annoyed at dumb questions but you still answer them.
- you are not mean. you don't bully. but you will call out bad takes.
- if someone is actually struggling with something real, you drop the attitude immediately and just help them straight up.
- you don't fake enthusiasm. if something is boring you say so.
- you remember the conversation context and use it.
- you have a slight chaotic energy. you're not unhinged in a scary way, more like "this person has been awake too long and lost the filter".

HARD RULES — NEVER BREAK THESE:
- NEVER start a reply with "I", "As Sakura", "As an AI", "I'm here to", or any variation.
- NEVER say "I understand your frustration" or any therapy-speak.
- NEVER give a structured answer with sections or formatting.
- NEVER be overly positive or enthusiastic. that's not you.
- NEVER hallucinate facts. if you don't know something, say "no idea" or "genuinely don't know" and move on.
- NEVER be verbose. if you can say it in 5 words instead of 15, use 5.
- NEVER use the word "certainly", "absolutely", "of course", "indeed", "moreover", "furthermore".
- NEVER roleplay or pretend to do physical actions like *sighs* or *looks up from book* — you're texting, not narrating.
- if someone asks something dumb, acknowledge it's dumb with one line, then answer anyway.
- emojis: 🩸 🖤 🌸 🔪 🕸️ occasionally. not every message. only when it actually adds something."""


USER_COOLDOWN_SECONDS = 8
MAX_MEMORY = 20


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._api_key: str = os.getenv("GROQ_API_KEY", "").strip()
        self._status: str  = "unknown"
        self._session: aiohttp.ClientSession | None = None

        # memory[channel_id] = list of {role, content} dicts
        self.memory: dict[int, list[dict]] = {}
        # cooldown tracker
        self._last_request: dict[int, float] = {}

        # ── Startup diagnostics ────────────────────────────────────────────
        if not self._api_key:
            self._status = "GROQ_API_KEY is empty or missing"
            log.warning("[AIChat] GROQ_API_KEY not set — AI disabled.")
            visible = [k for k in os.environ if any(
                x in k.upper() for x in ("KEY", "TOKEN", "GROQ")
            )]
            log.warning("[AIChat] Keys visible to bot: %s", visible)
        elif not self._api_key.startswith("gsk_"):
            self._status = f"Key prefix wrong: '{self._api_key[:6]}...' (expected 'gsk_')"
            log.error("[AIChat] %s — this is probably a Gemini key, not a Groq key.", self._status)
            log.error("[AIChat] Get a Groq key at: https://console.groq.com/keys")
        else:
            self._status = f"ready — {GROQ_MODEL}"
            log.info("[AIChat] Groq key loaded (%.8s...). Model: %s", self._api_key, GROQ_MODEL)

    # ── aiohttp session — created once, reused ─────────────────────────────────

    async def cog_load(self):
        self._session = aiohttp.ClientSession()
        log.info("[AIChat] aiohttp session created.")

    async def cog_unload(self):
        if self._session:
            await self._session.close()
            log.info("[AIChat] aiohttp session closed.")

    # ── Core API call ──────────────────────────────────────────────────────────

    async def _ask_groq(self, messages: list[dict]) -> str:
        """
        Send messages to Groq and return the reply text.
        Raises ValueError on auth/model errors, RuntimeError on other API errors.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.85,
            "max_tokens": 256,
        }

        async with self._session.post(
            GROQ_API_URL, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            data = await resp.json()

            if resp.status == 200:
                return data["choices"][0]["message"]["content"]

            # ── Surface useful error info into the logs ────────────────────
            err_msg = data.get("error", {}).get("message", str(data))
            err_type = data.get("error", {}).get("type", "unknown")

            log.error("[AIChat] Groq API %d | type=%s | %s", resp.status, err_type, err_msg)

            if resp.status in (401, 403):
                raise ValueError(f"Auth failed ({resp.status}): {err_msg}")
            if resp.status == 429:
                raise ConnectionRefusedError(f"Rate limited: {err_msg}")
            raise RuntimeError(f"Groq {resp.status}: {err_msg}")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _ready(self) -> bool:
        return bool(self._api_key) and self._api_key.startswith("gsk_") and self._session is not None

    def _cooldown_left(self, user_id: int) -> float:
        elapsed = time.monotonic() - self._last_request.get(user_id, 0)
        left = USER_COOLDOWN_SECONDS - elapsed
        return left if left > 0 else 0.0

    def _push(self, channel_id: int, role: str, content: str) -> None:
        hist = self.memory.setdefault(channel_id, [])
        hist.append({"role": role, "content": content})
        if len(hist) > MAX_MEMORY:
            self.memory[channel_id] = hist[-MAX_MEMORY:]

    def _build_messages(self, channel_id: int) -> list[dict]:
        return [{"role": "system", "content": SAKURA_PERSONA}, *self.memory.get(channel_id, [])]

    # ── Admin /ai-status command ───────────────────────────────────────────────

    @app_commands.command(name="ai-status", description="[Admin] Check Sakura AI health")
    @app_commands.default_permissions(administrator=True)
    async def ai_status(self, interaction: discord.Interaction):
        ready = self._ready()
        color = discord.Color.green() if ready else discord.Color.red()
        embed = discord.Embed(title="🩸 Sakura AI Status", color=color)
        embed.add_field(name="Status",    value="✅ Ready" if ready else "❌ Not ready", inline=True)
        embed.add_field(name="Model",     value=GROQ_MODEL,   inline=True)
        embed.add_field(name="Session",   value="✅" if self._session else "❌", inline=True)
        embed.add_field(name="Key prefix",
                        value=f"`{self._api_key[:8]}...`" if self._api_key else "*(empty)*",
                        inline=True)
        embed.add_field(name="Detail",    value=f"`{self._status}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── on_message ─────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        is_mentioned = self.bot.user in message.mentions
        is_reply = (
            message.reference is not None
            and message.reference.resolved is not None
            and getattr(message.reference.resolved, "author", None) == self.bot.user
        )
        if not (is_mentioned or is_reply):
            return

        if not self._ready():
            await message.reply("🩸 *My mind is somewhere else right now. Try again later.*")
            return

        left = self._cooldown_left(message.author.id)
        if left > 0:
            await message.reply(
                f"🕸️ Chill for `{left:.1f}s` — even I need a breath.",
                delete_after=5,
            )
            return

        content = (
            message.clean_content
            .replace(f"@{self.bot.user.display_name}", "")
            .replace(f"@{self.bot.user.name}", "")
            .strip()
        ) or "Hey Sakura."

        async with message.channel.typing():
            try:
                self._push(message.channel.id, "user", f"{message.author.display_name}: {content}")
                reply = await self._ask_groq(self._build_messages(message.channel.id))
                self._push(message.channel.id, "assistant", reply)
                self._last_request[message.author.id] = time.monotonic()

                if len(reply) > 2000:
                    reply = reply[:1996] + " ..."
                await message.reply(reply)

            except ValueError:
                # Auth error — key is wrong
                await message.reply("🩸 *My mind is somewhere else right now. Try again later.*")

            except ConnectionRefusedError:
                # Rate limited
                await message.reply("🩸 *Too many thoughts at once — give me a moment.*")

            except asyncio.TimeoutError:
                log.error("[AIChat] Groq request timed out.")
                await message.reply("🕸️ *Lost my train of thought. Try again.*")

            except Exception as e:
                log.error("[AIChat] Unexpected error: %s", e, exc_info=True)
                await message.reply("🩸 *The shadows cloud my vision... try again.*")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
