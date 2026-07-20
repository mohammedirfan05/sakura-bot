"""
🌸 Sakura Bot — cogs/custom_commands.py
Utility slash commands: /rules, /faq, /help, /socials, /customs, /ping, /serverinfo
"""

import discord
from discord.ext import commands
from discord import app_commands
import datetime
import logging

from core.config import CHANNEL_IDS, DEEP_CRIMSON, SUCCESS_GREEN, WARNING_YELLOW
from utils.embeds import sakura_embed

log = logging.getLogger(__name__)


class CustomCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /rules ────────────────────────────────────────────────────────────────
    @app_commands.command(name="rules", description="Display the server rules.")
    async def rules(self, interaction: discord.Interaction):
        embed = sakura_embed(title="📜 KARMA Server Rules")
        rules_list = [
            ("1️⃣ Be Respectful",  "No harassment, hate speech, racism, or discrimination of any kind."),
            ("2️⃣ No Spam",        "Avoid spamming messages, emojis, or excessive pings."),
            ("3️⃣ Keep it Clean",  "No NSFW content or inappropriate behaviour in any channel."),
            ("4️⃣ No Advertising", "Do not advertise other servers or services without staff permission."),
            ("5️⃣ Listen to Staff","Follow instructions from Moderators and Admins. Staff decisions are final."),
            ("6️⃣ No Alt Accounts","Do not use alt accounts to evade bans or timeouts."),
            ("7️⃣ English Only",   "Please keep conversations in English in main channels."),
        ]
        for name, value in rules_list:
            embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text="🖤 Breaking rules results in warns, timeouts, or bans.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /faq ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="faq", description="Frequently Asked Questions.")
    async def faq(self, interaction: discord.Interaction):
        embed = sakura_embed(title="❓ Frequently Asked Questions")
        faqs = [
            ("How do I get verified?",     f"Go to <#{CHANNEL_IDS['verification']}> and click the **Verify** button."),
            ("How do I open a ticket?",    f"Go to <#{CHANNEL_IDS['create_ticket']}> and select a category."),
            ("How do I level up?",         "Chat in community channels! You earn XP per message (60s cooldown)."),
            ("How do I earn Souls?",       "Use `/daily` and `/work` to earn Souls. Also win them in giveaways!"),
            ("How do I join custom games?",f"Check <#{CHANNEL_IDS['custom_matchmaking']}> for codes and queue info."),
            ("How do I apply for staff?",  "Open a ticket and select **General Support**."),
        ]
        for q, a in faqs:
            embed.add_field(name=f"❓ {q}", value=a, inline=False)
        embed.set_footer(text="🌸 Sakura FAQ")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /help ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="help", description="View all Sakura Bot commands.")
    async def help(self, interaction: discord.Interaction):
        embed = sakura_embed(
            title="🌸 Sakura Bot — Help",
            description="All available commands:",
        )
        sections = {
            "🛡️ Moderation": "/ban /kick /timeout /warn /warnings /unwarn /clear /lock /unlock /slowmode",
            "🪙 Economy":    "/daily /work /balance /pay  *(coming soon)*",
            "🎉 Giveaways":  "/giveaway start · /giveaway reroll  *(coming soon)*",
            "🤖 AI Chat":    "Chat with Sakura in designated channels  *(coming soon)*",
            "🎮 Fun":        "/8ball /coinflip /meme /cat /dog /avatar /banner",
            "📚 Utility":    "/rules /faq /help /socials /customs /ping /serverinfo",
            "⚙️ Admin":      "/setup-verification /setup-tickets /setup-roles",
        }
        for section, cmds in sections.items():
            embed.add_field(name=section, value=f"`{cmds}`", inline=False)
        embed.set_footer(text="🌸 Sakura Bot • Built for KARMA")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /socials ──────────────────────────────────────────────────────────────
    @app_commands.command(name="socials", description="View our social media links.")
    async def socials(self, interaction: discord.Interaction):
        embed = sakura_embed(
            title="🖤 KARMA Socials",
            description=(
                "Follow us and stay up to date!\n\n"
                "🎥 **YouTube** — *Coming soon*\n"
                "📸 **TikTok** — *Coming soon*\n"
                "🐦 **Twitter/X** — *Coming soon*\n"
                "🎮 **Twitch** — *Coming soon*"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /customs ──────────────────────────────────────────────────────────────
    @app_commands.command(name="customs", description="Learn how custom matches work.")
    async def customs(self, interaction: discord.Interaction):
        embed = sakura_embed(
            title="⚔️ Custom Matchmaking Info",
            description=(
                f"Head over to <#{CHANNEL_IDS['custom_matchmaking']}> "
                f"and <#{CHANNEL_IDS['queue_status']}> to see live game info.\n\n"
                "**How to join:**\n"
                "1. Check the queue status channel.\n"
                "2. Wait for a code drop announcement.\n"
                "3. Enter the code in Fortnite › Island Code.\n\n"
                "*Codes are distributed fairly — first come, first served!*"
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /ping ─────────────────────────────────────────────────────────────────
    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        colour  = SUCCESS_GREEN if latency < 100 else WARNING_YELLOW
        embed   = discord.Embed(
            title="🏓 Pong!",
            description=f"**{latency}ms** latency",
            colour=colour,
        )
        embed.set_footer(text="🌸 Sakura Bot")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── /serverinfo ───────────────────────────────────────────────────────────
    @app_commands.command(name="serverinfo", description="View information about this server.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"🌸 {guild.name}", colour=DEEP_CRIMSON)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner",          value=f"<@{guild.owner_id}>",               inline=True)
        embed.add_field(name="Members",        value=f"{guild.member_count:,}",             inline=True)
        embed.add_field(name="Boost Tier",     value=f"Tier {guild.premium_tier}",          inline=True)
        embed.add_field(name="Boosts",         value=guild.premium_subscription_count,      inline=True)
        embed.add_field(name="Text Channels",  value=len(guild.text_channels),              inline=True)
        embed.add_field(name="Voice Channels", value=len(guild.voice_channels),             inline=True)
        embed.add_field(name="Roles",          value=len(guild.roles),                      inline=True)
        embed.add_field(name="Created",        value=discord.utils.format_dt(guild.created_at, style="R"), inline=True)
        embed.set_footer(text=f"Guild ID: {guild.id}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(CustomCommands(bot))
