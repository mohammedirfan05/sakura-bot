"""
🌸 Sakura Bot — cogs/ai_chat.py
Custom AI Persona using Gemini. Sakura responds to pings or replies
with her dark, vampiric personality.
"""

import os
import logging
import discord
from discord.ext import commands
from google import genai
from google.genai import types

log = logging.getLogger(__name__)

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

class AIChat(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            log.warning("GEMINI_API_KEY not found in .env! AI Chat will be disabled.")
            
        self.memory: dict[int, list[types.Content]] = {}
        self.max_memory = 15

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        is_mentioned = self.bot.user in message.mentions
        is_reply = False
        if message.reference and message.reference.resolved:
            if getattr(message.reference.resolved, "author", None) == self.bot.user:
                is_reply = True

        if not (is_mentioned or is_reply):
            return

        if not self.client:
            await message.channel.send("🩸 *My mind is currently disconnected. (GEMINI_API_KEY is missing from `.env`)*")
            return
            
        content = message.clean_content.replace(f"@{self.bot.user.display_name}", "").replace(f"@{self.bot.user.name}", "").strip()
        if not content:
            content = "Hello, Sakura."

        async with message.channel.typing():
            try:
                channel_id = message.channel.id
                if channel_id not in self.memory:
                    self.memory[channel_id] = []
                    
                self.memory[channel_id].append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=f"{message.author.display_name}: {content}")]
                    )
                )
                
                if len(self.memory[channel_id]) > self.max_memory:
                    self.memory[channel_id] = self.memory[channel_id][-self.max_memory:]

                response = await self.client.aio.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=self.memory[channel_id],
                    config=types.GenerateContentConfig(
                        system_instruction=SAKURA_PERSONA,
                        temperature=0.7,
                    )
                )
                
                reply_text = response.text

                self.memory[channel_id].append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=reply_text)]
                    )
                )

                if len(reply_text) > 2000:
                    reply_text = reply_text[:1996] + "..."
                    
                await message.reply(reply_text)

            except Exception as e:
                log.error("Error generating AI response: %s", e, exc_info=True)
                await message.reply("🩸 *The shadows cloud my vision... I cannot answer right now.*")

async def setup(bot: commands.Bot):
    await bot.add_cog(AIChat(bot))
