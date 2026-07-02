"""
🌸 Sakura Bot — cogs/security.py
Anti-Nuke / Anti-Abuse security layer.
Ensures that only authorized users (Owner, Co-Owner) can assign critical roles.
If a rogue mod tries to allocate critical roles, Sakura will strip their roles and quarantine them.
"""

import discord
from discord.ext import commands
import asyncio
import logging
from typing import Set

from core.config import (
    ROLE_IDS,
    CHANNEL_IDS,
    CRITICAL_ROLE_IDS,
    AUTHORIZED_ASSIGNER_IDS,
    ERROR_RED
)

log = logging.getLogger(__name__)


class Security(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Monitor role changes to prevent unauthorized assignment of critical roles."""
        
        # Only care about role additions
        new_roles = set(after.roles) - set(before.roles)
        if not new_roles:
            return

        # Check if any of the new roles are critical
        critical_added = [role for role in new_roles if role.id in CRITICAL_ROLE_IDS]
        if not critical_added:
            return

        # Wait briefly to ensure Discord's audit log has populated
        await asyncio.sleep(2)

        # Fetch recent audit logs for member role updates
        try:
            # Look at recent role updates for this specific target user
            audit_logs = [
                entry async for entry in after.guild.audit_logs(
                    action=discord.AuditLogAction.member_role_update,
                    limit=10
                )
            ]
        except discord.Forbidden:
            log.warning("Security Cog: Missing View Audit Log permissions!")
            return

        actor = None
        for entry in audit_logs:
            # If the target of the audit log is the user who just got the role
            if entry.target.id == after.id:
                # Check if the critical role was added in this exact entry
                # entry.after.roles contains roles that were added or modified
                if hasattr(entry.after, 'roles'):
                    added_role_ids = [r.id for r in entry.after.roles]
                    if any(cr.id in added_role_ids for cr in critical_added):
                        actor = entry.user
                        break
        
        if not actor:
            log.warning(f"Security Cog: Could not find audit log entry for role addition on {after}.")
            return

        # If Sakura bot did it herself (or another bot maybe, but definitely ignore Sakura)
        if actor.id == self.bot.user.id:
            return
            
        # Check if actor has authorization
        if isinstance(actor, discord.Member):
            actor_role_ids = {r.id for r in actor.roles}
            # If actor has Owner or Co-Owner role, they are allowed.
            if any(auth_id in actor_role_ids for auth_id in AUTHORIZED_ASSIGNER_IDS):
                log.info(f"Security Cog: Authorized role assignment by {actor}.")
                return
        else:
            # If actor is not a Member (e.g. they left, or it's a webhook/system), we skip
            return

        # ==========================================
        # ROGUE MODERATOR DETECTED
        # ==========================================
        log.warning(f"🚨 ANTI-NUKE TRIGGERED: {actor} assigned critical roles {critical_added} to {after} without authorization!")

        try:
            # 1. Strip ALL roles from the rogue actor (except @everyone and premium/integration roles)
            removable_roles = [r for r in actor.roles if r != after.guild.default_role and not r.is_integration() and not r.is_premium_subscriber()]
            if removable_roles:
                await actor.remove_roles(*removable_roles, reason="Sakura Security: Unauthorized critical role assignment (Anti-Nuke).")
            
            # 2. Add Quarantined Role
            quarantine_role = after.guild.get_role(ROLE_IDS.get("quarantined"))
            if quarantine_role:
                await actor.add_roles(quarantine_role, reason="Sakura Security: Rogue staff quarantine.")
                
            # 3. Undo the critical role assignment on the target
            await after.remove_roles(*critical_added, reason="Sakura Security: Reverting unauthorized role assignment.")
            
        except discord.Forbidden:
            log.error("Security Cog: Missing permissions to modify roles during an Anti-Nuke trigger!")
            
        # 4. Send Alerts
        alert_msg = (
            f"🚨 **ANTI-NUKE ALERT** 🚨\n\n"
            f"**Rogue Action Detected:**\n"
            f"User {actor.mention} (`{actor.id}`) attempted to assign critical roles to {after.mention} (`{after.id}`).\n\n"
            f"**Action Taken:**\n"
            f"• All roles stripped from {actor.mention}.\n"
            f"• {actor.mention} has been Quarantined.\n"
            f"• Critical roles removed from {after.mention} to revert the action."
        )
        
        # Notify Mod Logs
        mod_log_channel = after.guild.get_channel(CHANNEL_IDS.get("mod_logs"))
        if mod_log_channel:
            embed = discord.Embed(
                title="🚨 Sakura Security: Anti-Nuke Triggered 🚨",
                description=alert_msg,
                color=ERROR_RED,
                timestamp=discord.utils.utcnow()
            )
            await mod_log_channel.send(embed=embed)
            
        # Notify Staff Chat to ping Owners
        staff_chat = after.guild.get_channel(CHANNEL_IDS.get("staff_chat"))
        if staff_chat:
            await staff_chat.send(alert_msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(Security(bot))
