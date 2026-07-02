import discord
from services.ticket_service import TicketService

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟 Claim Ticket", style=discord.ButtonStyle.green, custom_id="ticket:claim")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.claim_ticket(interaction, self)

    @discord.ui.button(label="📝 Rename", style=discord.ButtonStyle.secondary, custom_id="ticket:rename")
    async def rename_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.open_rename_modal(interaction)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.close_ticket(interaction, self)
