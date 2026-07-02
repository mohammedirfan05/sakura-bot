"""
🌸 Sakura Bot — cogs/tickets/ticket_open.py
Persistent view containing the "Index sprites you dont have" button posted in #create-ticket.
Clicking it opens the Sprite Index form modal before creating the ticket channel.
"""

import discord
from cogs.tickets.ticket_modal import SpriteIndexModal


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
        # Open the form — ticket channel is created only after user submits
        await interaction.response.send_modal(SpriteIndexModal())
