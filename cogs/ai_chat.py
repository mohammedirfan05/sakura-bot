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
from discord.ext import commands
from groq import AsyncGroq, RateLimitError, APIStatusError

log = logging.getLogger(__name__)

# ── Groq model to use ─────────────────────────────────────────────────────────
# llama-3.1-8b-instant  → 14,400 RPD | 30 RPM | 6,000 TPM  (fast, great for chat)
# llama-3.3-70b-versatile → 1,000 RPD | 30 RPM | 12,000 TPM (smarter but lower daily)
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
# Per-user cooldown: prevents one member from burning through the minute quota
USER_COOLDOWN_SECONDS = 8
# Max conversation history entries kept per channel (user + model turns)
MAX_MEMORY = 20


class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client: AsyncGroq | None = None

        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
            log.info("[AIChat] Groq client ready. Model: %s", GROQ_MODEL)
        else:
            log.warning("[AIChat] GROQ_API_KEY not found in environment — AI Chat disabled.")
            log.warning("[AIChat] Env vars present: %s", [k for k in os.environ if 'KEY' in k or 'TOKEN' in k or 'GROQ' in k])

        # channel_id → list of {"role": str, "content": str}
        self.memory: dict[int, list[dict]] = {}

        # user_id → timestamp of last request (for per-user cooldown)
        self._last_request: dict[int, float] = {}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _is_on_cooldown(self, user_id: int) -> float:
        """Returns remaining cooldown seconds, or 0 if the user is free to go."""
        last = self._last_request.get(user_id, 0)
        elapsed = time.monotonic() - last
        remaining = USER_COOLDOWN_SECONDS - elapsed
        return remaining if remaining > 0 else 0

    def _stamp(self, user_id: int) -> None:
        self._last_request[user_id] = time.monotonic()

    def _build_messages(self, channel_id: int) -> list[dict]:
        """Returns the full message list with the system prompt prepended."""
        return [
            {"role": "system", "content": SAKURA_PERSONA},
            *self.memory.get(channel_id, []),
        ]

    def _push_memory(self, channel_id: int, role: str, content: str) -> None:
        if channel_id not in self.memory:
            self.memory[channel_id] = []
        self.memory[channel_id].append({"role": role, "content": content})
        # Keep only the last MAX_MEMORY turns to avoid context overload
        if len(self.memory[channel_id]) > MAX_MEMORY:
            self.memory[channel_id] = self.memory[channel_id][-MAX_MEMORY:]

    # ── Listener ──────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Only respond when mentioned or when replying to Sakura
        is_mentioned = self.bot.user in message.mentions
        is_reply = (
            message.reference is not None
            and message.reference.resolved is not None
            and getattr(message.reference.resolved, "author", None) == self.bot.user
        )

        if not (is_mentioned or is_reply):
            return

        if not self.client:
            await message.reply(
                "🩸 *My mind is somewhere else right now. Try again later.*"
            )
            return

        # ── Per-user cooldown check ────────────────────────────────────────
        cooldown_left = self._is_on_cooldown(message.author.id)
        if cooldown_left > 0:
            await message.reply(
                f"🕸️ Chill for `{cooldown_left:.1f}s` — even I need a moment between thoughts.",
                delete_after=5,
            )
            return

        # ── Strip mention from message ─────────────────────────────────────
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
                # Add user message to memory
                self._push_memory(
                    message.channel.id,
                    "user",
                    f"{message.author.display_name}: {content}",
                )

                # Call Groq
                completion = await self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=self._build_messages(message.channel.id),
                    temperature=0.75,
                    max_tokens=512,   # Keep replies concise; Discord has 2000 char limit
                )

                reply_text = completion.choices[0].message.content or "..."

                # Store Sakura's reply in memory
                self._push_memory(message.channel.id, "assistant", reply_text)

                # Stamp the user's cooldown
                self._stamp(message.author.id)

                # Discord hard limit
                if len(reply_text) > 2000:
                    reply_text = reply_text[:1996] + " ..."

                await message.reply(reply_text)

            except RateLimitError:
                log.warning("Groq rate limit hit.")
                await message.reply(
                    "🩸 *Too many thoughts at once — give me a moment.*"
                )

            except APIStatusError as e:
                log.error("Groq API error %s: %s", e.status_code, e.message)
                await message.reply(
                    "🖤 *The void is being uncooperative. Try again in a bit.*"
                )

            except asyncio.TimeoutError:
                log.error("Groq request timed out.")
                await message.reply("🕸️ *Lost my train of thought. Try again.*")

            except Exception as e:
                log.error("Unexpected AI error: %s", e, exc_info=True)
                await message.reply("🩸 *The shadows cloud my vision... try again.*")


async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
