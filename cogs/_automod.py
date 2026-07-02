"""
🌸 Sakura Bot — cogs/automod.py
Automatic moderation layer. Runs silently in the background on every message.

Detections:
  1. Spam          — N messages in T seconds per user → delete burst + timeout
  2. Scam links    — Known phishing/scam domains → delete + warn
  3. Mass mentions — Too many @user pings in one message → delete + warn
  4. Invite links  — Discord invite links to non-allowlisted servers → delete + warn

All violations:
  - Message deleted
  - User warned (via db.add_warning, same as manual /warn)
  - Action logged to #mod_logs
  - Staff messages are always exempt
"""

import re
import time
import logging
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands

from core.config import (
    CHANNEL_IDS, STAFF_ROLE_IDS,
    AUTOMOD_SPAM_COUNT, AUTOMOD_SPAM_WINDOW, AUTOMOD_MENTION_MAX,
    AUTOMOD_ALLOWED_GUILDS, ERROR_RED, WARNING_YELLOW,
)
from core.database import db

log = logging.getLogger(__name__)

# ── Compiled regexes ──────────────────────────────────────────────────────────

# Discord invite patterns: discord.gg/xxx  |  discord.com/invite/xxx
_INVITE_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/([A-Za-z0-9\-]+)",
    re.IGNORECASE,
)

# Common phishing/scam domain fragments (substring match against lowercased message)
_SCAM_PATTERNS = [
    # Nitro scams
    r"free[-_]?nitro",
    r"nitro[-_]?gift",
    r"discord[-_]?nitro.*free",
    r"steamgift",
    r"steam[-_]?gift",
    # Crypto/NFT pump-and-dump
    r"nft[-_]?giveaway",
    r"claim.*(?:eth|btc|crypto|sol|usdt)",
    # Known scam domains (add more as seen)
    r"discordnitro\.(?:com|gg|io|xyz|top|shop|click|fun|online|site|live)",
    r"disord\.gg",           # typosquat
    r"discordapp-gift",
    r"discord-gift\.",
    r"dsc\.gg/gift",
    r"steamcommunity\.(?:ru|com\.ru|net)",
    r"steampowered\.(?:ru|xyz|tk|ml|ga|cf)",
    r"tradeoffer\.(?:ru|xyz|tk|ml|ga|cf)",
    # Generic suspicious TLDs combined with gift/free keywords
    r"(?:gift|free|prize|win|claim|reward).*\.(?:xyz|tk|ml|ga|cf|top|click|pw|cc|su)",
]
_SCAM_RE = re.compile("|".join(_SCAM_PATTERNS), re.IGNORECASE)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _is_staff(member: discord.Member) -> bool:
    return any(r.id in STAFF_ROLE_IDS for r in member.roles)


# ─────────────────────────────────────────────────────────────────────────────
#  AutoMod Cog
# ─────────────────────────────────────────────────────────────────────────────

