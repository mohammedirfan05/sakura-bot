"""
🌸 Sakura Bot — cogs/tickets/ticket_modal.py
Modals used by the ticket system.
"""

import discord
from services.ticket_service import TicketService


class SpriteIndexModal(discord.ui.Modal, title="🎟 Sprite Index"):
    """Form shown when a user clicks the Open Ticket button."""

    fn_username = discord.ui.TextInput(
        label="What is your Fortnite Username?",
        placeholder="Example: Darling-KFC",
        min_length=1,
        max_length=100,
        required=True,
        style=discord.TextStyle.short
    )

    sprites_needed = discord.ui.TextInput(
        label="Which sprite do you need indexed?",
        placeholder="4 sprites max",
        min_length=1,
        max_length=300,
        required=True,
        style=discord.TextStyle.paragraph
    )

    extraction_method = discord.ui.TextInput(
        label="How are you extracting?",
        placeholder="portable or normal",
        min_length=1,
        max_length=100,
        required=True,
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        await TicketService.create_ticket_channel(
            interaction,
            fn_username=self.fn_username.value,
            sprites_needed=self.sprites_needed.value,
            extraction_method=self.extraction_method.value
        )


class RenameModal(discord.ui.Modal, title="Rename Ticket"):
    new_name = discord.ui.TextInput(
        label="Enter new ticket name",
        placeholder="e.g. sprite-irfan or claimed-username",
        min_length=1,
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await TicketService.rename_ticket(interaction, self.new_name.value)
