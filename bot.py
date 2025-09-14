"""
Nova - A multipurpose Discord bot
Main entry point for the bot application.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

from config import Config
from utils.database import Database
from utils.status import StatusRotator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nova.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class Nova(commands.Bot):
    """Main bot class extending discord.ext.commands.Bot"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=commands.when_mentioned_or('n!'),
            intents=intents,
            help_command=None,
            case_insensitive=True,
            strip_after_prefix=True
        )
        
        self.config = Config()
        self.db: Database = None
        self.status_rotator: StatusRotator = None
        
    async def setup_hook(self) -> None:
        """Called when the bot is starting up"""
        logger.info("Setting up Nova...")
        
        # Initialize database
        self.db = Database(self.config.MONGO_URL)
        await self.db.connect()
        
        # Initialize status rotator
        self.status_rotator = StatusRotator(self)
        
        # Load all cogs
        await self.load_cogs()
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def load_cogs(self) -> None:
        """Load all cogs from the cogs directory"""
        cogs_to_load = [
            "cogs.moderation",
            "cogs.music", 
            "cogs.ai_chat",
            "cogs.utility",
            "cogs.fun",
            "cogs.economy",
            "cogs.tickets",
            "cogs.autoroles",
            "cogs.logging_cog",
            "cogs.leveling",
            "cogs.giveaways",
            "cogs.custom"
        ]
        
        for cog_name in cogs_to_load:
            try:
                await self.load_extension(cog_name)
                logger.info(f"Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog_name}: {e}")
    
    async def on_ready(self) -> None:
        """Called when bot is ready"""
        logger.info(f"{self.user} is ready!")
        logger.info(f"Serving {len(self.guilds)} guilds")
        
        # Start status rotation
        if self.status_rotator:
            self.status_rotator.start()
    
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """Global command error handler"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        logger.error(f"Command error in {ctx.command}: {error}")
    
    async def close(self) -> None:
        """Graceful shutdown"""
        logger.info("Shutting down Nova...")
        
        if self.status_rotator:
            self.status_rotator.cancel()
            
        if self.db:
            await self.db.close()
            
        await super().close()


async def main():
    """Main entry point"""
    bot = Nova()
    
    try:
        await bot.start(bot.config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
