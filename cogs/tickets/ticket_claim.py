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
    """App command check: only owner/co_owner/admin can run /ticket-panel."""
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = {
            ROLE_IDS.get("owner"),
            ROLE_IDS.get("co_owner"),
            ROLE_IDS.get("admin"),
        }
        member_role_ids = {r.id for r in interaction.user.roles}
        return bool(allowed & member_role_ids)
    return app_commands.check(predicate)


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
        # Always post to #create-ticket regardless of where command is run
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
    await bot.add_cog(TicketClaim(bot))
