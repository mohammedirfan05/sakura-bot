import discord
import asyncio
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
    async def create_ticket_channel(interaction: discord.Interaction):
        """Called when a user clicks 'Open Ticket'. Creates the private channel."""
        from cogs.tickets.ticket_buttons import TicketView

        guild = interaction.guild
        user = interaction.user

        # ── Duplicate check ──────────────────────────────────────────────────
        existing = await ticket_db.get_open_ticket_by_user(user.id)
        if existing:
            existing_channel = guild.get_channel(existing["channel_id"])
            if existing_channel:
                return await interaction.response.send_message(
                    f"❌ You already have an open ticket: {existing_channel.mention}\n"
                    "Please use that ticket or ask staff to close it first.",
                    ephemeral=True
                )
            # Channel was deleted externally — clean up DB and let them open a new one
            await ticket_db.update_status(existing["channel_id"], "CLOSED")

        # ── Build channel name (safe lowercase alphanumeric) ─────────────────
        safe_name = "".join(c for c in user.display_name.lower() if c.isalnum() or c == "-").strip("-")
        if not safe_name:
            safe_name = str(user.id)
        channel_name = f"ticket-{safe_name}"[:100]

        # ── Permission overwrites ─────────────────────────────────────────────
        overwrites: dict = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True
            ),
        }

        staff_keys = ["owner", "co_owner", "developer", "head_admin", "admin",
                      "moderator", "trial_moderator", "volunteer"]
        for key in staff_keys:
            role = guild.get_role(ROLE_IDS.get(key, 0))
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_messages=True,
                    manage_channels=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                )

        bot_member = guild.get_member(interaction.client.user.id)
        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                manage_channels=True,
                read_message_history=True,
                add_reactions=True,
                attach_files=True,
                embed_links=True,
                pin_messages=True,
            )

        # ── Create the channel ────────────────────────────────────────────────
        from core.config import CATEGORY_IDS
        category = guild.get_channel(CATEGORY_IDS.get("karma_court", 0))
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                topic=f"Ticket opened by {user.name} ({user.id})",
                reason=f"Ticket opened by {user.name}"
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I don't have permission to create channels. Please contact a staff member.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            log.error("Failed to create ticket channel: %s", e)
            return await interaction.response.send_message(
                "❌ Failed to create your ticket. Please try again.",
                ephemeral=True
            )

        # ── Register in DB ────────────────────────────────────────────────────
        await ticket_db.create_ticket(channel.id, user.id)

        # ── Send management embed inside the ticket ───────────────────────────
        embed = discord.Embed(
            title="🌸 Ticket Management",
            description=(
                f"Welcome {user.mention}! 👋\n\n"
                "A member of staff will be with you shortly.\n"
                "Please describe your issue below while you wait."
            ),
            color=BASE_BLACK
        )
        embed.set_footer(text="Staff: use the buttons below to manage this ticket.")
        view = TicketView()
        msg = await channel.send(embed=embed, view=view)
        try:
            await msg.pin(reason="Sakura Ticket Management Pin")
        except discord.Forbidden:
            log.warning("Missing permission to pin in %s", channel.name)

        # Ping the opener so they get a notification
        await channel.send(f"{user.mention} — your ticket is ready! Please state your issue.")

        # ── Log ───────────────────────────────────────────────────────────────
        await TicketService.log_action(
            guild,
            title="🎟️ Ticket Opened",
            description=f"**Ticket:** {channel.mention}\n**Opened By:** {user.mention}",
            color=SUCCESS_GREEN
        )

        # ── Acknowledge the interaction ───────────────────────────────────────
        await interaction.response.send_message(
            f"✅ Your ticket has been created: {channel.mention}",
            ephemeral=True
        )

    @staticmethod
    async def handle_new_ticket(channel: discord.TextChannel, creator_id: int):
        """Sends the Sakura management embed into an already-created ticket channel."""
        from cogs.tickets.ticket_buttons import TicketView

        await ticket_db.create_ticket(channel.id, creator_id)

        embed = discord.Embed(
            title="🌸 Ticket Management",
            description="Staff: Use the buttons below to manage this ticket.",
            color=BASE_BLACK
        )
        view = TicketView()
        msg = await channel.send(embed=embed, view=view)
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
        """Handle Close button — disables buttons, logs, then deletes the channel."""
        if not TicketService.is_staff(interaction.user):
            return await interaction.response.send_message("❌ You do not have permission to close tickets.", ephemeral=True)

        channel = interaction.channel

        # Mark as closed in DB
        await ticket_db.update_status(interaction.channel_id, "CLOSED")

        # Disable all buttons so nobody can click them again
        for item in view.children:
            item.disabled = True

        # Acknowledge the interaction and update the embed buttons
        await interaction.response.edit_message(view=view)

        # Send a visible closing notice (users can read it briefly before deletion)
        await channel.send(
            "🔒 **Ticket Closed** — This channel will be deleted in **5 seconds**.\n"
            f"Closed by {interaction.user.mention}."
        )

        # Log the closure BEFORE deleting the channel (so the mention still resolves)
        await TicketService.log_action(
            interaction.guild,
            title="🔒 Ticket Closed",
            description=f"**Ticket:** #{channel.name}\n**Closed By:** {interaction.user.mention}",
            color=NEON_RED
        )

        # Wait 5 seconds so everyone can see the closing message, then delete the channel
        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except discord.Forbidden:
            log.warning(f"Missing permissions to delete ticket channel #{channel.name}")
            await channel.send("❌ I don't have permission to delete this channel. Please delete it manually.")
        except discord.HTTPException as e:
            log.warning(f"Failed to delete ticket channel #{channel.name}: {e}")

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
