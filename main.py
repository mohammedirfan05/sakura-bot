"""
🌸 Sakura Bot — main.py
Entry point: loads environment, validates token, and starts the bot.
"""

import os
import asyncio
from dotenv import load_dotenv
from core.bot import SakuraBot

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

INITIAL_EXTENSIONS = [
    "cogs.custom_commands",
    "cogs.fun",
    "cogs.logging",
    "cogs.moderation",
    "cogs.reaction_roles",
    "cogs.verification",
    "cogs.welcome",
]


async def main():
    if not TOKEN:
        print("❌ Error: BOT_TOKEN not found in .env file.")
        return

    async with SakuraBot() as bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
