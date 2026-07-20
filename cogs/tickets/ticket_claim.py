"""
🌸 Sakura Bot — cogs/tickets/ticket_claim.py
Main cog for Sakura's native ticket system.
Registers persistent views and exposes /ticket-panel for staff to deploy the open-ticket panel.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging

from core.config import ROLE_IDS, CHANNEL_IDS, BASE_BLACK, DEEP_CRIMSON
from cogs.tickets.ticket_database import ticket_db
from cogs.tickets.ticket_buttons import TicketView
from cogs.tickets.ticket_open import OpenTicketView

log = logging.getLogger(__name__)


def is_staff():
    """App command check: only owner/co_owner/admin/moderator can run staff commands."""
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = {
            ROLE_IDS.get("owner"),
            ROLE_IDS.get("co_owner"),
            ROLE_IDS.get("admin"),
            ROLE_IDS.get("moderator"),
        }
        member_role_ids = {r.id for r in interaction.user.roles}
        return bool(allowed & member_role_ids)
    return app_commands.check(predicate)


# ── Ticket Role Group ──────────────────────────────────────────────────────────
# Defined outside the Cog class so @ticket_role.command() works correctly.
ticket_role = app_commands.Group(
    name="ticket-role",
    description="Manage which roles can view and manage tickets (Staff only)"
)


@ticket_role.command(name="add", description="Grant a role access to view and manage tickets")
@is_staff()
async def ticket_role_add(interaction: discord.Interaction, role: discord.Role):
    """Whitelists a new role for ticket management."""
    success = await ticket_db.add_ticket_role(role.id, interaction.user.id)
    if success:
        await interaction.response.send_message(
            f"✅ **{role.name}** can now view and manage tickets.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"ℹ️ **{role.name}** is already authorized to manage tickets.", ephemeral=True
        )


@ticket_role.command(name="remove", description="Revoke a role's access to ticket management")
@is_staff()
async def ticket_role_remove(interaction: discord.Interaction, role: discord.Role):
    """Removes a role from the ticket management whitelist."""
    success = await ticket_db.remove_ticket_role(role.id)
    if success:
        await interaction.response.send_message(
            f"✅ **{role.name}** has been removed from ticket management.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"ℹ️ **{role.name}** was not in the ticket management list.", ephemeral=True
        )


class TicketClaim(commands.Cog):
    """Main cog for the Sakura Ticket System."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        """Initialise DB and register all persistent ticket views."""
        await ticket_db.init()
        # Register persistent views so buttons survive bot restarts
        self.bot.add_view(TicketView())
        self.bot.add_view(OpenTicketView())
        log.info("Ticket system initialised — persistent views registered.")

    # ── /ticket-panel ──────────────────────────────────────────────────────────
    @app_commands.command(
        name="ticket-panel",
        description="Post the permanent Sakura ticket panel in #create-ticket. (Staff only)"
    )
    @is_staff()
    async def ticket_panel(self, interaction: discord.Interaction):
        """Posts the Open Ticket embed permanently in #create-ticket."""
        target_channel = interaction.guild.get_channel(CHANNEL_IDS["create_ticket"])
        if not target_channel:
            return await interaction.response.send_message(
                "❌ Could not find the #create-ticket channel. Check the channel ID in config.py.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🎟 Karma Court — Support Tickets",
            description=(
                "Need help from staff? Open a private ticket below.\n\n"
                "**📌 Before you open a ticket:**\n"
                "• Maximum **4 sprite requests** per ticket\n"
                "• Return borrowed sprites after indexing\n"
                "• Confirmed scams result in a **permanent ban**\n"
                "• Tickets inactive for **24 hours** may be closed\n\n"
                "**🩸 What to include in your ticket:**\n"
                "• A clear description of your issue\n"
                "• Any relevant screenshots or evidence\n"
                "• Your in-game name (if applicable)\n\n"
                "*Click the button below to open a private ticket with staff.*"
            ),
            color=DEEP_CRIMSON
        )
        embed.set_footer(text="🌸 Sakura — Karma Server Support System")

        view = OpenTicketView()
        await target_channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f"✅ Permanent ticket panel posted in {target_channel.mention}.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    cog = TicketClaim(bot)
    await bot.add_cog(cog)
    # Manually add the standalone group to the bot's command tree
    bot.tree.add_command(ticket_role)
