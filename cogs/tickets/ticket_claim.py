import discord
from discord.ext import commands
import logging
from cogs.tickets.ticket_database import ticket_db
from cogs.tickets.ticket_events import TicketEvents
from cogs.tickets.ticket_buttons import TicketView

log = logging.getLogger(__name__)

class TicketClaim(commands.Cog):
    """Main cog for the Sakura Ticket Claim System."""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_load(self):
        """Called when the cog is loaded."""
        # Initialize DB table for tickets
        await ticket_db.init()
        # Register the persistent view
        self.bot.add_view(TicketView())
        log.info("Ticket Claim system initialized and views registered.")

async def setup(bot):
    await bot.add_cog(TicketClaim(bot))
    # We also load the events cog here so they are bundled
    await bot.add_cog(TicketEvents(bot))
