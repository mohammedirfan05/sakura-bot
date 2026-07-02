"""
🌸 Sakura Bot — cogs/logging.py
Event listener cog. Posts styled embeds to the appropriate log channels:
  - Message edits / deletions  → #logs
  - Voice state changes        → #logs
  - Member join / leave        → #join_leave_logs
  - Role / nickname changes    → #logs
"""

import discord
from discord.ext import commands
import datetime
import logging

from core.config import CHANNEL_IDS, ERROR_RED, INFO_BLUE, SUCCESS_GREEN, DEEP_CRIMSON

log = logging.getLogger(__name__)


class Logging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_log_channel(self, guild: discord.Guild, key: str = "logs") -> discord.TextChannel | None:
        ch = guild.get_channel(CHANNEL_IDS.get(key))
        if not ch:
            log.debug("Log channel '%s' not found in guild %s", key, guild.id)
        return ch

    # ── Message deleted ───────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        ch = self._get_log_channel(message.guild)
        if not ch:
            return
        embed = discord.Embed(
            title="🗑️ Message Deleted",
            colour=ERROR_RED,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Author",  value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(
            name="Content",
            value=message.content[:1024] or "*[no text / attachment only]*",
            inline=False,
        )
        embed.set_footer(text=f"Author ID: {message.author.id}")
        await ch.send(embed=embed)

    # ── Message edited ────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content or not before.guild:
            return
        ch = self._get_log_channel(before.guild)
        if not ch:
            return
        embed = discord.Embed(
            title="✏️ Message Edited",
            colour=INFO_BLUE,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.add_field(name="Author",  value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Before",  value=before.content[:512] or "*[empty]*", inline=False)
        embed.add_field(name="After",   value=after.content[:512]  or "*[empty]*", inline=False)
        embed.add_field(name="Jump",    value=f"[Jump to message]({after.jump_url})", inline=False)
        embed.set_footer(text=f"Author ID: {before.author.id}")
        await ch.send(embed=embed)

    # ── Member join ───────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ch = self._get_log_channel(member.guild, "join_leave_logs")
        if not ch:
            return
        embed = discord.Embed(
            description=f"📥 **{member}** joined the server.",
            colour=SUCCESS_GREEN,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        account_age = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
        embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
        embed.set_footer(text=f"ID: {member.id}")
        await ch.send(embed=embed)

    # ── Member leave ──────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        ch = self._get_log_channel(member.guild, "join_leave_logs")
        if not ch:
            return
        embed = discord.Embed(
            description=f"📤 **{member}** left the server.",
            colour=ERROR_RED,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}")
        await ch.send(embed=embed)

    # ── Voice state change ────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        ch = self._get_log_channel(member.guild)
        if not ch:
            return

        if before.channel is None and after.channel is not None:
            desc = f"📥 {member.mention} **joined** {after.channel.mention}"
            colour = SUCCESS_GREEN
        elif before.channel is not None and after.channel is None:
            desc = f"📤 {member.mention} **left** {before.channel.mention}"
            colour = ERROR_RED
        elif before.channel != after.channel:
            desc = f"🔄 {member.mention} moved {before.channel.mention} → {after.channel.mention}"
            colour = INFO_BLUE
        else:
            return  # mute/deaf toggle — don't log

        embed = discord.Embed(
            description=desc,
            colour=colour,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_footer(text=f"ID: {member.id}")
        await ch.send(embed=embed)

    # ── Member role / nickname changes ────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        ch = self._get_log_channel(before.guild)
        if not ch:
            return

        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Nickname Changed",
                colour=INFO_BLUE,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.add_field(name="Member", value=after.mention, inline=True)
            embed.add_field(name="Before", value=before.nick or "*None*", inline=True)
            embed.add_field(name="After",  value=after.nick  or "*None*", inline=True)
            embed.set_footer(text=f"ID: {after.id}")
            await ch.send(embed=embed)

        added   = [r for r in after.roles  if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]
        if added or removed:
            embed = discord.Embed(
                title="🎭 Roles Updated",
                colour=DEEP_CRIMSON,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            embed.add_field(name="Member", value=after.mention, inline=False)
            if added:
                embed.add_field(name="Added",   value=" ".join(r.mention for r in added),   inline=True)
            if removed:
                embed.add_field(name="Removed", value=" ".join(r.mention for r in removed), inline=True)
            embed.set_footer(text=f"ID: {after.id}")
            await ch.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Logging(bot))
