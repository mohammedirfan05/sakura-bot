"""
🌸 Sakura Bot — cogs/reaction_roles.py
Posts an interactive dropdown to #roles for members to
self-assign platform, region, and ping notification roles.
/setup-roles — Admin command to re-post the panel.
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging

from core.config import CHANNEL_IDS, ROLE_IDS, DEEP_CRIMSON
from utils.checks import is_admin

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Self-assignable role groups
#  Keys  → display label shown in dropdown
#  Values → role ID from ROLE_IDS (or None if not yet configured)
# ─────────────────────────────────────────────────────────────────────────────

# Removed PLATFORM_ROLES and PING_ROLES since they are not configured in the server.

REGION_ROLES: dict[str, int | None] = {
    "🌍 Europe":        1521497097679933661,
    "🌎 North America": 1521497098376187904,
    "🌎 South America": 1521497098883825734,
    "🌏 Asia":          1521497099403788511,
    "🦘 Oceania":       1521497100700094504,
    "🌍 Africa":        1521497101371183154,
}

# ── Generic toggle select ─────────────────────────────────────────────────────

class RoleToggleSelect(discord.ui.Select):
    """Generic select that toggles roles by label lookup in a provided dict."""

    def __init__(
        self,
        placeholder: str,
        custom_id: str,
        role_map: dict[str, int | None],
    ):
        self._role_map = role_map
        options = [discord.SelectOption(label=label, value=label) for label in role_map]
        super().__init__(
            placeholder=placeholder,
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=custom_id,
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        toggled: list[str] = []
        any_configured = False

        for label, role_id in self._role_map.items():
            if role_id is None:
                continue
            any_configured = True
            role = guild.get_role(role_id)
            if not role:
                continue
            if label in self.values:
                if role not in interaction.user.roles:
                    await interaction.user.add_roles(role)
                    toggled.append(f"+ {label}")
            else:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    toggled.append(f"- {label}")

        if not any_configured:
            await interaction.response.send_message(
                "ℹ️ These roles haven't been configured by staff yet.", ephemeral=True
            )
            return

        if toggled:
            diff = "\n".join(toggled)
            await interaction.response.send_message(
                f"✅ Roles updated:\n```diff\n{diff}\n```", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "ℹ️ No changes made — deselect a role to remove it.", ephemeral=True
            )


class RolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleToggleSelect(
            placeholder="🌍 Choose your region…",
            custom_id="sakura:region_select",
            role_map=REGION_ROLES,
        ))


class ReactionRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._panel_posted = False
        bot.add_view(RolesView())   # Re-register persistent view on restart

    @commands.Cog.listener()
    async def on_ready(self):
        """Post the roles panel on startup if it's not already there."""
        if self._panel_posted:
            return
        self._panel_posted = True
        channel = self.bot.get_channel(CHANNEL_IDS["roles"])
        if not channel:
            log.warning("Roles channel not found.")
            return
        # Check if the panel already exists in recent history
        async for message in channel.history(limit=20):
            if message.author == self.bot.user and message.components:
                log.info("Roles panel already exists — skipping post.")
                return
        await self._post_roles_panel(channel)

    async def _post_roles_panel(self, channel: discord.TextChannel):
        embed = discord.Embed(
            title="🎭 Self-Assignable Roles",
            description=(
                "Use the dropdowns below to choose roles that match your preferences.\n\n"
                "**🌍 Region Roles** — Show your timezone/region.\n\n"
                "*Selecting/deselecting a dropdown option will toggle the role instantly.*"
            ),
            colour=DEEP_CRIMSON,
        )
        embed.set_footer(text="🌸 Sakura Role Selection • Changes are instant & private")
        await channel.send(embed=embed, view=RolesView())
        log.info("Posted roles panel to #%s", channel.name)

    @app_commands.command(name="setup-roles", description="[Admin] Re-post the self-role panel.")
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    async def setup_roles(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(CHANNEL_IDS["roles"])
        if not channel:
            await interaction.response.send_message("❌ Roles channel not found.", ephemeral=True)
            return
        await self._post_roles_panel(channel)
        await interaction.response.send_message("✅ Roles panel posted!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
