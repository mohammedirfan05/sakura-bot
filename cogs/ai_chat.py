"""
🌸 Sakura Bot — cogs/ai_chat.py
Custom AI Persona using Groq (Llama 3.1). Sakura responds to pings or replies
with her dark, sarcastic personality. Groq's free tier: 14,400 req/day,
30 req/min — far more generous than Gemini for a Discord community.
"""

import os
import asyncio
import logging
import time
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

# ── Try importing Groq — fail gracefully if not installed ─────────────────────
try:
    from groq import AsyncGroq, RateLimitError, APIStatusError
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    AsyncGroq = None
    RateLimitError = Exception
    APIStatusError = Exception
    log.error("[AIChat] 'groq' package not installed! Run: pip install groq>=0.9.0")

# ── Groq model ────────────────────────────────────────────────────────────────
# llama-3.1-8b-instant  → 14,400 RPD | 30 RPM | fast & free
# llama-3.3-70b-versatile → 1,000 RPD | 30 RPM | smarter but lower daily limit
GROQ_MODEL = "llama-3.1-8b-instant"

# ── Sakura's personality ───────────────────────────────────────────────────────
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

# ── Rate limit config ──────────────────────────────────────────────────────────
USER_COOLDOWN_SECONDS = 8   # per-user cooldown to protect the 30 RPM quota
MAX_MEMORY = 20              # max chat history turns per channel


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client: "AsyncGroq | None" = None
        self._status_reason: str = "Unknown"

        # ── Diagnose env + package on startup ─────────────────────────────
        if not GROQ_AVAILABLE:
            self._status_reason = "groq package not installed"
            log.error("[AIChat] groq package missing — AI Chat disabled.")
            return

        api_key = os.getenv("GROQ_API_KEY", "").strip()

        if not api_key:
            self._status_reason = "GROQ_API_KEY env var is empty or missing"
            log.warning("[AIChat] GROQ_API_KEY not set — AI Chat disabled.")
            # Log what keys ARE visible so Railway issues are obvious
            visible = [k for k in os.environ if any(
                word in k.upper() for word in ("KEY", "TOKEN", "GROQ", "GEMINI")
            )]
            log.warning("[AIChat] Keys visible in env: %s", visible)
            return

        if not api_key.startswith("gsk_"):
            self._status_reason = (
                f"GROQ_API_KEY looks wrong — expected to start with 'gsk_', "
                f"got '{api_key[:6]}...'"
            )
            log.error("[AIChat] %s", self._status_reason)
            # Still try to use it — Groq may change their key format
        
        try:
            self.client = AsyncGroq(api_key=api_key)
            self._status_reason = f"OK — model: {GROQ_MODEL}"
            log.info("[AIChat] Groq client ready. Model: %s | Key prefix: %s...", 
                     GROQ_MODEL, api_key[:8])
        except Exception as e:
            self._status_reason = f"AsyncGroq init failed: {e}"
            log.error("[AIChat] Failed to create Groq client: %s", e)

        # channel_id → list of {"role": str, "content": str}
        self.memory: dict[int, list[dict]] = {}
        # user_id → monotonic timestamp of last successful request
        self._last_request: dict[int, float] = {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_on_cooldown(self, user_id: int) -> float:
        last = self._last_request.get(user_id, 0)
        elapsed = time.monotonic() - last
        remaining = USER_COOLDOWN_SECONDS - elapsed
        return remaining if remaining > 0 else 0.0

    def _stamp(self, user_id: int) -> None:
        self._last_request[user_id] = time.monotonic()

    def _build_messages(self, channel_id: int) -> list[dict]:
        return [
            {"role": "system", "content": SAKURA_PERSONA},
            *self.memory.get(channel_id, []),
        ]

    def _push_memory(self, channel_id: int, role: str, content: str) -> None:
        hist = self.memory.setdefault(channel_id, [])
        hist.append({"role": role, "content": content})
        if len(hist) > MAX_MEMORY:
            self.memory[channel_id] = hist[-MAX_MEMORY:]

    # ── Admin status command ───────────────────────────────────────────────────

    @app_commands.command(name="ai-status", description="[Admin] Check Sakura AI status")
    @app_commands.default_permissions(administrator=True)
    async def ai_status(self, interaction: discord.Interaction):
        """Owner/admin can check the AI module status without touching Railway logs."""
        package_ok = "✅" if GROQ_AVAILABLE else "❌"
        client_ok  = "✅" if self.client else "❌"
        embed = discord.Embed(
            title="🩸 Sakura AI Status",
            color=discord.Color.from_str("#9B59B6"),
        )
        embed.add_field(name="Groq Package", value=f"{package_ok} {'Installed' if GROQ_AVAILABLE else 'MISSING'}", inline=True)
        embed.add_field(name="Client",       value=f"{client_ok} {'Ready' if self.client else 'Not ready'}", inline=True)
        embed.add_field(name="Model",        value=GROQ_MODEL, inline=True)
        embed.add_field(name="Status Detail", value=f"`{self._status_reason}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── on_message listener ────────────────────────────────────────────────────

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

        # Client not ready — silent in-character response, nothing technical
        if not self.client:
            await message.reply("🩸 *My mind is somewhere else right now. Try again later.*")
            return

        # Per-user cooldown
        cooldown_left = self._is_on_cooldown(message.author.id)
        if cooldown_left > 0:
            await message.reply(
                f"🕸️ Chill for `{cooldown_left:.1f}s` — even I need a moment between thoughts.",
                delete_after=5,
            )
            return

        # Strip bot mention from message
        content = (
            message.clean_content
            .replace(f"@{self.bot.user.display_name}", "")
            .replace(f"@{self.bot.user.name}", "")
            .strip()
        )
        if not content:
            content = "Hey Sakura."

        async with message.channel.typing():
            try:
                self._push_memory(
                    message.channel.id,
                    "user",
                    f"{message.author.display_name}: {content}",
                )

                completion = await self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=self._build_messages(message.channel.id),
                    temperature=0.75,
                    max_tokens=512,
                )

                reply_text = completion.choices[0].message.content or "..."
                self._push_memory(message.channel.id, "assistant", reply_text)
                self._stamp(message.author.id)

                if len(reply_text) > 2000:
                    reply_text = reply_text[:1996] + " ..."

                await message.reply(reply_text)

            except RateLimitError:
                log.warning("[AIChat] Groq rate limit hit.")
                await message.reply("🩸 *Too many thoughts at once — give me a moment.*")

            except APIStatusError as e:
                log.error("[AIChat] Groq API error %s: %s", e.status_code, e.message)
                await message.reply("🖤 *The void is being uncooperative. Try again in a bit.*")

            except asyncio.TimeoutError:
                log.error("[AIChat] Groq request timed out.")
                await message.reply("🕸️ *Lost my train of thought. Try again.*")

            except Exception as e:
                log.error("[AIChat] Unexpected error: %s", e, exc_info=True)
                await message.reply("🩸 *The shadows cloud my vision... try again.*")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
