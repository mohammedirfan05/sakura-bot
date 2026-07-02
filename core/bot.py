"""
🌸 Sakura Bot — core/bot.py
Custom bot subclass. Handles cog auto-discovery, database initialisation,
Python logging setup, and global error handling.
"""

import os
import logging
import discord
from discord.ext import commands
from core.database import init_db
from core.config import GUILD_ID

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sakura")

# Silence noisy discord.py gateway/http logs unless debugging
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)


class SakuraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents(
            guilds=True,
            members=True,
            messages=True,
            message_content=True,
            voice_states=True,
            moderation=True,
            reactions=True,
        )
        super().__init__(
            command_prefix="!sakura ",   # prefix reserved for owner debug commands only
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        """Called before the bot connects — initialise DB, load cogs, sync commands."""
        log.info("Initialising database...")
        await init_db()

        # Auto-discover and load all cogs from the cogs/ directory
        cogs_dir = os.path.join(os.path.dirname(__file__), "..", "cogs")
        cogs_loaded = 0
        for filename in sorted(os.listdir(cogs_dir)):
            if filename.endswith(".py") and not filename.startswith("_"):
                cog_name = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_name)
                    log.info("Loaded cog: %s", cog_name)
                    cogs_loaded += 1
                except Exception as exc:
                    log.error("Failed to load cog %s: %s", cog_name, exc, exc_info=True)

        # Load nested cogs (Tickets — loads TicketClaim which registers all persistent views)
        try:
            await self.load_extension("cogs.tickets.ticket_claim")
            log.info("Loaded cog: cogs.tickets.ticket_claim")
            cogs_loaded += 1
        except Exception as exc:
            log.error("Failed to load cog cogs.tickets.ticket_claim: %s", exc, exc_info=True)


        log.info("Loaded %d cogs", cogs_loaded)

        # Sync slash commands to guild immediately (no 1-hour global delay)
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        log.info("Synced %d slash commands to guild %d", len(synced), GUILD_ID)

    async def on_ready(self):
        log.info("─" * 50)
        log.info("🌸  Sakura Bot online: %s (ID: %s)", self.user, self.user.id)
        log.info("discord.py v%s", discord.__version__)
        log.info("─" * 50)
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="🩸 Karma judges all…",
            ),
        )

    async def on_error(self, event: str, *args, **kwargs):
        log.exception("Unhandled exception in event %s", event)

    async def on_tree_error(
        self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError
    ):
        """Global slash command error handler."""
        if isinstance(error, discord.app_commands.CheckFailure):
            await self._safe_reply(
                interaction, "❌ You don't have permission to use this command.", ephemeral=True
            )
        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await self._safe_reply(
                interaction,
                f"⏱️ This command is on cooldown. Try again in **{error.retry_after:.1f}s**.",
                ephemeral=True,
            )
        else:
            log.error("Unhandled slash command error in /%s: %s",
                      interaction.command.name if interaction.command else "?", error, exc_info=True)
            await self._safe_reply(
                interaction, f"❌ An unexpected error occurred: `{error}`", ephemeral=True
            )

    @staticmethod
    async def _safe_reply(interaction: discord.Interaction, content: str, **kwargs):
        """Send a reply whether the interaction has been responded to or not."""
        try:
            if interaction.response.is_done():
                await interaction.followup.send(content, **kwargs)
            else:
                await interaction.response.send_message(content, **kwargs)
        except Exception:
            pass
