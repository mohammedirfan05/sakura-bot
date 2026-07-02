"""
🌸 Sakura Bot — cogs/tickets/ticket_open.py
Persistent view containing the "Open Ticket" button posted in #create-ticket.
"""

import discord
from services.ticket_service import TicketService


class OpenTicketView(discord.ui.View):
    """A persistent view with a single Open Ticket button."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Index sprites you dont have",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:open"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.create_ticket_channel(interaction)
