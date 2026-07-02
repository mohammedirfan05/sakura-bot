import discord
from discord.ext import commands
from services.ticket_service import TicketService
import asyncio

class TicketEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Detect when Ticket Tool creates a new ticket channel."""
        if not isinstance(channel, discord.TextChannel):
            return

        # Assuming Ticket Tool creates channels starting with "ticket-"
        if channel.name.startswith("ticket-"):
            # Wait briefly to ensure Ticket Tool has finished setting up the channel/permissions
            await asyncio.sleep(2)
            await TicketService.handle_new_ticket(channel)

async def setup(bot):
    await bot.add_cog(TicketEvents(bot))
