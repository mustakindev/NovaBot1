"""
Leveling cog for Nova bot
Provides XP and ranking system functionality.
"""

import math
import random
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class Leveling(commands.Cog):
    """XP and leveling system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp_cooldowns = {}  # Simple in-memory cooldown tracking
    
    def calculate_level(self, xp: int) -> int:
        """Calculate level from XP"""
        # Formula: level = sqrt(xp / 100)
        return int(math.sqrt(xp / 100))
    
    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP needed for a specific level"""
        return level * level * 100
    
    def calculate_xp_for_next_level(self, current_xp: int) -> int:
        """Calculate XP needed for next level"""
        current_level = self.calculate_level(current_xp)
        next_level_xp = self.calculate_xp_for_level(current_level + 1)
        return next_level_xp - current_xp
    
    async def get_user_data(self, user_id: int, guild_id: int) -> dict:
        """Get user's leveling data"""
        data = await self.bot.db.leveling.find_one({
            "user_id": user_id,
            "guild_id": guild_id
        })
        
        if not data:
            return {"user_id": user_id, "guild_id": guild_id, "xp": 0, "messages": 0}
        
        return data
    
    async def add_xp(self, user_id: int, guild_id: int, xp_gained: int) -> dict:
        """Add XP to user and return updated data"""
        result = await self.bot.db.leveling.find_one_and_update(
            {"user_id": user_id, "guild_id": guild_id},
            {
                "$inc": {"xp": xp_gained, "messages": 1},
                "$set": {"last_message": datetime.utcnow()}
            },
            upsert=True,
            return_document=True
        )
        
        return result
    
    @app_commands.command(name="rank", description="📊 Check your or someone's rank")
    @app_commands.describe(user="User to check rank for (optional)")
    async def rank(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Check user's rank and level"""
        target = user if user else interaction.user
        
        if target.bot:
            embed = EmbedBuilder.error("Bots don't have ranks!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        user_data = await self.get_user_data(target.id, interaction.guild.id)
        current_xp = user_data["xp"]
        current_level = self.calculate_level(current_xp)
        xp_for_next = self.calculate_xp_for_next_level(current_xp)
        xp_for_current_level = self.calculate_xp_for_level(current_level)
        progress_xp = current_xp - xp_for_current_level
        progress_needed = self.calculate_xp_for_level(current_level + 1) - xp_for_current_level
        
        # Calculate server rank
        pipeline = [
            {"$match": {"guild_id": interaction.guild.id}},
            {"$sort": {"xp": -1}},
            {"$group": {
                "_id": None,
                "users": {"$push": {"user_id": "$user_id", "xp": "$xp"}}
            }}
        ]
        
        result = await self.bot.db.leveling.aggregate(pipeline).to_list(length=1)
        rank = "N/A"
        
        if result and result[0]["users"]:
            for i, user_rank in enumerate(result[0]["users"], 1):
                if user_rank["user_id"] == target.id:
                    rank = f"#{i}"
                    break
        
        embed = EmbedBuilder.create(
            title=f"📊 {target.display_name}'s Rank",
            color=discord.Color.from_rgb(144, 238, 144)
        )
        
        if target.avatar:
            embed.set_thumbnail(url=target.avatar.url)
        
        embed.add_field(name="Level", value=str(current_level), inline=True)
        embed.add_field(name="XP", value=f"{current_xp:,}", inline=True)
        embed.add_field(name="Rank", value=rank, inline=True)
        
        embed.add_field(name="Progress", value=f"{progress_xp}/{progress_needed} XP", inline=True)
        embed.add_field(name="XP to Next Level", value=f"{xp_for_next:,}", inline=True)
        embed.add_field(name="Messages Sent", value=f"{user_data.get('messages', 0):,}", inline=True)
        
        # Progress bar
        if progress_needed > 0:
            progress_percent = (progress_xp / progress_needed) * 100
            filled_blocks = int(progress_percent / 10)
            empty_blocks = 10 - filled_blocks
            progress_bar = "█" * filled_blocks + "░" * empty_blocks
            embed.add_field(name="Progress Bar", value=f"`{progress_bar}` {progress_percent:.1f}%", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="🏆 View the server XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show server XP leaderboard"""
        await interaction.response.defer()
        
        # Get top 10 users by XP
        cursor = self.bot.db.leveling.find(
            {"guild_id": interaction.guild.id}
        ).sort("xp", -1).limit(10)
        
        users = await cursor.to_list(length=10)
        
        if not users:
            embed = EmbedBuilder.create(
                title="🏆 XP Leaderboard",
                description="No one has earned XP yet! Start chatting to gain XP!",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = EmbedBuilder.create(
            title="🏆 XP Leaderboard",
            description="Top members by XP in this server!",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        
        leaderboard_text = ""
        for i, user_data in enumerate(users, 1):
            try:
                user = self.bot.get_user(user_data["user_id"])
                if user:
                    level = self.calculate_level(user_data["xp"])
                    
                    if i == 1:
                        emoji = "🥇"
                    elif i == 2:
                        emoji = "🥈"
                    elif i == 3:
                        emoji = "🥉"
                    else:
                        emoji = f"{i}."
                    
                    leaderboard_text += f"{emoji} **{user.display_name}** - Level {level} ({user_data['xp']:,} XP)\n"
            except:
                continue
        
        if leaderboard_text:
            embed.add_field(name="Rankings", value=leaderboard_text, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="level-toggle", description="⚙️ Toggle XP system for this server")
    async def level_toggle(self, interaction: discord.Interaction):
        """Toggle XP system on/off"""
        if not interaction.user.guild_permissions.manage_guild:
            embed = EmbedBuilder.error("You need Manage Server permission to toggle the XP system!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get current setting
        server_data = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id})
        current_setting = server_data.get("leveling_enabled", True) if server_data else True
        
        # Toggle setting
        new_setting = not current_setting
        
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"leveling_enabled": new_setting}},
            upsert=True
        )
        
        status = "enabled" if new_setting else "disabled"
        embed = EmbedBuilder.success(f"XP system has been **{status}** for this server!")
        
        if new_setting:
            embed.add_field(
                name="How it works",
                value="Members gain 15-25 XP per message (1 minute cooldown)\nUse `/rank` to check levels and `/leaderboard` to see top members",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="reset-levels", description="🗑️ Reset all XP data for this server")
    async def reset_levels(self, interaction: discord.Interaction):
        """Reset all leveling data for the server"""
        if not interaction.user.guild_permissions.administrator:
            embed = EmbedBuilder.error("You need Administrator permission to reset XP data!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Count current data
        count = await self.bot.db.leveling.count_documents({"guild_id": interaction.guild.id})
        
        if count == 0:
            embed = EmbedBuilder.error("There is no XP data to reset!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create confirmation view
        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.confirmed = False
            
            @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.red)
            async def confirm(self, interaction, button):
                self.confirmed = True
                await interaction.response.defer()
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction, button):
                await interaction.response.defer()
                self.stop()
        
        embed = EmbedBuilder.create(
            title="🗑️ Reset XP Data",
            description=f"⚠️ **WARNING** ⚠️\n\nThis will permanently delete XP data for {count} members!\n\n**This action cannot be undone!**",
            color=discord.Color.red()
        )
        
        view = ConfirmView()
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        
        if view.confirmed:
          result = await self.bot.db.leveling.delete_many({"guild_id": interaction.guild.id})
            embed = EmbedBuilder.success(f"Reset complete! Deleted XP data for {result.deleted_count} members.")
        else:
            embed = EmbedBuilder.create(
                title="Cancelled",
                description="XP reset cancelled.",
                color=discord.Color.blue()
            )
        
        await interaction.edit_original_response(embed=embed, view=None)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award XP for messages"""
        # Ignore bots
        if message.author.bot:
            return
        
        # Only in guilds
        if not message.guild:
            return
        
        # Check if leveling is enabled
        server_data = await self.bot.db.server_settings.find_one({"guild_id": message.guild.id})
        if server_data and not server_data.get("leveling_enabled", True):
            return
        
        # Check cooldown (1 minute)
        user_key = f"{message.author.id}_{message.guild.id}"
        now = datetime.utcnow()
        
        if user_key in self.xp_cooldowns:
            if now - self.xp_cooldowns[user_key] < timedelta(minutes=1):
                return
        
        self.xp_cooldowns[user_key] = now
        
        # Award XP (15-25 per message)
        xp_gained = random.randint(15, 25)
        
        # Get user data before update
        old_data = await self.get_user_data(message.author.id, message.guild.id)
        old_level = self.calculate_level(old_data["xp"])
        
        # Add XP
        new_data = await self.add_xp(message.author.id, message.guild.id, xp_gained)
        new_level = self.calculate_level(new_data["xp"])
        
        # Check for level up
        if new_level > old_level:
            embed = EmbedBuilder.create(
                title="🎉 Level Up!",
                description=f"Congratulations {message.author.mention}! You reached **Level {new_level}**!",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            embed.add_field(name="Total XP", value=f"{new_data['xp']:,}", inline=True)
            embed.add_field(name="Messages Sent", value=f"{new_data['messages']:,}", inline=True)
            
            # Check for level rewards (placeholder)
            if new_level % 10 == 0:  # Every 10 levels
                embed.add_field(
                    name="🎁 Milestone Reward!",
                    value=f"You've reached level {new_level}! Special rewards coming soon!",
                    inline=False
                )
            
            try:
                await message.channel.send(embed=embed, delete_after=10)
            except:
                pass  # Fail silently if can't send message


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Leveling(bot))
