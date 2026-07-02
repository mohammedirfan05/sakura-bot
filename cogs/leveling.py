"""
🌸 Sakura Bot — cogs/leveling.py
XP-based leveling system:
  - Gains 15–25 XP per message (60s cooldown per user)
  - Channels that award XP are set in config.XP_CHANNEL_KEYS
  - Level-up announcement in the same channel
  - Auto-assigns progression roles at milestone levels (replaces old)
  - /rank  — shows a user's rank embed
  - /leaderboard — top 10 XP users
"""

import discord
from discord.ext import commands
from discord import app_commands
import random
import time
import logging

from core.config import CHANNEL_IDS, XP_CHANNEL_KEYS, XP_MIN, XP_MAX, XP_COOLDOWN_SECONDS, LEVEL_ROLES, DEEP_CRIMSON, GOLD
from core.database import db

log = logging.getLogger(__name__)

# Build the set of channel IDs that earn XP at import time
_XP_CHANNEL_IDS: set[int] = {CHANNEL_IDS[k] for k in XP_CHANNEL_KEYS if k in CHANNEL_IDS}


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._xp_cooldown: dict[int, float] = {}  # user_id → last-xp-awarded timestamp

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.channel.id not in _XP_CHANNEL_IDS:
            return

        uid = message.author.id
        now = time.time()

        if now - self._xp_cooldown.get(uid, 0) < XP_COOLDOWN_SECONDS:
            return
        self._xp_cooldown[uid] = now

        xp_gain = random.randint(XP_MIN, XP_MAX)
        new_xp, new_level, leveled_up = await db.add_xp(uid, xp_gain)

        if leveled_up:
            embed = discord.Embed(
                title="🩸 Level Up!",
                description=(
                    f"🎉 Congratulations {message.author.mention}! "
                    f"You reached **Level {new_level}**!"
                ),
                colour=DEEP_CRIMSON,
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            await message.channel.send(embed=embed)

            # Assign milestone role (remove previous level roles first)
            role_id = LEVEL_ROLES.get(new_level)
            if role_id:
                role = message.guild.get_role(role_id)
                if role:
                    old_roles = [
                        message.guild.get_role(rid)
                        for rid in LEVEL_ROLES.values()
                        if rid != role_id
                    ]
                    to_remove = [r for r in old_roles if r and r in message.author.roles]
                    try:
                        if to_remove:
                            await message.author.remove_roles(*to_remove)
                        await message.author.add_roles(role, reason=f"Level {new_level} milestone")
                    except discord.HTTPException as exc:
                        log.warning("Failed to assign level role for %s: %s", message.author, exc)

    # ── /rank ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="rank", description="Check your or another member's rank.")
    @app_commands.describe(member="Member to check (default: yourself)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        target = member or interaction.user
        user = await db.get_user(target.id)
        level    = user["level"]
        xp       = user["xp"]
        xp_need  = db.xp_for_level(level + 1)
        progress = int((xp / xp_need) * 20) if xp_need else 20
        bar = "█" * progress + "░" * (20 - progress)

        embed = discord.Embed(title=f"🩸 {target.display_name}'s Rank", colour=DEEP_CRIMSON)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Level",    value=f"**{level}**",                  inline=True)
        embed.add_field(name="XP",       value=f"**{xp:,}** / {xp_need:,}",    inline=True)
        embed.add_field(name="Progress", value=f"`{bar}` {progress * 5}%",      inline=False)
        embed.set_footer(text="🌸 Sakura Leveling")
        await interaction.response.send_message(embed=embed)

    # ── /leaderboard ──────────────────────────────────────────────────────────
    @app_commands.command(name="leaderboard", description="View the top 10 most active members.")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        top = await db.get_leaderboard(10)
        embed = discord.Embed(title="🐉 KARMA XP Leaderboard", colour=GOLD)
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, row in enumerate(top, 1):
            m = interaction.guild.get_member(row["user_id"])
            name  = m.display_name if m else f"Unknown ({row['user_id']})"
            medal = medals[i - 1] if i <= 3 else f"**#{i}**"
            lines.append(f"{medal} {name} — Level **{row['level']}** ({row['xp']:,} XP)")
        embed.description = "\n".join(lines) or "No data yet!"
        embed.set_footer(text="🌸 Sakura Leveling System")
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
