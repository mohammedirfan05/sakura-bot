"""
🌸 Sakura Bot — cogs/moderation.py
Full moderation suite: /ban /kick /warn /timeout /unwarn /warnings /clear /lock /unlock
Every action is logged to #mod_logs with a styled embed.
Warn thresholds trigger automatic punishments.
"""

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import logging

from core.config import (
    CHANNEL_IDS, ERROR_RED, WARNING_YELLOW, SUCCESS_GREEN,
    WARN_TIMEOUT_THRESHOLD, WARN_KICK_THRESHOLD, WARN_BAN_THRESHOLD,
)
from core.database import db
from utils.checks import is_staff, is_admin

log = logging.getLogger(__name__)


async def log_mod_action(guild: discord.Guild, title: str, colour: int, **fields):
    """Post a styled mod-action embed to #mod_logs."""
    channel = guild.get_channel(CHANNEL_IDS["mod_logs"])
    if not channel:
        return
    embed = discord.Embed(
        title=f"⚔️ {title}",
        colour=colour,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    for name, value in fields.items():
        embed.add_field(name=name, value=str(value), inline=True)
    embed.set_footer(text="⚖️ KARMA COURT")
    try:
        await channel.send(embed=embed)
    except Exception as exc:
        log.warning("Could not post mod log: %s", exc)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /ban ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="ban", description="Ban a member from the server.")
    @app_commands.default_permissions(ban_members=True)
    @is_staff()
    @app_commands.describe(
        member="Member to ban",
        reason="Reason for the ban",
        delete_days="Days of messages to delete (0–7)",
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
        delete_days: app_commands.Range[int, 0, 7] = 1,
    ):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ You cannot ban someone with an equal or higher role.", ephemeral=True
            )
            return
        try:
            await member.send(
                embed=discord.Embed(
                    description=f"🚫 You have been **banned** from **KARMA**.\n**Reason:** {reason}",
                    colour=ERROR_RED,
                )
            )
        except Exception:
            pass
        await member.ban(reason=f"{reason} | Mod: {interaction.user}", delete_message_days=delete_days)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"🚫 **{member}** has been banned.\n**Reason:** {reason}",
                colour=ERROR_RED,
            )
        )
        await log_mod_action(
            interaction.guild, "Member Banned", ERROR_RED,
            Member=member.mention, Moderator=interaction.user.mention, Reason=reason,
        )

    # ── /kick ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.default_permissions(kick_members=True)
    @is_staff()
    @app_commands.describe(member="Member to kick", reason="Reason for the kick")
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        if member.top_role >= interaction.user.top_role:
            await interaction.response.send_message(
                "❌ You cannot kick someone with an equal or higher role.", ephemeral=True
            )
            return
        try:
            await member.send(
                embed=discord.Embed(
                    description=f"👢 You have been **kicked** from **KARMA**.\n**Reason:** {reason}",
                    colour=WARNING_YELLOW,
                )
            )
        except Exception:
            pass
        await member.kick(reason=f"{reason} | Mod: {interaction.user}")
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"👢 **{member}** has been kicked.\n**Reason:** {reason}",
                colour=WARNING_YELLOW,
            )
        )
        await log_mod_action(
            interaction.guild, "Member Kicked", WARNING_YELLOW,
            Member=member.mention, Moderator=interaction.user.mention, Reason=reason,
        )

    # ── /timeout ──────────────────────────────────────────────────────────────
    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.default_permissions(moderate_members=True)
    @is_staff()
    @app_commands.describe(
        member="Member to timeout",
        minutes="Duration in minutes (1–40320 / 28 days)",
        reason="Reason",
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320] = 60,
        reason: str = "No reason provided",
    ):
        until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"⏱️ **{member}** timed out for **{minutes}m**.\n**Reason:** {reason}",
                colour=WARNING_YELLOW,
            )
        )
        await log_mod_action(
            interaction.guild, "Member Timed Out", WARNING_YELLOW,
            Member=member.mention, Duration=f"{minutes} minutes",
            Moderator=interaction.user.mention, Reason=reason,
        )

    # ── /warn ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="warn", description="Warn a member.")
    @app_commands.default_permissions(moderate_members=True)
    @is_staff()
    @app_commands.describe(member="Member to warn", reason="Reason for the warning")
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided",
    ):
        await interaction.response.defer()
        total = await db.add_warning(member.id, interaction.guild_id, interaction.user.id, reason)
        await interaction.followup.send(
            embed=discord.Embed(
                description=(
                    f"⚠️ **{member}** has been warned. (**{total}** total warnings)\n"
                    f"**Reason:** {reason}"
                ),
                colour=WARNING_YELLOW,
            )
        )
        try:
            await member.send(
                embed=discord.Embed(
                    description=(
                        f"⚠️ You have been warned in **KARMA**.\n"
                        f"**Reason:** {reason}\n**Total warns:** {total}"
                    ),
                    colour=WARNING_YELLOW,
                )
            )
        except Exception:
            pass
        await log_mod_action(
            interaction.guild, "Member Warned", WARNING_YELLOW,
            Member=member.mention, Warns=total,
            Moderator=interaction.user.mention, Reason=reason,
        )

        # Threshold auto-punishments
        guild = interaction.guild
        until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

        if total >= WARN_BAN_THRESHOLD:
            try:
                await member.ban(reason=f"Auto-ban: {total} warnings")
                await log_mod_action(guild, "Auto-Ban (Warn Threshold)", ERROR_RED,
                                     Member=member.mention, Warns=total)
            except discord.HTTPException as exc:
                log.warning("Auto-ban failed for %s: %s", member, exc)
        elif total >= WARN_KICK_THRESHOLD:
            try:
                await member.kick(reason=f"Auto-kick: {total} warnings")
                await log_mod_action(guild, "Auto-Kick (Warn Threshold)", WARNING_YELLOW,
                                     Member=member.mention, Warns=total)
            except discord.HTTPException as exc:
                log.warning("Auto-kick failed for %s: %s", member, exc)
        elif total >= WARN_TIMEOUT_THRESHOLD:
            try:
                await member.timeout(until, reason=f"Auto-timeout: {total} warnings")
                await log_mod_action(guild, "Auto-Timeout (Warn Threshold)", WARNING_YELLOW,
                                     Member=member.mention, Warns=total, Duration="1 hour")
            except discord.HTTPException as exc:
                log.warning("Auto-timeout failed for %s: %s", member, exc)

    # ── /warnings ─────────────────────────────────────────────────────────────
    @app_commands.command(name="warnings", description="View a member's warnings.")
    @app_commands.default_permissions(moderate_members=True)
    @is_staff()
    @app_commands.describe(member="Member to check")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        warns = await db.get_warnings(member.id, interaction.guild_id)
        if not warns:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ **{member}** has no warnings.",
                    colour=SUCCESS_GREEN,
                ),
                ephemeral=True,
            )
            return
        embed = discord.Embed(title=f"⚠️ Warnings for {member}", colour=WARNING_YELLOW)
        for i, w in enumerate(warns, 1):
            embed.add_field(
                name=f"Warning #{i}",
                value=f"**Reason:** {w['reason']}\n**Moderator:** <@{w['moderator']}>",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /unwarn ───────────────────────────────────────────────────────────────
    @app_commands.command(name="unwarn", description="Clear all warnings for a member.")
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    @app_commands.describe(member="Member to clear warnings for")
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member):
        await db.clear_warnings(member.id, interaction.guild_id)
        await interaction.response.send_message(
            embed=discord.Embed(
                description=f"✅ All warnings cleared for **{member}**.",
                colour=SUCCESS_GREEN,
            ),
            ephemeral=True,
        )
        await log_mod_action(
            interaction.guild, "Warnings Cleared", SUCCESS_GREEN,
            Member=member.mention, Moderator=interaction.user.mention,
        )

    # ── /clear ────────────────────────────────────────────────────────────────
    @app_commands.command(name="clear", description="Bulk-delete messages in this channel.")
    @app_commands.default_permissions(manage_messages=True)
    @is_staff()
    @app_commands.describe(amount="Number of messages to delete (1–100)")
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 100] = 10,
    ):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            embed=discord.Embed(
                description=f"🗑️ Deleted **{len(deleted)}** messages.",
                colour=SUCCESS_GREEN,
            ),
            ephemeral=True,
        )
        await log_mod_action(
            interaction.guild, "Messages Purged", WARNING_YELLOW,
            Channel=interaction.channel.mention,
            Amount=len(deleted),
            Moderator=interaction.user.mention,
        )

    # ── /lock ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="lock", description="Lock the current channel.")
    @app_commands.default_permissions(manage_channels=True)
    @is_staff()
    async def lock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(
            interaction.guild.default_role, send_messages=False
        )
        await interaction.response.send_message(
            embed=discord.Embed(
                description="🔒 Channel locked. Only staff can send messages.",
                colour=ERROR_RED,
            )
        )
        await log_mod_action(
            interaction.guild, "Channel Locked", ERROR_RED,
            Channel=interaction.channel.mention, Moderator=interaction.user.mention,
        )

    # ── /unlock ───────────────────────────────────────────────────────────────
    @app_commands.command(name="unlock", description="Unlock the current channel.")
    @app_commands.default_permissions(manage_channels=True)
    @is_staff()
    async def unlock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(
            interaction.guild.default_role, send_messages=None
        )
        await interaction.response.send_message(
            embed=discord.Embed(
                description="🔓 Channel unlocked.",
                colour=SUCCESS_GREEN,
            )
        )
        await log_mod_action(
            interaction.guild, "Channel Unlocked", SUCCESS_GREEN,
            Channel=interaction.channel.mention, Moderator=interaction.user.mention,
        )

    # ── /slowmode ──────────────────────────────────────────────────────────────
    @app_commands.command(name="slowmode", description="Set slowmode on the current channel.")
    @app_commands.default_permissions(manage_channels=True)
    @is_staff()
    @app_commands.describe(seconds="Slowmode delay in seconds (0 = off, max 21600)")
    async def slowmode(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 0, 21600] = 5,
    ):
        await interaction.channel.edit(slowmode_delay=seconds)
        desc = (
            f"⏱️ Slowmode set to **{seconds}s** in {interaction.channel.mention}."
            if seconds > 0
            else f"⏱️ Slowmode **disabled** in {interaction.channel.mention}."
        )
        await interaction.response.send_message(
            embed=discord.Embed(description=desc, colour=WARNING_YELLOW)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
