"""
Logging cog for Nova bot
Provides server event logging functionality.
"""

from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class Logging(commands.Cog):
    """Server event logging system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="log-channel", description="📋 Set the logging channel")
    @app_commands.describe(channel="Channel to send log messages to")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the logging channel"""
        if not interaction.user.guild_permissions.manage_guild:
            embed = EmbedBuilder.error("You need Manage Server permission to set the log channel!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not channel.permissions_for(interaction.guild.me).send_messages:
            embed = EmbedBuilder.error("I don't have permission to send messages in that channel!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update database
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"log_channel": channel.id}},
            upsert=True
        )
        
        embed = EmbedBuilder.success(f"Log channel set to {channel.mention}!")
        embed.add_field(
            name="Events Logged",
            value="• Member joins/leaves\n• Message edits/deletes\n• Moderation actions\n• Role changes\n• Channel changes",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Send test message to log channel
        test_embed = EmbedBuilder.create(
            title="📋 Logging Enabled",
            description="This channel has been set as the server log channel.",
            color=discord.Color.green()
        )
        test_embed.add_field(name="Set by", value=interaction.user.mention, inline=True)
        test_embed.timestamp = datetime.utcnow()
        
        await channel.send(embed=test_embed)
    
    @app_commands.command(name="log-disable", description="❌ Disable server logging")
    async def disable_logging(self, interaction: discord.Interaction):
        """Disable server logging"""
        if not interaction.user.guild_permissions.manage_guild:
            embed = EmbedBuilder.error("You need Manage Server permission to disable logging!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        result = await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$unset": {"log_channel": ""}}
        )
        
        if result.modified_count > 0:
            embed = EmbedBuilder.success("Server logging has been disabled!")
        else:
            embed = EmbedBuilder.error("Logging was not enabled on this server!")
        
        await interaction.response.send_message(embed=embed)
    
    async def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get the log channel for a guild"""
        try:
            log_data = await self.bot.db.server_settings.find_one({"guild_id": guild.id})
            if log_data and "log_channel" in log_data:
                return guild.get_channel(log_data["log_channel"])
        except:
            pass
        return None
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Log member joins"""
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        embed = EmbedBuilder.create(
            title="📥 Member Joined",
            description=f"**{member}** joined the server",
            color=discord.Color.green()
        )
        
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Log member leaves"""
        log_channel = await self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        embed = EmbedBuilder.create(
            title="📤 Member Left",
            description=f"**{member}** left the server",
            color=discord.Color.red()
        )
        
        embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
        if member.joined_at:
            embed.add_field(name="Joined", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Member Count", value=str(member.guild.member_count), inline=True)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Log message edits"""
        # Ignore bot messages
        if before.author.bot:
            return
        
        # Ignore if content didn't change
        if before.content == after.content:
            return
        
        log_channel = await self.get_log_channel(before.guild)
        if not log_channel:
            return
        
        embed = EmbedBuilder.create(
            title="📝 Message Edited",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Author", value=before.author.mention, inline=True)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Message ID", value=str(before.id), inline=True)
        
        # Truncate long messages
        before_content = before.content[:1000] + "..." if len(before.content) > 1000 else before.content
        after_content = after.content[:1000] + "..." if len(after.content) > 1000 else after.content
        
        embed.add_field(name="Before", value=before_content or "*No content*", inline=False)
        embed.add_field(name="After", value=after_content or "*No content*", inline=False)
        
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Log message deletions"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Ignore if in DMs
        if not message.guild:
            return
        
        log_channel = await self.get_log_channel(message.guild)
        if not log_channel:
            return
        
        embed = EmbedBuilder.create(
            title="🗑️ Message Deleted",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Message ID", value=str(message.id), inline=True)
        
        # Truncate long messages
        content = message.content[:1000] + "..." if len(message.content) > 1000 else message.content
        embed.add_field(name="Content", value=content or "*No content*", inline=False)
        
        # Add attachment info if any
        if message.attachments:
            attachment_names = [att.filename for att in message.attachments]
            embed.add_field(name="Attachments", value=", ".join(attachment_names), inline=False)
        
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Log member updates (roles, nickname)"""
        log_channel = await self.get_log_channel(before.guild)
        if not log_channel:
            return
        
        # Check for role changes
        if before.roles != after.roles:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            if added_roles or removed_roles:
                embed = EmbedBuilder.create(
                    title="🎭 Member Roles Updated",
                    color=discord.Color.blue()
                )
                
                embed.add_field(name="Member", value=after.mention, inline=True)
                
                if added_roles:
                    role_list = ", ".join([role.mention for role in added_roles])
                    embed.add_field(name="Roles Added", value=role_list, inline=False)
                
                if removed_roles:
                    role_list = ", ".join([role.mention for role in removed_roles])
                    embed.add_field(name="Roles Removed", value=role_list, inline=False)
                
                embed.timestamp = datetime.utcnow()
                
                try:
                    await log_channel.send(embed=embed)
                except:
                    pass
        
        # Check for nickname changes
        if before.nick != after.nick:
            embed = EmbedBuilder.create(
                title="📝 Nickname Changed",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Member", value=after.mention, inline=True)
            embed.add_field(name="Before", value=before.nick or before.name, inline=True)
            embed.add_field(name="After", value=after.nick or after.name, inline=True)
            
            embed.timestamp = datetime.utcnow()
            
            try:
                await log_channel.send(embed=embed)
            except:
                pass
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Log channel creation"""
        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel:
            return
        
        embed = EmbedBuilder.create(
            title="📁 Channel Created",
            description=f"**{channel.name}** was created",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Channel", value=channel.mention if hasattr(channel, 'mention') else channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Log channel deletion"""
        log_channel = await self.get_log_channel(channel.guild)
        if not log_channel or log_channel.id == channel.id:
            return
        
        embed = EmbedBuilder.create(
            title="🗑️ Channel Deleted",
            description=f"**{channel.name}** was deleted",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Channel Name", value=channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).title(), inline=True)
        embed.add_field(name="ID", value=str(channel.id), inline=True)
        
        if hasattr(channel, 'category') and channel.category:
            embed.add_field(name="Category", value=channel.category.name, inline=True)
        
        embed.timestamp = datetime.utcnow()
        
        try:
            await log_channel.send(embed=embed)
        except:
            pass


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Logging(bot))
