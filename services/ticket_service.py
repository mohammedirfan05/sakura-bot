import discord
import time
import logging
from core.config import ROLE_IDS, CHANNEL_IDS, NEON_RED, SUCCESS_GREEN, INFO_BLUE, BASE_BLACK
from cogs.tickets.ticket_database import ticket_db

log = logging.getLogger(__name__)

class TicketService:
    """Service to handle ticket business logic cleanly."""

    @staticmethod
    def is_staff(member: discord.Member) -> bool:
        """Check if user has permission to manage tickets."""
        # Using .get in case volunteer doesn't exist yet in config
        allowed_roles = {
            ROLE_IDS.get("owner"),
            ROLE_IDS.get("co_owner"),
            ROLE_IDS.get("admin"),
            ROLE_IDS.get("moderator"),
            ROLE_IDS.get("volunteer")
        }
        member_role_ids = {role.id for role in member.roles}
        return bool(allowed_roles & member_role_ids)

    @staticmethod
    async def handle_new_ticket(channel: discord.TextChannel):
        """Called when a new ticket channel is created."""
        from cogs.tickets.ticket_buttons import TicketView

        # We assume Ticket Tool sets the channel topic to the creator ID, or we fetch from DB/audit logs.
        # But wait, without reading audit logs, how do we know the creator?
        # A common way is the first message ping, or we just store `None` if unknown.
        # For now, we'll store 0 as creator if we can't figure it out immediately.
        creator_id = 0
        
        # 1. Register in DB
        await ticket_db.create_ticket(channel.id, creator_id)

        # 2. Send Sakura embed
        embed = discord.Embed(
            title="🌸 Ticket Management",
            description="Staff: Use the buttons below to manage this ticket.",
            color=BASE_BLACK
        )
        view = TicketView()
        
        msg = await channel.send(embed=embed, view=view)
        
        # 3. Pin the Sakura message
        try:
            await msg.pin(reason="Sakura Ticket Management Pin")
        except discord.Forbidden:
            log.warning(f"Missing permissions to pin message in {channel.name}")

    @staticmethod
    async def claim_ticket(interaction: discord.Interaction, view: discord.ui.View):
        """Handle the Claim Ticket button."""
        if not TicketService.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You do not have permission to claim tickets.", ephemeral=True)
            
        ticket = await ticket_db.get_ticket(interaction.channel_id)
        if not ticket:
            return await interaction.response.send_message("❌ Ticket not found in database.", ephemeral=True)
            
        if ticket["status"] == "CLAIMED":
            claimer_id = ticket["claimer_id"]
            return await interaction.response.send_message(f"❌ This ticket has already been claimed by <@{claimer_id}>.", ephemeral=True)
            
        # Update DB
        success = await ticket_db.claim_ticket(interaction.channel_id, interaction.user.id)
        if not success:
            return await interaction.response.send_message("❌ Failed to claim ticket (it might have just been claimed).", ephemeral=True)
            
        # Disable claim button and update text
        for item in view.children:
            if getattr(item, "custom_id", None) == "ticket:claim":
                item.disabled = True
                item.label = f"✅ Claimed by {interaction.user.display_name}"
                item.style = discord.ButtonStyle.grey
                break
                
        await interaction.response.edit_message(view=view)
        
        # Rename channel
        new_name = f"claimed-{interaction.user.display_name.lower()}"
        try:
            await interaction.channel.edit(name=new_name, reason=f"Claimed by {interaction.user.name}")
        except discord.Forbidden:
            log.warning(f"Missing permissions to rename channel {interaction.channel.name}")
        except discord.HTTPException:
            log.warning(f"Rate limited or other HTTP error when renaming {interaction.channel.name}")

        # Send greeting and pin it
        greeting_text = (
            f"👋 Hi <@{ticket['creator_id'] if ticket['creator_id'] != 0 else 'User'}>!\n\n"
            f"I'm {interaction.user.mention} and I'll be assisting you today.\n\n"
            "**Before we get started:**\n"
            "• Maximum of 4 sprite requests per ticket.\n"
            "• Return borrowed sprites after indexing.\n"
            "• Confirmed scams result in a permanent ban.\n"
            "• Tickets inactive for 24 hours may be closed.\n\n"
            "Please let me know when you're ready."
        )
        greeting_msg = await interaction.channel.send(greeting_text)
        try:
            await greeting_msg.pin(reason="Staff greeting pinned")
        except discord.Forbidden:
            pass

        # Send Log
        await TicketService.log_action(
            interaction.guild,
            title="🎟️ Ticket Claimed",
            description=f"**Ticket:** {interaction.channel.mention}\n**Claimed By:** {interaction.user.mention}\n**Opened By:** <@{ticket['creator_id']}>",
            color=SUCCESS_GREEN
        )

    @staticmethod
    async def open_rename_modal(interaction: discord.Interaction):
        """Open the Rename Modal for the Rename button."""
        if not TicketService.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You do not have permission to rename tickets.", ephemeral=True)
            
        from cogs.tickets.ticket_modal import RenameModal
        await interaction.response.send_modal(RenameModal())

    @staticmethod
    async def rename_ticket(interaction: discord.Interaction, new_name: str):
        """Handle the modal submission for renaming."""
        try:
            old_name = interaction.channel.name
            await interaction.channel.edit(name=new_name, reason=f"Renamed by {interaction.user.name}")
            await interaction.response.send_message(f"✅ Ticket renamed to `{new_name}`.", ephemeral=True)
            
            await TicketService.log_action(
                interaction.guild,
                title="📝 Ticket Renamed",
                description=f"**Old Name:** #{old_name}\n**New Name:** {interaction.channel.mention}\n**Renamed By:** {interaction.user.mention}",
                color=INFO_BLUE
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ Missing permissions to rename channel.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("❌ Rate limited. Cannot rename right now.", ephemeral=True)

    @staticmethod
    async def close_ticket(interaction: discord.Interaction, view: discord.ui.View):
        """Handle Close button."""
        if not TicketService.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You do not have permission to close tickets.", ephemeral=True)

        await ticket_db.update_status(interaction.channel_id, "CLOSED")
        
        # Remove all member overwrites so users can't text anymore
        for target, overwrite in interaction.channel.overwrites.items():
            if isinstance(target, discord.Member):
                try:
                    await interaction.channel.set_permissions(target, overwrite=None, reason="Ticket closed")
                except discord.Forbidden:
                    pass
        
        # Disable all buttons
        for item in view.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=view)
        await interaction.channel.send("🔒 This ticket has been marked as closed in Sakura's system. The user has been removed.")

        await TicketService.log_action(
            interaction.guild,
            title="🔒 Ticket Closed",
            description=f"**Ticket:** #{interaction.channel.name}\n**Closed By:** {interaction.user.mention}",
            color=NEON_RED
        )

    @staticmethod
    async def log_action(guild: discord.Guild, title: str, description: str, color: int):
        """Helper to send logs to the ticket-logs channel."""
        log_channel_id = CHANNEL_IDS.get("ticket_logs")
        if not log_channel_id:
            return
            
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=discord.utils.utcnow()
            )
            await log_channel.send(embed=embed)
