import discord
from services.ticket_service import TicketService

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
