"""
🌸 Sakura Bot — cogs/tickets/ticket_open.py
Persistent view containing the "Index sprites you dont have" button posted in #create-ticket.
Clicking it opens the Sprite Index form modal before creating the ticket channel.
"""

import discord
from cogs.tickets.ticket_modal import SpriteIndexModal, WinnerClaimModal


class OpenTicketView(discord.ui.View):
    """A persistent view with buttons for opening tickets."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎟 Index Sprites",
        style=discord.ButtonStyle.danger,
        custom_id="ticket:open"
    )
    async def open_sprite_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SpriteIndexModal())

    @discord.ui.button(
        label="🏆 Winner Claim",
        style=discord.ButtonStyle.success,
        custom_id="ticket:open_winner"
    )
    async def open_winner_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(WinnerClaimModal())

