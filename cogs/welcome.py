"""
🌸 Sakura Bot — cogs/welcome.py
Sends a styled embed to #welcome when a member joins.
Join/leave logging is handled by cogs/logging.py.
"""

import discord
from discord.ext import commands
import datetime
import logging

from core.config import CHANNEL_IDS, DEEP_CRIMSON

log = logging.getLogger(__name__)


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = member.guild.get_channel(CHANNEL_IDS.get("joins", 0))
        if not channel:
            log.warning("Welcome channel not found in guild %s", member.guild.id)
            return

        # Member count excluding bots
        member_count = sum(1 for m in member.guild.members if not m.bot)

        embed = discord.Embed(
            title="🩸 A New Soul Enters THE GATE!",
            description=(
                f"Welcome, {member.mention}! 🖤\n\n"
                f"You are member **#{member_count}** to join KARMA.\n\n"
                f"📜 Read our <#{CHANNEL_IDS['rules']}> and "
                f"verify yourself in <#{CHANNEL_IDS['verification']}> to get started!\n\n"
                f"*Karma judges all — make it count.*"
            ),
            colour=DEEP_CRIMSON,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="🌸 Sakura • Welcome!")
        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
