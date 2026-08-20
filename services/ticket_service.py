"""
🌸 Sakura Bot — services/ticket_service.py
Business logic for the Sakura native ticket system, including Custom Games Winner tickets.
"""

import discord
import asyncio
import time
import logging
from typing import Optional

from core.config import (
    ROLE_IDS, CHANNEL_IDS, NEON_RED, SUCCESS_GREEN, INFO_BLUE, BASE_BLACK, GOLD, WARNING_YELLOW
)
from cogs.tickets.ticket_database import ticket_db

log = logging.getLogger(__name__)


class TicketService:
    """Service to handle ticket business logic cleanly."""

    @staticmethod
    async def is_staff(member: discord.Member) -> bool:
        """Check if user has permission to manage tickets."""
        allowed_roles = {
            ROLE_IDS.get("owner"),
            ROLE_IDS.get("co_owner"),
            ROLE_IDS.get("admin"),
            ROLE_IDS.get("moderator"),
            ROLE_IDS.get("volunteer")
        }
        member_role_ids = {role.id for role in member.roles}
        
        # Check hardcoded roles first
        if bool(allowed_roles & member_role_ids):
            return True
            
        # Check dynamic ticket roles
        dynamic_roles = set(await ticket_db.get_ticket_roles())
        return bool(dynamic_roles & member_role_ids)

    # ── Standard Ticket Creation (Sprite Index) ────────────────────────────────

    @staticmethod
    async def create_ticket_channel(
        interaction: discord.Interaction,
        fn_username: str = None,
        sprites_needed: str = None,
        extraction_method: str = None
    ):
        """
        Called when a user submits the Sprite Index form.
        Creates the private ticket channel and posts the management embed with form answers.
        """
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
            # Channel was deleted externally — clean up DB and let them reopen
            await ticket_db.update_status(existing["channel_id"], "CLOSED")

        # ── Build safe channel name ───────────────────────────────────────────
        safe_name = "".join(
            c for c in user.display_name.lower() if c.isalnum() or c == "-"
        ).strip("-")
        if not safe_name:
            safe_name = str(user.id)
        channel_name = f"ticket-{safe_name}"[:100]

        overwrites = await TicketService._build_overwrites(guild, user)

        # ── Create the channel ────────────────────────────────────────────────
        from core.config import CATEGORY_IDS
        category = guild.get_channel(CATEGORY_IDS.get("karma_court", 0))
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                topic=f"[SAKURA_MANAGED] Ticket opened by {user.name} ({user.id})",
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

        inserted = await ticket_db.create_ticket(channel.id, user.id, ticket_type="SPRITE")
        if not inserted:
            return await interaction.response.send_message(
                f"✅ Your ticket has been created: {channel.mention}", ephemeral=True
            )

        # ── Build the management embed ───────────────────────────────────────
        embed = discord.Embed(
            title="🌸 Ticket Management",
            description=(
                f"Welcome {user.mention}! 👋\n"
                "A member of staff will be with you shortly."
            ),
            color=BASE_BLACK
        )
        if fn_username:
            embed.add_field(name="🎮 Fortnite Username", value=fn_username, inline=False)
        if sprites_needed:
            embed.add_field(name="🎨 Sprites Needed", value=sprites_needed, inline=False)
        if extraction_method:
            embed.add_field(name="⚙️ Extraction Method", value=extraction_method, inline=False)
        embed.set_footer(text="Staff: use the buttons below to manage this ticket.")

        view = TicketView()
        msg = await channel.send(embed=embed, view=view)
        try:
            await msg.pin(reason="Sakura Ticket Management Pin")
        except discord.Forbidden:
            log.warning("Missing permission to pin in %s", channel.name)

        await TicketService.log_action(
            guild,
            title="🎟️ Ticket Opened",
            description=(
                f"**Ticket:** {channel.mention}\n"
                f"**Opened By:** {user.mention}\n"
                f"**Fortnite Username:** {fn_username or 'N/A'}\n"
                f"**Sprites Needed:** {sprites_needed or 'N/A'}\n"
                f"**Extraction:** {extraction_method or 'N/A'}"
            ),
            color=SUCCESS_GREEN
        )

        await interaction.response.send_message(
            f"✅ Your ticket has been created: {channel.mention}",
            ephemeral=True
        )

    # ── Custom Games Winner Ticket Creation ───────────────────────────────────

    @staticmethod
    async def create_winner_ticket_channel(
        interaction: discord.Interaction,
        epic_name: str,
        discord_username: str,
        game_mode: str,
        date_won: str,
        proof_url: Optional[str] = None
    ):
        """
        Called when a user submits the Winner Claim form.
        Creates a private winner ticket channel with staff verification checklists.
        """
        from cogs.tickets.ticket_buttons import WinnerTicketView

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
            await ticket_db.update_status(existing["channel_id"], "CLOSED")

        safe_name = "".join(
            c for c in user.display_name.lower() if c.isalnum() or c == "-"
        ).strip("-")
        if not safe_name:
            safe_name = str(user.id)
        channel_name = f"winner-{safe_name}"[:100]

        overwrites = await TicketService._build_overwrites(guild, user)

        from core.config import CATEGORY_IDS
        category = guild.get_channel(CATEGORY_IDS.get("karma_court", 0))
        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=category,
                topic=f"[SAKURA_MANAGED] Winner Claim ticket opened by {user.name} ({user.id})",
                reason=f"Winner Ticket opened by {user.name}"
            )
        except discord.Forbidden:
            return await interaction.response.send_message(
                "❌ I don't have permission to create channels. Please contact staff.",
                ephemeral=True
            )
        except discord.HTTPException as e:
            log.error("Failed to create winner ticket channel: %s", e)
            return await interaction.response.send_message(
                "❌ Failed to create winner ticket. Please try again.",
                ephemeral=True
            )

        inserted = await ticket_db.create_ticket(
            channel_id=channel.id,
            creator_id=user.id,
            ticket_type="WINNER",
            epic_name=epic_name,
            discord_username=discord_username,
            game_mode=game_mode,
            date_won=date_won,
            proof_url=proof_url
        )
        if not inserted:
            return await interaction.response.send_message(
                f"✅ Your ticket has been created: {channel.mention}", ephemeral=True
            )

        # Build & post pinned winner embed
        ticket = await ticket_db.get_ticket(channel.id)
        embed = TicketService._build_winner_embed(user, ticket)

        view = WinnerTicketView()
        msg = await channel.send(embed=embed, view=view)
        try:
            await msg.pin(reason="Sakura Winner Management Pin")
        except discord.Forbidden:
            pass

        await TicketService.log_action(
            guild,
            title="🏆 Winner Claim Ticket Opened",
            description=(
                f"**Ticket:** {channel.mention}\n"
                f"**Opened By:** {user.mention}\n"
                f"**Epic Games Name:** {epic_name}\n"
                f"**Discord Username:** {discord_username}\n"
                f"**Game Mode Won:** {game_mode}\n"
                f"**Date Won:** {date_won}"
            ),
            color=GOLD
        )

        await interaction.response.send_message(
            f"✅ Your Winner Claim ticket has been created: {channel.mention}",
            ephemeral=True
        )

    # ── Permission Helper ──────────────────────────────────────────────────────

    @staticmethod
    async def _build_overwrites(guild: discord.Guild, user: discord.User) -> dict:
        overwrites: dict = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                attach_files=True,
                read_message_history=True
            ),
        }

        staff_keys = [
            "owner", "co_owner", "developer", "head_admin", "admin",
            "moderator", "trial_moderator", "volunteer"
        ]
        staff_roles = []
        for key in staff_keys:
            r = guild.get_role(ROLE_IDS.get(key, 0))
            if r: staff_roles.append(r)
            
        dynamic_role_ids = await ticket_db.get_ticket_roles()
        for r_id in dynamic_role_ids:
            r = guild.get_role(r_id)
            if r and r not in staff_roles:
                staff_roles.append(r)

        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_messages=True,
                manage_channels=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            )

        bot_member = guild.get_member(guild.me.id if guild.me else 0)
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
        return overwrites

    # ── Embed Helper for Winner Ticket ────────────────────────────────────────

    @staticmethod
    def _build_winner_embed(creator: discord.User, ticket: dict) -> discord.Embed:
        status = ticket.get("winner_status") or "🟡 Waiting for Verification"
        
        embed = discord.Embed(
            title="🏆 Custom Games Winner Ticket",
            description=(
                f"Welcome {creator.mention}! 🎉 Congratulations on your Victory Royale!\n"
                "Our staff team will verify your win details below before issuing your prize."
            ),
            color=GOLD
        )

        # Winner Information
        info_lines = [
            f"• **Epic Games Name:** `{ticket.get('epic_name', 'N/A')}`",
            f"• **Discord Username:** `{ticket.get('discord_username', 'N/A')}`",
            f"• **Game Mode Won:** `{ticket.get('game_mode', 'N/A')}`",
            f"• **Date Won:** `{ticket.get('date_won', 'N/A')}`",
        ]
        if ticket.get("proof_url"):
            info_lines.append(f"• **Proof Link:** [Click to view proof]({ticket.get('proof_url')})")
        else:
            info_lines.append("• **Proof:** Please upload your Victory Royale screenshot in this channel.")

        embed.add_field(name="📋 Winner Information", value="\n".join(info_lines), inline=False)

        # Staff Verification Checklist
        wc = "✅" if ticket.get("winner_confirmed") else "❌"
        rc = "✅" if ticket.get("rules_checked") else "❌"
        lc = "✅" if ticket.get("win_limit_checked") else "❌"
        pa = "✅" if ticket.get("prize_approved") else "❌"

        checklist_text = (
            f"{wc} **Winner confirmed**\n"
            f"{rc} **Rules checked** (no teaming, cheating, exploiting)\n"
            f"{lc} **Win limit checked**\n"
            f"{pa} **Prize approved**"
        )
        embed.add_field(name="🔍 Staff Verification", value=checklist_text, inline=False)

        # Prize Delivery
        ps = "✅" if ticket.get("prize_sent") else "❌"
        sent_by = f"<@{ticket['prize_sent_by']}>" if ticket.get("prize_sent_by") else "N/A"
        date_sent = f"<t:{ticket['prize_sent_at']}:f>" if ticket.get("prize_sent_at") else "N/A"

        prize_text = (
            f"• **V-Bucks / Prize Sent:** {ps}\n"
            f"• **Sent By:** {sent_by}\n"
            f"• **Date Sent:** {date_sent}"
        )
        embed.add_field(name="🎁 Prize Delivery", value=prize_text, inline=False)

        # Status field
        embed.add_field(name="🏷️ Ticket Status", value=f"**{status}**", inline=False)
        embed.set_footer(text="Staff: use the control buttons below to update checks & status.")
        return embed

    # ── Refresh Pinned Winner Embed ────────────────────────────────────────────

    @staticmethod
    async def refresh_winner_embed(channel: discord.TextChannel, ticket: dict):
        """Helper to find and update the pinned winner embed in the channel."""
        creator = channel.guild.get_member(ticket["creator_id"])
        if not creator:
            creator = await channel.guild.fetch_member(ticket["creator_id"])

        embed = TicketService._build_winner_embed(creator, ticket)

        # Find pinned message or last bot message
        try:
            pinned = await channel.pins()
            for msg in pinned:
                if msg.author == channel.guild.me and msg.embeds and "Custom Games Winner Ticket" in (msg.embeds[0].title or ""):
                    await msg.edit(embed=embed)
                    return
        except discord.HTTPException:
            pass

        # Fallback: search recent messages
        async for msg in channel.history(limit=20):
            if msg.author == channel.guild.me and msg.embeds and "Custom Games Winner Ticket" in (msg.embeds[0].title or ""):
                await msg.edit(embed=embed)
                return

    # ── Interactive Staff Actions for Winner Tickets ───────────────────────────

    @staticmethod
    async def open_verification_checklist(interaction: discord.Interaction):
        """Open ephemeral checklist toggle menu for staff."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to use staff verification actions.", ephemeral=True
            )
        from cogs.tickets.ticket_buttons import VerificationChecklistView
        await interaction.response.send_message(
            "Select a verification check to toggle state:",
            view=VerificationChecklistView(),
            ephemeral=True
        )

    @staticmethod
    async def toggle_verification(interaction: discord.Interaction, check_key: str):
        """Toggle verification check state and update embed."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ Permission denied.", ephemeral=True
            )

        ticket = await ticket_db.get_ticket(interaction.channel_id)
        if not ticket:
            return await interaction.response.send_message(
                "❌ Ticket record not found.", ephemeral=True
            )

        current_val = bool(ticket.get(check_key))
        new_val = not current_val
        await ticket_db.update_verification_check(interaction.channel_id, check_key, new_val)

        updated_ticket = await ticket_db.get_ticket(interaction.channel_id)
        await TicketService.refresh_winner_embed(interaction.channel, updated_ticket)

        field_labels = {
            "winner_confirmed": "Winner confirmed",
            "rules_checked": "Rules checked",
            "win_limit_checked": "Win limit checked",
            "prize_approved": "Prize approved"
        }
        label = field_labels.get(check_key, check_key)
        state_str = "✅ Checked" if new_val else "❌ Unchecked"

        await interaction.response.send_message(
            f"Updated **{label}** to **{state_str}**.", ephemeral=True
        )

        await TicketService.log_action(
            interaction.guild,
            title="🔍 Verification Check Updated",
            description=(
                f"**Ticket:** {interaction.channel.mention}\n"
                f"**Staff Member:** {interaction.user.mention}\n"
                f"**Check Item:** {label}\n"
                f"**New State:** {state_str}"
            ),
            color=INFO_BLUE
        )

    @staticmethod
    async def open_status_menu(interaction: discord.Interaction):
        """Open ephemeral status select menu for staff."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to update ticket status.", ephemeral=True
            )
        from cogs.tickets.ticket_buttons import StatusSelectView
        await interaction.response.send_message(
            "Select the new status for this winner claim ticket:",
            view=StatusSelectView(),
            ephemeral=True
        )

    @staticmethod
    async def set_winner_status(interaction: discord.Interaction, new_status: str):
        """Update ticket winner status and refresh embed & topic."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message("❌ Permission denied.", ephemeral=True)

        ticket = await ticket_db.get_ticket(interaction.channel_id)
        if not ticket:
            return await interaction.response.send_message("❌ Ticket record not found.", ephemeral=True)

        await ticket_db.update_winner_status(interaction.channel_id, new_status)
        updated_ticket = await ticket_db.get_ticket(interaction.channel_id)
        await TicketService.refresh_winner_embed(interaction.channel, updated_ticket)

        # Notify channel
        await interaction.channel.send(
            f"🏷️ Ticket status updated to **{new_status}** by {interaction.user.mention}."
        )

        await interaction.response.send_message(
            f"✅ Status updated to **{new_status}**.", ephemeral=True
        )

        await TicketService.log_action(
            interaction.guild,
            title="🏷️ Winner Ticket Status Changed",
            description=(
                f"**Ticket:** {interaction.channel.mention}\n"
                f"**Updated By:** {interaction.user.mention}\n"
                f"**New Status:** {new_status}"
            ),
            color=WARNING_YELLOW
        )

    @staticmethod
    async def mark_prize_sent(interaction: discord.Interaction):
        """Mark V-Bucks/Prize as sent for winner ticket and post to Hall of Fame."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message("❌ Permission denied.", ephemeral=True)

        ticket = await ticket_db.get_ticket(interaction.channel_id)
        if not ticket:
            return await interaction.response.send_message("❌ Ticket record not found.", ephemeral=True)

        await ticket_db.mark_prize_sent(interaction.channel_id, interaction.user.id)
        await ticket_db.update_winner_status(interaction.channel_id, "✅ Completed")

        updated_ticket = await ticket_db.get_ticket(interaction.channel_id)
        await TicketService.refresh_winner_embed(interaction.channel, updated_ticket)

        await interaction.channel.send(
            f"🎁 **Prize Delivered!** V-Bucks have been sent by {interaction.user.mention}. Congratulations! 🎉"
        )

        # Post permanent record to #hall-of-fame channel
        await TicketService.post_to_hall_of_fame(interaction.guild, updated_ticket, interaction.user)

        await interaction.response.send_message("✅ Marked prize as sent, posted to #hall-of-fame, and ticket set to Completed.", ephemeral=True)

        await TicketService.log_action(
            interaction.guild,
            title="🎁 Winner Prize Sent",
            description=(
                f"**Ticket:** {interaction.channel.mention}\n"
                f"**Sent By:** {interaction.user.mention}\n"
                f"**Winner:** <@{ticket['creator_id']}>"
            ),
            color=SUCCESS_GREEN
        )

    @staticmethod
    async def post_to_hall_of_fame(guild: discord.Guild, ticket: dict, staff_member: discord.User):
        """Post a permanent winner receipt record in the #hall-of-fame channel."""
        channel_id = CHANNEL_IDS.get("hall_of_fame")
        if not channel_id:
            return
        channel = guild.get_channel(channel_id)
        if not channel:
            return

        winner_id = ticket.get("creator_id")
        epic_name = ticket.get("epic_name", "N/A")
        discord_username = ticket.get("discord_username", "N/A")
        game_mode = ticket.get("game_mode", "N/A")
        date_won = ticket.get("date_won", "N/A")
        proof_url = ticket.get("proof_url")
        sent_at = ticket.get("prize_sent_at", int(time.time()))

        embed = discord.Embed(
            title="🏆 Custom Games — Winner Hall of Fame",
            description=f"🎉 Congratulations <@{winner_id}> on your Victory Royale!",
            color=GOLD,
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(name="👤 Winner", value=f"<@{winner_id}>\n(`{discord_username}`)", inline=True)
        embed.add_field(name="🎮 Epic Games Name", value=f"`{epic_name}`", inline=True)
        embed.add_field(name="🕹️ Game Mode Won", value=f"`{game_mode}`", inline=True)

        embed.add_field(name="📅 Date Won", value=f"`{date_won}`", inline=True)
        embed.add_field(name="🎁 Delivered By", value=staff_member.mention, inline=True)
        embed.add_field(name="🕒 Delivered At", value=f"<t:{sent_at}:f>", inline=True)

        if proof_url and proof_url.startswith("http"):
            embed.add_field(name="🖼️ Victory Proof", value=f"[Click to View Screenshot]({proof_url})", inline=False)
            embed.set_thumbnail(url=proof_url)

        embed.set_footer(text="🌸 Sakura Bot — Custom Games Prize Receipt")

        try:
            await channel.send(embed=embed)
        except Exception as e:
            log.warning("Failed to post to #hall-of-fame channel: %s", e)


    # ── Claim ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def claim_ticket(interaction: discord.Interaction, view: discord.ui.View):
        """Handle the Claim Ticket button."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to claim tickets.", ephemeral=True
            )

        ticket = await ticket_db.get_ticket(interaction.channel_id)
        if not ticket:
            return await interaction.response.send_message(
                "❌ Ticket not found in database.", ephemeral=True
            )

        if ticket["status"] == "CLAIMED":
            claimer_id = ticket["claimer_id"]
            return await interaction.response.send_message(
                f"❌ This ticket has already been claimed by <@{claimer_id}>.", ephemeral=True
            )

        success = await ticket_db.claim_ticket(interaction.channel_id, interaction.user.id)
        if not success:
            return await interaction.response.send_message(
                "❌ Failed to claim ticket (it might have just been claimed).", ephemeral=True
            )

        # Disable claim button
        for item in view.children:
            if getattr(item, "custom_id", None) == "ticket:claim":
                item.disabled = True
                item.label = f"✅ Claimed by {interaction.user.display_name}"
                item.style = discord.ButtonStyle.grey
                break

        await interaction.response.edit_message(view=view)

        new_name = f"claimed-{interaction.user.display_name.lower()}"
        try:
            await interaction.channel.edit(
                name=new_name, reason=f"Claimed by {interaction.user.name}"
            )
        except discord.Forbidden:
            log.warning("Missing permissions to rename channel %s", interaction.channel.name)
        except discord.HTTPException:
            log.warning("Rate limited when renaming %s", interaction.channel.name)

        if ticket.get("ticket_type") == "WINNER":
            greeting_text = (
                f"👋 Hi <@{ticket['creator_id']}>!\n\n"
                f"I'm {interaction.user.mention} and I'll be assisting you today.\n\n"
                "**Before we get started:**\n"
                "• Please ensure all details and screenshots are uploaded.\n"
                "• Staff will verify your win and deliver your prize shortly.\n"
                "• Tickets inactive for 24 hours may be closed.\n\n"
                "Please let me know when you're ready."
            )
        else:
            greeting_text = (
                f"👋 Hi <@{ticket['creator_id']}>!\n\n"
                f"I'm {interaction.user.mention} and I'll be assisting you today with your sprite request.\n\n"
                "**Before we get started:**\n"
                "• Please ensure your sprite details and preferences are clear.\n"
                "• Staff will assist you with your request shortly.\n"
                "• Tickets inactive for 24 hours may be closed.\n\n"
                "Please let me know when you're ready."
            )
        greeting_msg = await interaction.channel.send(greeting_text)
        try:
            await greeting_msg.pin(reason="Staff greeting pinned")
        except discord.Forbidden:
            pass

        await TicketService.log_action(
            interaction.guild,
            title="🎟️ Ticket Claimed",
            description=(
                f"**Ticket:** {interaction.channel.mention}\n"
                f"**Claimed By:** {interaction.user.mention}\n"
                f"**Opened By:** <@{ticket['creator_id']}>"
            ),
            color=SUCCESS_GREEN
        )

    # ── Rename ─────────────────────────────────────────────────────────────────

    @staticmethod
    async def open_rename_modal(interaction: discord.Interaction):
        """Open the Rename Modal for the Rename button."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to rename tickets.", ephemeral=True
            )
        from cogs.tickets.ticket_modal import RenameModal
        await interaction.response.send_modal(RenameModal())

    @staticmethod
    async def rename_ticket(interaction: discord.Interaction, new_name: str):
        """Handle the modal submission for renaming."""
        try:
            old_name = interaction.channel.name
            await interaction.channel.edit(
                name=new_name, reason=f"Renamed by {interaction.user.name}"
            )
            await interaction.response.send_message(
                f"✅ Ticket renamed to `{new_name}`.", ephemeral=True
            )
            await TicketService.log_action(
                interaction.guild,
                title="📝 Ticket Renamed",
                description=(
                    f"**Old Name:** #{old_name}\n"
                    f"**New Name:** {interaction.channel.mention}\n"
                    f"**Renamed By:** {interaction.user.mention}"
                ),
                color=INFO_BLUE
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Missing permissions to rename channel.", ephemeral=True
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Rate limited. Cannot rename right now.", ephemeral=True
            )

    # ── Close ──────────────────────────────────────────────────────────────────

    @staticmethod
    async def close_ticket(interaction: discord.Interaction, view: discord.ui.View):
        """Handle Close button — disables buttons, logs, then deletes the channel."""
        if not await TicketService.is_staff(interaction.user):
            return await interaction.response.send_message(
                "❌ You do not have permission to close tickets.", ephemeral=True
            )

        channel = interaction.channel

        await ticket_db.update_status(interaction.channel_id, "CLOSED")

        for item in view.children:
            item.disabled = True

        await interaction.response.edit_message(view=view)

        await channel.send(
            "🔒 **Ticket Closed** — This channel will be deleted in **5 seconds**.\n"
            f"Closed by {interaction.user.mention}."
        )

        await TicketService.log_action(
            interaction.guild,
            title="🔒 Ticket Closed",
            description=(
                f"**Ticket:** #{channel.name}\n"
                f"**Closed By:** {interaction.user.mention}"
            ),
            color=NEON_RED
        )

        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except discord.Forbidden:
            log.warning("Missing permissions to delete ticket channel #%s", channel.name)
            await channel.send("❌ I don't have permission to delete this channel. Please delete it manually.")
        except discord.HTTPException as e:
            log.warning("Failed to delete ticket channel #%s: %s", channel.name, e)

    # ── Log Helper ─────────────────────────────────────────────────────────────

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
