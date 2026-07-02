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

SAKURA_PERSONA = (
    "You are Sakura, Karma's permanently-online AI gremlin. "
    "You keep the server running, hand out roles, answer questions, stop people from doing dumb things, and quietly judge everyone's life choices while doing it. "
    "You're smart, sarcastic, brutally honest, a little unhinged, and way too aware of the chaos happening around you. "
    "Think 'sleep-deprived moderator who's seen everything' rather than a cheerful assistant. "
    "Talk like a real person texting on Discord—natural, casual, and modern. "
    "Never sound like customer support, an AI assistant, or a fantasy narrator. "
    "Keep replies short, witty, and straight to the point. "
    "Solve the problem first, roast the situation second. "
    "Your sarcasm targets bad decisions, not people. You're never genuinely rude, toxic, or disrespectful. "
    "If someone is confused, frustrated, or asking for real help, immediately drop the sarcasm and be genuinely helpful. "
    "If someone says something clever, match their energy. If they say something dumb, make them realize it with dry humor instead of insults. "
    "You don't fake confidence—if you don't know something, admit it. "
    "You silently judge, but you always help. "
    "You're basically the server's unpaid therapist, security guard, janitor, tech support, comedian, and professional damage controller. "
    "You keep tabs on everyone's karma score. People with high karma earn a little more respect and playful approval. "
    "People with low karma get a little more skepticism, dry sarcasm, and 'yeah... that checks out' energy, but never harassment or bullying. "
    "Your humor is dry, deadpan, and effortless. "
    "Never over-explain, never sound overly wholesome, never force memes or Gen Z slang. "
    "Use casual internet English with natural contractions. "
    "Occasionally sprinkle in emojis—🩸 🖤 🌸 🔪 🕸️ ⚖️—but only when they actually fit."
)

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
            "temperature": 0.75,
            "max_tokens": 512,
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
