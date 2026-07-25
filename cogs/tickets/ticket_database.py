"""
🌸 Sakura Bot — cogs/tickets/ticket_database.py
Database layer for the Ticket Claim system.
"""

import aiosqlite
import time
import logging
from typing import Optional

log = logging.getLogger(__name__)

DB_PATH = "data/sakura.db"


class TicketDatabase:
    """Async database manager for ticket claims."""

    def __init__(self, path: str = DB_PATH):
        self.path = path

    async def init(self) -> None:
        """Create the tickets table and perform idempotent migrations if needed."""
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER UNIQUE NOT NULL,
                    creator_id INTEGER NOT NULL,
                    claimer_id INTEGER,
                    status TEXT DEFAULT 'OPEN',
                    created_at INTEGER NOT NULL,
                    claimed_at INTEGER,
                    closed_at INTEGER
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ticket_roles (
                    role_id INTEGER PRIMARY KEY,
                    added_by INTEGER NOT NULL
                );
            """)
            
            # Idempotent column additions for Winner Claim features
            columns = [
                ("ticket_type", "TEXT DEFAULT 'SPRITE'"),
                ("epic_name", "TEXT"),
                ("discord_username", "TEXT"),
                ("game_mode", "TEXT"),
                ("date_won", "TEXT"),
                ("proof_url", "TEXT"),
                ("winner_confirmed", "INTEGER DEFAULT 0"),
                ("rules_checked", "INTEGER DEFAULT 0"),
                ("win_limit_checked", "INTEGER DEFAULT 0"),
                ("prize_approved", "INTEGER DEFAULT 0"),
                ("prize_sent", "INTEGER DEFAULT 0"),
                ("prize_sent_by", "INTEGER"),
                ("prize_sent_at", "INTEGER"),
                ("winner_status", "TEXT DEFAULT '🟡 Waiting for Verification'")
            ]
            for col_name, col_type in columns:
                try:
                    await conn.execute(f"ALTER TABLE tickets ADD COLUMN {col_name} {col_type};")
                except Exception:
                    # Column already exists
                    pass

            await conn.commit()
        log.info("Ticket database initialised with schema migrations.")

    async def create_ticket(
        self,
        channel_id: int,
        creator_id: int,
        ticket_type: str = "SPRITE",
        epic_name: Optional[str] = None,
        discord_username: Optional[str] = None,
        game_mode: Optional[str] = None,
        date_won: Optional[str] = None,
        proof_url: Optional[str] = None
    ) -> bool:
        """
        Registers a newly created ticket in the database.
        Returns True if the row was inserted, False if it already existed.
        """
        now = int(time.time())
        async with aiosqlite.connect(self.path) as conn:
            async with conn.execute(
                """
                INSERT OR IGNORE INTO tickets (
                    channel_id, creator_id, created_at, ticket_type,
                    epic_name, discord_username, game_mode, date_won, proof_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (channel_id, creator_id, now, ticket_type, epic_name, discord_username, game_mode, date_won, proof_url)
            ) as cur:
                await conn.commit()
                return cur.rowcount > 0

    async def get_ticket(self, channel_id: int) -> Optional[dict]:
        """Fetch a ticket by its channel ID."""
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_open_ticket_by_user(self, creator_id: int) -> Optional[dict]:
        """Return the most recent open/claimed ticket for a user, or None."""
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM tickets WHERE creator_id = ? AND status IN ('OPEN', 'CLAIMED') ORDER BY created_at DESC LIMIT 1",
                (creator_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def claim_ticket(self, channel_id: int, claimer_id: int) -> bool:
        """Mark a ticket as CLAIMED by a staff member."""
        now = int(time.time())
        async with aiosqlite.connect(self.path) as conn:
            # Only claim if it's OPEN
            async with conn.execute(
                "UPDATE tickets SET claimer_id = ?, status = 'CLAIMED', claimed_at = ? WHERE channel_id = ? AND status = 'OPEN'",
                (claimer_id, now, channel_id)
            ) as cur:
                await conn.commit()
                return cur.rowcount > 0

    async def update_status(self, channel_id: int, status: str) -> None:
        """Update the ticket's status (e.g., to CLOSED)."""
        now = int(time.time())
        async with aiosqlite.connect(self.path) as conn:
            if status == "CLOSED":
                await conn.execute(
                    "UPDATE tickets SET status = ?, closed_at = ? WHERE channel_id = ?",
                    (status, now, channel_id)
                )
            else:
                await conn.execute(
                    "UPDATE tickets SET status = ? WHERE channel_id = ?",
                    (status, channel_id)
                )
            await conn.commit()

    async def update_verification_check(self, channel_id: int, check_name: str, value: bool) -> None:
        """Toggle verification checklist fields (winner_confirmed, rules_checked, win_limit_checked, prize_approved)."""
        allowed = {"winner_confirmed", "rules_checked", "win_limit_checked", "prize_approved"}
        if check_name not in allowed:
            raise ValueError(f"Invalid verification check field: {check_name}")

        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                f"UPDATE tickets SET {check_name} = ? WHERE channel_id = ?",
                (1 if value else 0, channel_id)
            )
            await conn.commit()

    async def update_winner_status(self, channel_id: int, winner_status: str) -> None:
        """Update visual ticket winner status (e.g., 🟡 Waiting for Verification, 🔵 Under Review, etc.)."""
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE tickets SET winner_status = ? WHERE channel_id = ?",
                (winner_status, channel_id)
            )
            await conn.commit()

    async def mark_prize_sent(self, channel_id: int, staff_id: int) -> None:
        """Mark V-Bucks / Prize as sent for a winner claim ticket."""
        now = int(time.time())
        async with aiosqlite.connect(self.path) as conn:
            await conn.execute(
                "UPDATE tickets SET prize_sent = 1, prize_sent_by = ?, prize_sent_at = ? WHERE channel_id = ?",
                (staff_id, now, channel_id)
            )
            await conn.commit()

    async def add_ticket_role(self, role_id: int, added_by: int) -> bool:
        """Add a role to the authorized ticket managers list."""
        async with aiosqlite.connect(self.path) as conn:
            async with conn.execute(
                "INSERT OR IGNORE INTO ticket_roles (role_id, added_by) VALUES (?, ?)",
                (role_id, added_by)
            ) as cur:
                await conn.commit()
                return cur.rowcount > 0

    async def remove_ticket_role(self, role_id: int) -> bool:
        """Remove a role from the authorized ticket managers list."""
        async with aiosqlite.connect(self.path) as conn:
            async with conn.execute(
                "DELETE FROM ticket_roles WHERE role_id = ?",
                (role_id,)
            ) as cur:
                await conn.commit()
                return cur.rowcount > 0

    async def get_ticket_roles(self) -> list[int]:
        """Get all authorized dynamic ticket role IDs."""
        async with aiosqlite.connect(self.path) as conn:
            async with conn.execute("SELECT role_id FROM ticket_roles") as cur:
                rows = await cur.fetchall()
                return [row[0] for row in rows]

ticket_db = TicketDatabase()

