"""
Moderation cog for Nova bot
Provides server moderation commands and utilities.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder
from utils.checks import has_permissions


class Moderation(commands.Cog):
    """Moderation commands for server management"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="ban", description="🔨 Ban a user from the server")
    @app_commands.describe(
        user="The user to ban",
        reason="Reason for the ban",
        delete_days="Days of messages to delete (0-7)"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided",
        delete_days: Optional[int] = 0
    ):
        """Ban a user from the server"""
        if not interaction.user.guild_permissions.ban_members:
            embed = EmbedBuilder.error("You don't have permission to ban members!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            embed = EmbedBuilder.error("You cannot ban someone with equal or higher role!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Try to DM user before ban
            try:
                dm_embed = EmbedBuilder.create(
                    title="You have been banned",
                    description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason}",
                    color=discord.Color.red()
                )
                await user.send(embed=dm_embed)
            except:
                pass  # User has DMs disabled
            
            await user.ban(reason=reason, delete_message_days=min(delete_days, 7))
            
            # Log the action
            await self._log_action(interaction, "Ban", user, reason)
            
            embed = EmbedBuilder.success(f"Successfully banned {user.mention}")
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            embed = EmbedBuilder.error("I don't have permission to ban this user!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = EmbedBuilder.error(f"Failed to ban user: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="kick", description="👢 Kick a user from the server")
    @app_commands.describe(
        user="The user to kick",
        reason="Reason for the kick"
    )
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """Kick a user from the server"""
        if not interaction.user.guild_permissions.kick_members:
            embed = EmbedBuilder.error("You don't have permission to kick members!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            embed = EmbedBuilder.error("You cannot kick someone with equal or higher role!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Try to DM user before kick
            try:
                dm_embed = EmbedBuilder.create(
                    title="You have been kicked",
                    description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason}",
                    color=discord.Color.orange()
                )
                await user.send(embed=dm_embed)
            except:
                pass
            
            await user.kick(reason=reason)
            
            # Log the action
            await self._log_action(interaction, "Kick", user, reason)
            
            embed = EmbedBuilder.success(f"Successfully kicked {user.mention}")
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            embed = EmbedBuilder.error("I don't have permission to kick this user!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = EmbedBuilder.error(f"Failed to kick user: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="mute", description="🔇 Timeout a user")
    @app_commands.describe(
        user="The user to timeout",
        duration="Duration in minutes (max 40320 - 28 days)",
        reason="Reason for the timeout"
    )
    async def mute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: int,
        reason: Optional[str] = "No reason provided"
    ):
        """Timeout a user (Discord's built-in timeout feature)"""
        if not interaction.user.guild_permissions.moderate_members:
            embed = EmbedBuilder.error("You don't have permission to timeout members!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            embed = EmbedBuilder.error("You cannot timeout someone with equal or higher role!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if duration > 40320:  # Discord's max timeout
            embed = EmbedBuilder.error("Maximum timeout duration is 40320 minutes (28 days)!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            timeout_until = datetime.utcnow() + timedelta(minutes=duration)
            await user.timeout(timeout_until, reason=reason)
            
            # Log the action
            await self._log_action(interaction, "Timeout", user, f"{reason} (Duration: {duration} minutes)")
            
            embed = EmbedBuilder.success(f"Successfully timed out {user.mention} for {duration} minutes")
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            embed = EmbedBuilder.error("I don't have permission to timeout this user!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = EmbedBuilder.error(f"Failed to timeout user: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="unmute", description="🔊 Remove timeout from a user")
    @app_commands.describe(
        user="The user to remove timeout from",
        reason="Reason for removing timeout"
    )
    async def unmute(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """Remove timeout from a user"""
        if not interaction.user.guild_permissions.moderate_members:
            embed = EmbedBuilder.error("You don't have permission to manage timeouts!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not user.is_timed_out():
            embed = EmbedBuilder.error("This user is not currently timed out!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await user.timeout(None, reason=reason)
            
            # Log the action
            await self._log_action(interaction, "Timeout Removed", user, reason)
            
            embed = EmbedBuilder.success(f"Successfully removed timeout from {user.mention}")
            embed.add_field(name="Reason", value=reason, inline=False)
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            embed = EmbedBuilder.error("I don't have permission to manage this user's timeout!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = EmbedBuilder.error(f"Failed to remove timeout: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="warn", description="⚠️ Warn a user")
    @app_commands.describe(
        user="The user to warn",
        reason="Reason for the warning"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: Optional[str] = "No reason provided"
    ):
        """Warn a user"""
        if not interaction.user.guild_permissions.moderate_members:
            embed = EmbedBuilder.error("You don't have permission to warn members!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            # Store warning in database
            await self.bot.db.warnings.insert_one({
                "guild_id": interaction.guild.id,
                "user_id": user.id,
                "moderator_id": interaction.user.id,
                "reason": reason,
                "timestamp": datetime.utcnow()
            })
            
            # Get warning count
            warning_count = await self.bot.db.warnings.count_documents({
                "guild_id": interaction.guild.id,
                "user_id": user.id
            })
            
            # Try to DM user
            try:
                dm_embed = EmbedBuilder.create(
                    title="You received a warning",
                    description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason}\n**Total Warnings:** {warning_count}",
                    color=discord.Color.orange()
                )
                await user.send(embed=dm_embed)
            except:
                pass
            
            # Log the action
            await self._log_action(interaction, "Warning", user, f"{reason} (Total: {warning_count})")
            
            embed = EmbedBuilder.success(f"Successfully warned {user.mention}")
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            embed = EmbedBuilder.error(f"Failed to warn user: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="clear", description="🗑️ Delete multiple messages")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user"
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: Optional[discord.Member] = None
    ):
        """Delete multiple messages from the channel"""
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedBuilder.error("You don't have permission to manage messages!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if amount < 1 or amount > 100:
            embed = EmbedBuilder.error("Amount must be between 1 and 100!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            def check(message):
                return user is None or message.author == user
            
            deleted = await interaction.channel.purge(limit=amount, check=check)
            
            embed = EmbedBuilder.success(f"Successfully deleted {len(deleted)} messages")
            if user:
                embed.add_field(name="User", value=user.mention, inline=True)
            
            # Send response and delete it after a few seconds
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            # Log the action
            log_reason = f"Cleared {len(deleted)} messages"
            if user:
                log_reason += f" from {user}"
            await self._log_action(interaction, "Clear", None, log_reason)
            
        except discord.Forbidden:
            embed = EmbedBuilder.error("I don't have permission to delete messages!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            embed = EmbedBuilder.error(f"Failed to clear messages: {str(e)}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def _log_action(
        self,
        interaction: discord.Interaction,
        action: str,
        target: Optional[discord.Member],
        reason: str
    ):
        """Log moderation action to the logging channel"""
        try:
            # Get logging channel from database
            log_data = await self.bot.db.server_settings.find_one({
                "guild_id": interaction.guild.id
            })
            
            if not log_data or "log_channel" not in log_data:
                return
            
            log_channel = interaction.guild.get_channel(log_data["log_channel"])
            if not log_channel:
                return
            
            embed = EmbedBuilder.create(
                title=f"Moderation Action: {action}",
                color=discord.Color.orange()
            )
            
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            if target:
                embed.add_field(name="Target", value=target.mention, inline=True)
            embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.timestamp = datetime.utcnow()
            
            await log_channel.send(embed=embed)
        except:
            pass  # Fail silently if logging fails


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Moderation(bot))
