"""
🌸 Sakura Bot — utils/embeds.py
Standard embed factory functions. All cogs import from here.
"""

import discord
from core.config import DEEP_CRIMSON, ERROR_RED, SUCCESS_GREEN, WARNING_YELLOW, INFO_BLUE


def sakura_embed(
    title: str = "",
    description: str = "",
    colour: int = DEEP_CRIMSON,
    footer: str = "🌸 Sakura",
) -> discord.Embed:
    """Standard Sakura embed. Enforces the dark aesthetic."""
    embed = discord.Embed(title=title, description=description, colour=colour)
    embed.set_footer(text=footer)
    return embed


def error_embed(title: str = "Error", description: str = "") -> discord.Embed:
    return sakura_embed(title=f"❌ {title}", description=description, colour=ERROR_RED)


def success_embed(title: str = "Success", description: str = "") -> discord.Embed:
    return sakura_embed(title=f"✅ {title}", description=description, colour=SUCCESS_GREEN)


def warning_embed(title: str = "Warning", description: str = "") -> discord.Embed:
    return sakura_embed(title=f"⚠️ {title}", description=description, colour=WARNING_YELLOW)


def info_embed(title: str = "Info", description: str = "") -> discord.Embed:
    return sakura_embed(title=f"ℹ️ {title}", description=description, colour=INFO_BLUE)
