"""
🌸 Sakura Bot — utils/checks.py
Shared permission check decorators for slash commands.
Import these instead of duplicating is_staff() per-cog.
"""

import discord
from discord import app_commands
from core.config import STAFF_ROLE_IDS, ROLE_IDS


def is_staff():
    """Check: interaction user has at least one staff role."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return any(r.id in STAFF_ROLE_IDS for r in interaction.user.roles)
    return app_commands.check(predicate)


def is_admin():
    """Check: interaction user is Admin or above."""
    admin_ids = {
        ROLE_IDS["owner"],
        ROLE_IDS["co_owner"],
        ROLE_IDS["head_admin"],
        ROLE_IDS["admin"],
    }
    async def predicate(interaction: discord.Interaction) -> bool:
        return any(r.id in admin_ids for r in interaction.user.roles)
    return app_commands.check(predicate)


def is_owner():
    """Check: interaction user is the Owner."""
    async def predicate(interaction: discord.Interaction) -> bool:
        return any(r.id == ROLE_IDS["owner"] for r in interaction.user.roles)
    return app_commands.check(predicate)
