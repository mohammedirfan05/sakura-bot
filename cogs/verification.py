"""
🌸 Sakura Bot — cogs/verification.py
Button-based member verification:
  - Posts a persistent "Verify" button embed to #verification on startup
  - Checks Discord account age (min 7 days) to block fresh alts
  - On success: assigns Verified + Member + Lost Soul roles
  - Logs join verification to #join_leave_logs
  - /setup-verification admin command to re-post the panel
"""

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import logging

from core.config import (
    CHANNEL_IDS, ROLE_IDS,
    VERIFY_MIN_ACCOUNT_AGE_DAYS,
    DEEP_CRIMSON, SUCCESS_GREEN, ERROR_RED, WARNING_YELLOW,
)
from utils.checks import is_admin

log = logging.getLogger(__name__)

VERIFIED_ROLES = [
    ROLE_IDS["verified"],
    ROLE_IDS["member"],
    ROLE_IDS["lost_soul"],
]


# ── Persistent verify button ───────────────────────────────────────────────────

class VerifyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.red,
            label="Verify 🩸",
            emoji=None,
            custom_id="sakura:verify_button",
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild  = interaction.guild

        # ── 1. Already verified? ──────────────────────────────────────────────
        verified_role = guild.get_role(ROLE_IDS["verified"])
        if verified_role and verified_role in member.roles:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="✅ You are already verified! Welcome back.",
                    colour=SUCCESS_GREEN,
                ),
                ephemeral=True,
            )
            return

        # ── 2. Account age check ──────────────────────────────────────────────
        now         = datetime.datetime.now(datetime.timezone.utc)
        account_age = (now - member.created_at).days

        if account_age < VERIFY_MIN_ACCOUNT_AGE_DAYS:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Verification Failed",
                    description=(
                        f"Your Discord account must be at least **{VERIFY_MIN_ACCOUNT_AGE_DAYS} days old** "
                        f"to verify here.\n\n"
                        f"Your account is **{account_age} day(s) old**.\n"
                        f"Please try again later or open a ticket if you believe this is an error."
                    ),
                    colour=ERROR_RED,
                ),
                ephemeral=True,
            )
            log.info(
                "Verification blocked for %s (account age: %d days)", member, account_age
            )
            return

        # ── 3. Assign roles ───────────────────────────────────────────────────
        roles_to_add: list[discord.Role] = []
        for role_id in VERIFIED_ROLES:
            role = guild.get_role(role_id)
            if role and role not in member.roles:
                roles_to_add.append(role)

        if not roles_to_add:
            # Roles exist but couldn't find any — likely a config mismatch
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "⚠️ Verification roles aren't configured yet. "
                        "Please contact a staff member."
                    ),
                    colour=WARNING_YELLOW,
                ),
                ephemeral=True,
            )
            return

        try:
            await member.add_roles(*roles_to_add, reason="Member verified via button")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=(
                        "❌ I don't have permission to assign roles. "
                        "Please contact staff."
                    ),
                    colour=ERROR_RED,
                ),
                ephemeral=True,
            )
            log.error("Missing Manage Roles permission when verifying %s", member)
            return
        except discord.HTTPException as exc:
            log.error("Failed to assign roles to %s: %s", member, exc)
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ Something went wrong. Please try again or contact staff.",
                    colour=ERROR_RED,
                ),
                ephemeral=True,
            )
            return

        # ── 4. Success response ───────────────────────────────────────────────
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Verified!",
                description=(
                    f"Welcome to **KARMA**, {member.mention}! 🖤\n\n"
                    f"You've been granted access to the server.\n"
                    f"Your journey begins as a **Lost Soul** — prove your worth.\n\n"
                    f"📜 Read <#{CHANNEL_IDS['rules']}> • "
                    f"🎭 Get roles in <#{CHANNEL_IDS['roles']}>"
                ),
                colour=SUCCESS_GREEN,
            ),
            ephemeral=True,
        )
        log.info("Verified: %s (account age: %d days)", member, account_age)

        # ── 5. Log to join_leave_logs ─────────────────────────────────────────
        log_ch = guild.get_channel(CHANNEL_IDS["join_leave_logs"])
        if log_ch:
            embed = discord.Embed(
                description=f"✅ {member.mention} **verified** and granted access.",
                colour=SUCCESS_GREEN,
                timestamp=now,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.add_field(name="Account Age", value=f"{account_age} days", inline=True)
            embed.set_footer(text=f"ID: {member.id}")
            await log_ch.send(embed=embed)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VerifyButton())


# ── Cog ───────────────────────────────────────────────────────────────────────

class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._panel_posted = False
        bot.add_view(VerifyView())   # Re-register persistent view so it survives restarts

    @commands.Cog.listener()
    async def on_ready(self):
        """Post the verification panel on startup if it's not already there."""
        if self._panel_posted:
            return
        self._panel_posted = True

        channel = self.bot.get_channel(CHANNEL_IDS["verification"])
        if not channel:
            log.warning("Verification channel (ID %d) not found.", CHANNEL_IDS["verification"])
            return

        # Check if panel already exists in recent history
        async for message in channel.history(limit=20):
            if message.author == self.bot.user and message.components:
                log.info("Verification panel already exists in #%s — skipping.", channel.name)
                return

        await self._post_panel(channel)

    async def _post_panel(self, channel: discord.TextChannel):
        embed = discord.Embed(
            title="🩸 Enter THE GATE",
            description=(
                "To gain access to KARMA, you must verify yourself.\n\n"
                "**Requirements:**\n"
                f"▸ Discord account at least **{VERIFY_MIN_ACCOUNT_AGE_DAYS} days old**\n"
                "▸ Agree to follow the server rules\n\n"
                "Click the button below when you're ready.\n"
                "*Verification is instant and private.*"
            ),
            colour=DEEP_CRIMSON,
        )
        embed.set_footer(text="🌸 Sakura Verification System")
        await channel.send(embed=embed, view=VerifyView())
        log.info("Posted verification panel to #%s", channel.name)

    # ── /setup-verification ────────────────────────────────────────────────────
    @app_commands.command(
        name="setup-verification",
        description="[Admin] Re-post the verification panel to #verification.",
    )
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    async def setup_verification(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(CHANNEL_IDS["verification"])
        if not channel:
            await interaction.response.send_message(
                "❌ Verification channel not found. Check `CHANNEL_IDS['verification']` in config.",
                ephemeral=True,
            )
            return
        await self._post_panel(channel)
        await interaction.response.send_message(
            "✅ Verification panel posted!", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
