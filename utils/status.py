"""
Status rotation utility for Nova bot
Manages automatic status rotation with dynamic information.
"""

import asyncio
import random
from typing import List

import discord
from discord.ext import tasks


class StatusRotator:
    """Manages rotating bot status messages"""
    
    def __init__(self, bot):
        self.bot = bot
        self.current_index = 0
        self.statuses = [
            {"type": discord.ActivityType.watching, "name": "over {guild_count} cute servers 💕"},
            {"type": discord.ActivityType.playing, "name": "/help for 150+ commands ✨"},
            {"type": discord.ActivityType.listening, "name": "to Spotify vibes 🎵"},
            {"type": discord.ActivityType.competing, "name": "to be your #1 multipurpose bot 🌸"},
            {"type": discord.ActivityType.watching, "name": "tickets being opened 📬"},
            {"type": discord.ActivityType.playing, "name": "with new ideas from users 🌟"},
            {"type": discord.ActivityType.listening, "name": "to your questions with AI 🤍"},
            {"type": discord.ActivityType.watching, "name": "over amazing communities 🌺"},
            {"type": discord.ActivityType.playing, "name": "music for everyone 🎶"},
            {"type": discord.ActivityType.listening, "name": "to feedback and suggestions 💖"}
        ]
    
    @tasks.loop(seconds=30)
    async def rotate_status(self):
        """Rotate the bot's status every 30 seconds"""
        try:
            if not self.statuses:
                return
            
            status = self.statuses[self.current_index]
            guild_count = len(self.bot.guilds)
            user_count = len(self.bot.users)
            
            formatted_name = status["name"].format(
                guild_count=guild_count,
                user_count=user_count
            )
            
            activity = discord.Activity(
                type=status["type"],
                name=formatted_name
            )
            
            await self.bot.change_presence(activity=activity, status=discord.Status.online)
            
            self.current_index = (self.current_index + 1) % len(self.statuses)
            
        except Exception as e:
            print(f"Error updating status: {e}")
    
    @rotate_status.before_loop
    async def before_rotate_status(self):
        """Wait for bot to be ready before starting rotation"""
        await self.bot.wait_until_ready()
    
    def start(self):
        """Start status rotation"""
        if not self.rotate_status.is_running():
            self.rotate_status.start()
    
    def stop(self):
        """Stop status rotation"""
        if self.rotate_status.is_running():
            self.rotate_status.cancel()
    
    def add_status(self, activity_type: discord.ActivityType, name: str):
        """Add a new status to the rotation"""
        self.statuses.append({"type": activity_type, "name": name})
    
    def remove_status(self, index: int):
        """Remove a status from rotation by index"""
        if 0 <= index < len(self.statuses):
            self.statuses.pop(index)
            if self.current_index >= len(self.statuses):
                self.current_index = 0
    
    def set_custom_status(self, activity_type: discord.ActivityType, name: str):
        """Set a temporary custom status (stops rotation)"""
        asyncio.create_task(self._set_custom_status(activity_type, name))
    
    async def _set_custom_status(self, activity_type: discord.ActivityType, name: str):
        """Set custom status helper"""
        try:
            self.stop()
            activity = discord.Activity(type=activity_type, name=name)
            await self.bot.change_presence(activity=activity)
        except Exception as e:
            print(f"Error setting custom status: {e}")
    
    def resume_rotation(self):
        """Resume normal status rotation"""
        self.start()
    
    def shuffle_statuses(self):
        """Randomize the order of statuses"""
        random.shuffle(self.statuses)
        self.current_index = 0
    
    def get_current_status(self) -> dict:
        """Get the current status info"""
        if self.statuses:
            return self.statuses[self.current_index]
        return {}
    
    def get_all_statuses(self) -> List[dict]:
        """Get all configured statuses"""
        return self.statuses.copy()
    
    def cancel(self):
        """Cancel the status rotation task"""
        if self.rotate_status.is_running():
            self.rotate_status.cancel()


class StatusPresets:
    """Predefined status sets for special occasions"""
    
    HOLIDAY_CHRISTMAS = [
        {"type": discord.ActivityType.watching, "name": "Christmas magic ❄️🎄"},
        {"type": discord.ActivityType.playing, "name": "in the snow ⛄"},
        {"type": discord.ActivityType.listening, "name": "to Christmas carols 🎵"},
    ]
    
    HOLIDAY_HALLOWEEN = [
        {"type": discord.ActivityType.watching, "name": "spooky servers 👻"},
        {"type": discord.ActivityType.playing, "name": "trick or treat 🎃"},
        {"type": discord.ActivityType.listening, "name": "to Halloween music 🦇"},
    ]
    
    MAINTENANCE = [
        {"type": discord.ActivityType.playing, "name": "under maintenance 🔧"},
        {"type": discord.ActivityType.watching, "name": "for updates 📡"},
    ]
    
    NEW_YEAR = [
        {"type": discord.ActivityType.watching, "name": "fireworks 🎆"},
        {"type": discord.ActivityType.playing, "name": "with confetti 🎊"},
        {"type": discord.ActivityType.listening, "name": "to New Year tunes 🎶"},
                          ]