class AutoMod(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Spam tracking: user_id → deque of message timestamps
        self._spam_tracker: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=AUTOMOD_SPAM_COUNT + 2)
        )
        # Cooldown: skip duplicate warnings within this window (seconds)
        self._action_cooldown: dict[int, float] = {}
        self._cooldown_window = 10.0

        # Build set of exempt channel IDs at startup
        self._exempt_channels: set[int] = {
            CHANNEL_IDS.get("staff_chat",     0),
            CHANNEL_IDS.get("staff_commands", 0),
            CHANNEL_IDS.get("reports",        0),
            CHANNEL_IDS.get("mod_logs",       0),
            CHANNEL_IDS.get("logs",           0),
        } - {0}

    # ── Main listener ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore DMs, bots, and staff
        if not message.guild or message.author.bot:
            return
        if not isinstance(message.author, discord.Member):
            return
        if _is_staff(message.author):
            return
        if message.channel.id in self._exempt_channels:
            return

        # Run all checks; stop at first hit to avoid double-punishing
        if await self._check_spam(message):
            return
        if await self._check_scam_links(message):
            return
        if await self._check_invites(message):
            return
        if await self._check_mass_mentions(message):
            return

    # ── 1. Spam detection ─────────────────────────────────────────────────────

    async def _check_spam(self, message: discord.Message) -> bool:
        uid  = message.author.id
        now  = time.monotonic()
        hist = self._spam_tracker[uid]
        hist.append(now)

        # Only look at the last AUTOMOD_SPAM_COUNT timestamps
        if len(hist) < AUTOMOD_SPAM_COUNT:
            return False

        window_start = now - AUTOMOD_SPAM_WINDOW
        recent = [t for t in hist if t >= window_start]
        if len(recent) < AUTOMOD_SPAM_COUNT:
            return False

        # Spam confirmed — clear their history to reset the window
        hist.clear()

        if not await self._can_act(uid):
            return True

        # Delete all recent messages from this user in this channel
        try:
            def is_spam_msg(m: discord.Message):
                return (
                    m.author.id == uid
                    and (time.monotonic() - now) < AUTOMOD_SPAM_WINDOW + 2
                )
            await message.channel.purge(limit=20, check=lambda m: m.author.id == uid)
        except discord.HTTPException:
            pass

        # Timeout 5 minutes
        try:
            import datetime
            until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
            await message.author.timeout(until, reason="AutoMod: spam")
        except discord.HTTPException:
            pass

        total = await db.add_warning(uid, message.guild.id, self.bot.user.id, "AutoMod: Spam")
        await self._log_action(
            message.guild,
            "🚫 AutoMod — Spam Detected",
            WARNING_YELLOW,
            User=message.author.mention,
            Channel=message.channel.mention,
            Action="Messages deleted • 5 min timeout",
            TotalWarns=total,
        )
        try:
            await message.author.send(
                embed=discord.Embed(
                    description=(
                        "⚠️ You were timed out in **KARMA** for **spamming**.\n"
                        "Please slow down — the cooldown is 5 minutes."
                    ),
                    colour=WARNING_YELLOW,
                )
            )
        except Exception:
            pass
        return True

    # ── 2. Scam / phishing link detection ────────────────────────────────────

    async def _check_scam_links(self, message: discord.Message) -> bool:
        if not _SCAM_RE.search(message.content):
            return False
        if not await self._can_act(message.author.id):
            return True

        try:
            await message.delete()
        except discord.HTTPException:
            pass

        total = await db.add_warning(
            message.author.id, message.guild.id,
            self.bot.user.id, "AutoMod: Scam/phishing link"
        )
        await self._log_action(
            message.guild,
            "🔗 AutoMod — Scam Link Detected",
            ERROR_RED,
            User=message.author.mention,
            Channel=message.channel.mention,
            Content=message.content[:200],
            TotalWarns=total,
        )
        try:
            await message.channel.send(
                embed=discord.Embed(
                    description=(
                        f"⚠️ {message.author.mention} — Scam/phishing links are **not allowed** here. "
                        f"Your message was removed."
                    ),
                    colour=ERROR_RED,
                ),
                delete_after=8,
            )
        except discord.HTTPException:
            pass
        try:
            await message.author.send(
                embed=discord.Embed(
                    description=(
                        "⚠️ Your message in **KARMA** was removed for containing a suspected "
                        "scam or phishing link.\n\nIf this was a mistake, please open a ticket."
                    ),
                    colour=ERROR_RED,
                )
            )
        except Exception:
            pass
        return True

    # ── 3. Discord invite filter ──────────────────────────────────────────────

    async def _check_invites(self, message: discord.Message) -> bool:
        matches = _INVITE_RE.findall(message.content)
        if not matches:
            return False

        # Validate each invite; allow if it points to an allowed guild
        for code in matches:
            try:
                invite = await self.bot.fetch_invite(code)
                if invite.guild and invite.guild.id in AUTOMOD_ALLOWED_GUILDS:
                    continue
                # Not allowed
                break
            except discord.NotFound:
                break   # Invalid invite, still remove it
            except discord.HTTPException:
                break
        else:
            # All invites were from allowed guilds
            return False

        if not await self._can_act(message.author.id):
            return True

        try:
            await message.delete()
        except discord.HTTPException:
            pass

        total = await db.add_warning(
            message.author.id, message.guild.id,
            self.bot.user.id, "AutoMod: Unauthorised Discord invite"
        )
        await self._log_action(
            message.guild,
            "📨 AutoMod — Invite Link Blocked",
            WARNING_YELLOW,
            User=message.author.mention,
            Channel=message.channel.mention,
            TotalWarns=total,
        )
        try:
            await message.channel.send(
                embed=discord.Embed(
                    description=(
                        f"⚠️ {message.author.mention} — Advertising other servers is **not allowed**. "
                        f"Your message was removed."
                    ),
                    colour=WARNING_YELLOW,
                ),
                delete_after=8,
            )
        except discord.HTTPException:
            pass
        return True

    # ── 4. Mass mention detection ─────────────────────────────────────────────

    async def _check_mass_mentions(self, message: discord.Message) -> bool:
        # Count unique user mentions + @everyone/@here
        mention_count = len(set(m.id for m in message.mentions))
        if message.mention_everyone:
            mention_count += 2  # weight @everyone/@here heavily

        if mention_count < AUTOMOD_MENTION_MAX:
            return False

        if not await self._can_act(message.author.id):
            return True

        try:
            await message.delete()
        except discord.HTTPException:
            pass

        total = await db.add_warning(
            message.author.id, message.guild.id,
            self.bot.user.id, f"AutoMod: Mass mention ({mention_count} mentions)"
        )
        await self._log_action(
            message.guild,
            "📣 AutoMod — Mass Mention",
            ERROR_RED,
            User=message.author.mention,
            Channel=message.channel.mention,
            Mentions=mention_count,
            TotalWarns=total,
        )
        try:
            await message.channel.send(
                embed=discord.Embed(
                    description=(
                        f"⚠️ {message.author.mention} — Mass pinging is **not allowed**. "
                        f"Your message was removed."
                    ),
                    colour=ERROR_RED,
                ),
                delete_after=8,
            )
        except discord.HTTPException:
            pass
        return True

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _can_act(self, user_id: int) -> bool:
        """
        Returns True if we haven't already acted on this user within the cooldown window.
        Prevents duplicate punishments when multiple violations fire at once.
        """
        now = time.monotonic()
        last = self._action_cooldown.get(user_id, 0)
        if now - last < self._cooldown_window:
            return False
        self._action_cooldown[user_id] = now
        return True

    async def _log_action(self, guild: discord.Guild, title: str, colour: int, **fields):
        """Post a styled embed to #mod_logs."""
        channel = guild.get_channel(CHANNEL_IDS["mod_logs"])
        if not channel:
            return
        import datetime
        embed = discord.Embed(
            title=title,
            colour=colour,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        for name, value in fields.items():
            embed.add_field(name=name, value=str(value), inline=True)
        embed.set_footer(text="🌸 Sakura AutoMod")
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as exc:
            log.warning("Failed to post automod log: %s", exc)

    # ── /automod-status ───────────────────────────────────────────────────────

    @app_commands.command(
        name="automod-status",
        description="[Staff] Show current AutoMod configuration.",
    )
    @app_commands.default_permissions(moderate_members=True)
    async def automod_status(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛡️ AutoMod Status", colour=discord.Colour.blurple())
        embed.add_field(
            name="Spam",
            value=f"{AUTOMOD_SPAM_COUNT} messages / {AUTOMOD_SPAM_WINDOW}s → 5 min timeout",
            inline=False,
        )
        embed.add_field(
            name="Scam Links",
            value=f"{len(_SCAM_PATTERNS)} patterns active",
            inline=False,
        )
        embed.add_field(
            name="Mass Mentions",
            value=f">{AUTOMOD_MENTION_MAX} unique mentions → warn + delete",
            inline=False,
        )
        embed.add_field(
            name="Invite Filter",
            value=f"Active • {len(AUTOMOD_ALLOWED_GUILDS)} allowed guild(s)",
            inline=False,
        )
        embed.add_field(
            name="Exempt Channels",
            value=f"{len(self._exempt_channels)} staff channels",
            inline=False,
        )
        embed.set_footer(text="🌸 Sakura AutoMod")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoMod(bot))
