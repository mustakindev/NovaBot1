"""
Database utilities for Nova bot
Provides MongoDB connection and helper functions.
"""

import asyncio
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class Database:
    """MongoDB database manager"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000
            )
            
            # Test connection
            await self.client.admin.command('ping')
            print("Connected to MongoDB successfully")
            
            # Get database (extract from connection string or use default)
            db_name = self.connection_string.split('/')[-1] or 'nova'
            self.db = self.client[db_name]
            
        except Exception as e:
            print(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            print("MongoDB connection closed")
    
    # Collection properties for easy access
    @property
    def server_settings(self):
        """Server settings collection"""
        return self.db.server_settings
    
    @property
    def economy(self):
        """Economy collection"""
        return self.db.economy
    
    @property
    def leveling(self):
        """Leveling collection"""
        return self.db.leveling
    
    @property
    def warnings(self):
        """Warnings collection"""
        return self.db.warnings
    
    @property
    def tickets(self):
        """Tickets collection"""
        return self.db.tickets
    
    @property
    def giveaways(self):
        """Giveaways collection"""
        return self.db.giveaways
    
    @property
    def autoroles(self):
        """Autoroles collection"""
        return self.db.autoroles
    
    @property
    def tags(self):
        """Custom tags collection"""
        return self.db.tags
    
    @property
    def music_playlists(self):
        """Music playlists collection"""
        return self.db.music_playlists
    
    # Helper methods
    async def get_server_settings(self, guild_id: int) -> dict:
        """Get server settings with defaults"""
        settings = await self.server_settings.find_one({"guild_id": guild_id})
        
        if not settings:
            # Create default settings
            default_settings = {
                "guild_id": guild_id,
                "leveling_enabled": True,
                "ai_chat_enabled": False,
                "welcome_enabled": False,
                "autoroles_enabled": True,
            }
            
            await self.server_settings.insert_one(default_settings)
            return default_settings
        
        return settings
    
    async def update_server_setting(self, guild_id: int, key: str, value) -> None:
        """Update a specific server setting"""
        await self.server_settings.update_one(
            {"guild_id": guild_id},
            {"$set": {key: value}},
            upsert=True
        )
    
    async def get_user_economy(self, user_id: int, guild_id: int) -> dict:
        """Get user economy data with defaults"""
        data = await self.economy.find_one({
            "user_id": user_id,
            "guild_id": guild_id
        })
        
        if not data:
            return {
                "user_id": user_id,
                "guild_id": guild_id,
                "balance": 0,
                "daily_streak": 0
            }
        
        return data
    
    async def cleanup_invalid_data(self) -> None:
        """Clean up invalid data (run periodically)"""
        try:
            # Remove autoroles for deleted roles/guilds
            # Remove expired giveaways
            # Remove old warnings (optional)
            # This would need bot instance to check if roles/guilds exist
            pass
        except Exception as e:
            print(f"Error during cleanup
