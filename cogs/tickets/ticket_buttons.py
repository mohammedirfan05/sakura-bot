import discord
from services.ticket_service import TicketService


class TicketView(discord.ui.View):
    """Persistent view for standard sprite index tickets."""
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


class WinnerTicketView(discord.ui.View):
    """Persistent view for Custom Games Winner tickets."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟 Claim Ticket", style=discord.ButtonStyle.green, custom_id="ticket:claim")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.claim_ticket(interaction, self)

    @discord.ui.button(label="✅ Staff Checklist", style=discord.ButtonStyle.primary, custom_id="ticket:verify_menu")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.open_verification_checklist(interaction)

    @discord.ui.button(label="🏷️ Ticket Status", style=discord.ButtonStyle.secondary, custom_id="ticket:set_status")
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.open_status_menu(interaction)

    @discord.ui.button(label="🎁 Mark Prize Sent", style=discord.ButtonStyle.success, custom_id="ticket:mark_prize")
    async def mark_prize_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.mark_prize_sent(interaction)

    @discord.ui.button(label="📝 Rename", style=discord.ButtonStyle.secondary, custom_id="ticket:rename")
    async def rename_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.open_rename_modal(interaction)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await TicketService.close_ticket(interaction, self)


class VerificationChecklistSelect(discord.ui.Select):
    """Select menu for staff to toggle verification steps."""
    def __init__(self):
        options = [
            discord.SelectOption(label="Winner Confirmed", value="winner_confirmed", description="Toggle winner confirmation check", emoji="✅"),
            discord.SelectOption(label="Rules Checked", value="rules_checked", description="No teaming, cheating, or exploiting", emoji="⚖️"),
            discord.SelectOption(label="Win Limit Checked", value="win_limit_checked", description="Verify user win limits", emoji="📊"),
            discord.SelectOption(label="Prize Approved", value="prize_approved", description="Approve prize allocation", emoji="🎁"),
        ]
        super().__init__(placeholder="Select a checklist item to toggle...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await TicketService.toggle_verification(interaction, self.values[0])


class VerificationChecklistView(discord.ui.View):
    """Ephemeral container view for VerificationChecklistSelect."""
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(VerificationChecklistSelect())


class StatusSelect(discord.ui.Select):
    """Select menu for staff to update winner ticket status."""
    def __init__(self):
        options = [
            discord.SelectOption(label="Waiting for Verification", value="🟡 Waiting for Verification", description="Awaiting staff review", emoji="🟡"),
            discord.SelectOption(label="Under Review", value="🔵 Under Review", description="Staff actively inspecting win", emoji="🔵"),
            discord.SelectOption(label="Prize Ready", value="🟢 Prize Ready", description="Win verified, waiting for prize delivery", emoji="🟢"),
            discord.SelectOption(label="Completed", value="✅ Completed", description="Prize delivered and verified", emoji="✅"),
            discord.SelectOption(label="Denied", value="❌ Denied", description="Claim denied", emoji="❌"),
        ]
        super().__init__(placeholder="Select new ticket status...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await TicketService.set_winner_status(interaction, self.values[0])


class StatusSelectView(discord.ui.View):
    """Ephemeral container view for StatusSelect."""
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(StatusSelect())
