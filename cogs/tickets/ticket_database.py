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
        """Create the tickets table if it doesn't exist."""
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
            await conn.commit()
        log.info("Ticket database initialised.")

    async def create_ticket(self, channel_id: int, creator_id: int) -> bool:
        """
        Registers a newly created ticket in the database.
        Returns True if the row was inserted (first caller), False if it already existed.
        This is used to prevent duplicate welcome embeds during Railway process overlaps.
        """
        now = int(time.time())
        async with aiosqlite.connect(self.path) as conn:
            async with conn.execute(
                "INSERT OR IGNORE INTO tickets (channel_id, creator_id, created_at) VALUES (?, ?, ?)",
                (channel_id, creator_id, now)
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
