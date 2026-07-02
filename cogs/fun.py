"""
🌸 Sakura Bot — cogs/fun.py
Fun commands:
  /8ball, /coinflip, /meme (meme-api.com), /cat, /dog, /avatar, /banner
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
import logging

from core.config import DEEP_CRIMSON, GOLD

log = logging.getLogger(__name__)

EIGHT_BALL_RESPONSES = [
    "🖤 It is certain.",
    "🖤 Without a doubt.",
    "🖤 Yes, definitely!",
    "🖤 You may rely on it.",
    "🖤 Most likely.",
    "🖤 Signs point to yes.",
    "🖤 Reply hazy, try again.",
    "🖤 Ask again later.",
    "🖤 Cannot predict now.",
    "🖤 Don't count on it.",
    "🖤 My sources say no.",
    "🖤 Very doubtful.",
    "🖤 Outlook not so good.",
]


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self):
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": "SakuraBot/2.0 (Discord Bot)"}
        )

    async def cog_unload(self):
        if self.session:
            await self.session.close()
            self.session = None

    # ── /8ball ────────────────────────────────────────────────────────────────
    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question.")
    @app_commands.describe(question="Your question")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        answer = random.choice(EIGHT_BALL_RESPONSES)
        embed = discord.Embed(colour=DEEP_CRIMSON)
        embed.add_field(name="❓ Question", value=question, inline=False)
        embed.add_field(name="🎱 Answer",   value=answer,   inline=False)
        embed.set_footer(text="🌸 Sakura Magic 8-Ball")
        await interaction.response.send_message(embed=embed)

    # ── /coinflip ─────────────────────────────────────────────────────────────
    @app_commands.command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["🪙 Heads", "🪙 Tails"])
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"It landed on… **{result}**!",
            colour=GOLD,
        )
        await interaction.response.send_message(embed=embed)

    # ── /meme (meme-api.com — no auth required) ───────────────────────────────
    @app_commands.command(name="meme", description="Get a random meme.")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.session.get("https://meme-api.com/gimme") as resp:
                if resp.status != 200:
                    raise ValueError(f"API returned {resp.status}")
                data = await resp.json()
                if data.get("nsfw"):
                    # Retry once with a safe subreddit
                    async with self.session.get("https://meme-api.com/gimme/wholesomememes") as r2:
                        data = await r2.json()
                embed = discord.Embed(
                    title=data["title"][:256],
                    url=data["postLink"],
                    colour=DEEP_CRIMSON,
                )
                embed.set_image(url=data["url"])
                embed.set_footer(text=f"🌸 r/{data['subreddit']} • 👍 {data.get('ups', 0):,}")
                await interaction.followup.send(embed=embed)
        except Exception as exc:
            log.warning("Meme fetch failed: %s", exc)
            await interaction.followup.send("❌ Couldn't fetch a meme right now. Try again!", ephemeral=True)

    # ── /cat ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="cat", description="Get a random cat photo 🐱")
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.session.get("https://api.thecatapi.com/v1/images/search") as resp:
                data = await resp.json()
                url = data[0]["url"]
            embed = discord.Embed(title="🐱 Meow!", colour=DEEP_CRIMSON)
            embed.set_image(url=url)
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            log.warning("Cat fetch failed: %s", exc)
            await interaction.followup.send("❌ Couldn't fetch a cat. Try again!", ephemeral=True)

    # ── /dog ──────────────────────────────────────────────────────────────────
    @app_commands.command(name="dog", description="Get a random dog photo 🐶")
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with self.session.get("https://dog.ceo/api/breeds/image/random") as resp:
                data = await resp.json()
                url = data["message"]
            embed = discord.Embed(title="🐶 Woof!", colour=DEEP_CRIMSON)
            embed.set_image(url=url)
            await interaction.followup.send(embed=embed)
        except Exception as exc:
            log.warning("Dog fetch failed: %s", exc)
            await interaction.followup.send("❌ Couldn't fetch a dog. Try again!", ephemeral=True)

    # ── /avatar ───────────────────────────────────────────────────────────────
    @app_commands.command(name="avatar", description="View a member's avatar.")
    @app_commands.describe(member="Member (default: yourself)")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        embed = discord.Embed(title=f"🖤 {target.display_name}'s Avatar", colour=DEEP_CRIMSON)
        embed.set_image(url=target.display_avatar.url)
        embed.set_footer(text="🌸 Sakura")
        await interaction.response.send_message(embed=embed)

    # ── /banner ───────────────────────────────────────────────────────────────
    @app_commands.command(name="banner", description="View a member's profile banner.")
    @app_commands.describe(member="Member (default: yourself)")
    async def banner(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        fetched = await interaction.client.fetch_user(target.id)
        if not fetched.banner:
            await interaction.response.send_message(
                f"❌ **{target.display_name}** doesn't have a profile banner set.", ephemeral=True
            )
            return
        embed = discord.Embed(title=f"🖤 {target.display_name}'s Banner", colour=DEEP_CRIMSON)
        embed.set_image(url=fetched.banner.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
