"""
🌸 Sakura Bot — core/database.py
DatabaseManager class: async SQLite interface with connection pool (WAL mode),
full schema management, and all methods used by the cog layer.

Usage:
    from core.database import db
    user = await db.get_user(discord_id)
"""

import aiosqlite
import asyncio
import time
import logging
from typing import Optional

log = logging.getLogger(__name__)

DB_PATH = "data/sakura.db"

# XP formula: xp required to reach `level` from level 0
def _xp_for_level(level: int) -> int:
    """Total XP required to reach `level`. Uses quadratic curve."""
    return 5 * (level ** 2) + 50 * level + 100


class DatabaseManager:
    """
    Singleton async database manager.
    Call `await db.init()` once at startup (done in init_db()).
    All public methods open a fresh connection from the pool.
    """

    def __init__(self, path: str = DB_PATH):
        self.path = path
        self._lock = asyncio.Lock()

    # ── Schema ────────────────────────────────────────────────────────────────

    async def init(self) -> None:
        """Create tables and indexes if they don't exist. Call once at startup."""
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id      INTEGER PRIMARY KEY,
                    xp              INTEGER DEFAULT 0,
                    level           INTEGER DEFAULT 0,
                    karma_score     INTEGER DEFAULT 0,
                    souls_balance   INTEGER DEFAULT 0,
                    faction_id      TEXT,
                    last_daily      INTEGER DEFAULT 0,
                    last_work       INTEGER DEFAULT 0,
                    created_at      INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS warnings (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id         INTEGER NOT NULL,
                    guild_id        INTEGER NOT NULL,
                    moderator_id    INTEGER NOT NULL,
                    reason          TEXT    NOT NULL DEFAULT 'No reason provided',
                    created_at      INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_warnings_user
                    ON warnings (user_id, guild_id);

                CREATE TABLE IF NOT EXISTS factions (
                    id              TEXT PRIMARY KEY,
                    total_points    INTEGER DEFAULT 0,
                    leader_id       INTEGER
                );

                CREATE TABLE IF NOT EXISTS matchmaking_sessions (
                    id              TEXT PRIMARY KEY,
                    host_id         INTEGER NOT NULL,
                    game            TEXT    NOT NULL,
                    join_code       TEXT,
                    status          TEXT    DEFAULT 'pending',
                    created_at      INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reaction_role_messages (
                    message_id      INTEGER PRIMARY KEY,
                    channel_id      INTEGER NOT NULL,
                    panel_type      TEXT    NOT NULL
                );

                INSERT OR IGNORE INTO factions (id)
                VALUES ('kitsune'), ('ronin'), ('dragon'), ('reaper');
            """)
            await conn.commit()
        log.info("Database initialised at %s", self.path)

    # ── User helpers ──────────────────────────────────────────────────────────

    async def get_user(self, discord_id: int) -> dict:
        """Fetch a user row, auto-creating it if it doesn't exist."""
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM users WHERE discord_id = ?", (discord_id,)
            ) as cur:
                row = await cur.fetchone()
                if row:
                    return dict(row)

            now = int(time.time())
            await conn.execute(
                "INSERT INTO users (discord_id, created_at) VALUES (?, ?)",
                (discord_id, now),
            )
            await conn.commit()
            return {
                "discord_id":    discord_id,
                "xp":            0,
                "level":         0,
                "karma_score":   0,
                "souls_balance": 0,
                "faction_id":    None,
                "last_daily":    0,
                "last_work":     0,
                "created_at":    now,
            }

    # ── XP / Leveling ─────────────────────────────────────────────────────────

    @staticmethod
    def xp_for_level(level: int) -> int:
        """XP threshold to reach `level`."""
        return _xp_for_level(level)

    async def add_xp(self, discord_id: int, amount: int) -> tuple[int, int, bool]:
        """
        Add `amount` XP to a user. Handles level-ups automatically.
        Returns (new_xp, new_level, leveled_up).
        """
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            # Ensure user exists
            await self.get_user(discord_id)

            async with conn.execute(
                "SELECT xp, level FROM users WHERE discord_id = ?", (discord_id,)
            ) as cur:
                row = await cur.fetchone()

            xp    = (row["xp"] or 0) + amount
            level = row["level"] or 0

            leveled_up = False
            while xp >= _xp_for_level(level + 1):
                xp -= _xp_for_level(level + 1)
                level += 1
                leveled_up = True

            await conn.execute(
                "UPDATE users SET xp = ?, level = ? WHERE discord_id = ?",
                (xp, level, discord_id),
            )
            await conn.commit()
        return xp, level, leveled_up

    async def get_leaderboard(self, limit: int = 10) -> list[dict]:
        """Return top `limit` users ordered by level desc, then xp desc."""
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT discord_id AS user_id, xp, level FROM users "
                "ORDER BY level DESC, xp DESC LIMIT ?",
                (limit,),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    # ── Warnings ──────────────────────────────────────────────────────────────

    async def add_warning(
        self, user_id: int, guild_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        Add a warning. Returns the user's new total warning count for this guild.
        """
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "INSERT INTO warnings (user_id, guild_id, moderator_id, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, guild_id, moderator_id, reason, int(time.time())),
            )
            await conn.commit()
            async with conn.execute(
                "SELECT COUNT(*) FROM warnings WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id),
            ) as cur:
                row = await cur.fetchone()
                return row[0]

    async def get_warnings(self, user_id: int, guild_id: int) -> list[dict]:
        """Return all warnings for a user in the guild, oldest first."""
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT reason, moderator_id AS moderator, created_at FROM warnings "
                "WHERE user_id = ? AND guild_id = ? ORDER BY created_at ASC",
                (user_id, guild_id),
            ) as cur:
                return [dict(r) for r in await cur.fetchall()]

    async def clear_warnings(self, user_id: int, guild_id: int) -> None:
        """Delete all warnings for a user in the guild."""
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "DELETE FROM warnings WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id),
            )
            await conn.commit()

    # ── Economy ───────────────────────────────────────────────────────────────

    async def get_balance(self, discord_id: int) -> int:
        """Return a user's souls_balance."""
        user = await self.get_user(discord_id)
        return user["souls_balance"]

    async def add_souls(self, discord_id: int, amount: int) -> int:
        """Add (or subtract) souls. Returns new balance. Raises ValueError if result < 0."""
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            await self.get_user(discord_id)  # ensure exists
            async with conn.execute(
                "SELECT souls_balance FROM users WHERE discord_id = ?", (discord_id,)
            ) as cur:
                row = await cur.fetchone()
            new_bal = (row["souls_balance"] or 0) + amount
            if new_bal < 0:
                raise ValueError("Insufficient souls balance")
            await conn.execute(
                "UPDATE users SET souls_balance = ? WHERE discord_id = ?",
                (new_bal, discord_id),
            )
            await conn.commit()
        return new_bal

    async def get_last_daily(self, discord_id: int) -> int:
        """Return Unix timestamp of last /daily claim."""
        user = await self.get_user(discord_id)
        return user["last_daily"]

    async def set_last_daily(self, discord_id: int) -> None:
        """Stamp /daily as claimed now."""
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE users SET last_daily = ? WHERE discord_id = ?",
                (int(time.time()), discord_id),
            )
            await conn.commit()

    async def get_last_work(self, discord_id: int) -> int:
        """Return Unix timestamp of last /work use."""
        user = await self.get_user(discord_id)
        return user["last_work"]

    async def set_last_work(self, discord_id: int) -> None:
        """Stamp /work as used now."""
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE users SET last_work = ? WHERE discord_id = ?",
                (int(time.time()), discord_id),
            )
            await conn.commit()


# ── Module-level singleton ─────────────────────────────────────────────────────
db = DatabaseManager()


async def init_db() -> None:
    """Called by bot.setup_hook() to initialise the DB on startup."""
    await db.init()
