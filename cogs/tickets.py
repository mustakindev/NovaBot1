"""
Tickets cog for Nova bot
Provides support ticket system functionality.
"""

import asyncio
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class TicketView(discord.ui.View):
    """Persistent view for ticket management"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create a new support ticket"""
        # Check if user already has a ticket
        existing_channel = discord.utils.get(
            interaction.guild.channels,
            name=f"ticket-{interaction.user.id}"
        )
        
        if existing_channel:
            embed = EmbedBuilder.error(f"You already have an open ticket: {existing_channel.mention}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get ticket category
            ticket_data = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id})
            category = None
            
            if ticket_data and "ticket_category" in ticket_data:
                category = interaction.guild.get_channel(ticket_data["ticket_category"])
            
            # Create ticket channel
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True,
                    embed_links=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True,
                    embed_links=True,
                    attach_files=True
                )
            }
            
            # Add support role permissions if configured
            if ticket_data and "support_role" in ticket_data:
                support_role = interaction.guild.get_role(ticket_data["support_role"])
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True
                    )
            
            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.id}",
                category=category,
                overwrites=overwrites,
                topic=f"Support ticket for {interaction.user.display_name}"
            )
            
            # Store ticket in database
            await self.bot.db.tickets.insert_one({
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "user_id": interaction.user.id,
                "created_at": datetime.utcnow(),
                "status": "open"
            })
            
            # Create ticket embed
            embed = EmbedBuilder.create(
                title="🎫 Support Ticket",
                description=f"Hello {interaction.user.mention}! Welcome to your support ticket.\n\nPlease describe your issue and our staff will assist you shortly.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Created by", value=interaction.user.mention, inline=True)
            embed.add_field(name="Created at", value=f"<t:{int(datetime.utcnow().timestamp())}:F>", inline=True)
            
            # Create ticket control view
            ticket_controls = TicketControlView(self.bot)
            message = await channel.send(embed=embed, view=ticket_controls)
            
            # Pin the message
            await message.pin()
            
            success_embed = EmbedBuilder.success(f"Ticket created! {channel.mention}")
            await interaction.followup.send(embed=success_embed, ephemeral=True)
            
            # Log ticket creation
            await self._log_ticket_action(interaction.guild, "Ticket Created", interaction.user, channel)
            
        except Exception as e:
            error_embed = EmbedBuilder.error(f"Failed to create ticket: {str(e)}")
            await interaction.followup.send(embed=error_embed, ephemeral=True)
    
    async def _log_ticket_action(self, guild: discord.Guild, action: str, user: discord.Member, channel: discord.TextChannel):
        """Log ticket actions to log channel"""
        try:
            log_data = await self.bot.db.server_settings.find_one({"guild_id": guild.id})
            if not log_data or "log_channel" not in log_data:
                return
            
            log_channel = guild.get_channel(log_data["log_channel"])
            if not log_channel:
                return
            
            embed = EmbedBuilder.create(
                title=f"🎫 {action}",
                color=discord.Color.blue()
            )
            embed.add_field(name="User", value=user.mention, inline=True)
            embed.add_field(name="Channel", value=channel.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            
            await log_channel.send(embed=embed)
        except:
            pass


class TicketControlView(discord.ui.View):
    """Control panel for individual tickets"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="🔒 Close", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Close the ticket"""
        # Check if user has permission to close tickets
        ticket_data = await self.bot.db.tickets.find_one({"channel_id": interaction.channel.id})
        
        if not ticket_data:
            embed = EmbedBuilder.error("This doesn't appear to be a valid ticket channel!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Allow ticket creator, support staff, or admins to close
        can_close = (
            interaction.user.id == ticket_data["user_id"] or
            interaction.user.guild_permissions.manage_channels or
            interaction.user.guild_permissions.administrator
        )
        
        # Check support role
        if not can_close:
            server_settings = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id})
            if server_settings and "support_role" in server_settings:
                support_role = interaction.guild.get_role(server_settings["support_role"])
                if support_role and support_role in interaction.user.roles:
                    can_close = True
        
        if not can_close:
            embed = EmbedBuilder.error("You don't have permission to close this ticket!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Confirmation embed
        embed = EmbedBuilder.create(
            title="🔒 Close Ticket",
            description="Are you sure you want to close this ticket?\nThe channel will be deleted in 10 seconds.",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
        
        # Update database
        await self.bot.db.tickets.update_one(
            {"channel_id": interaction.channel.id},
            {
                "$set": {
                    "status": "closed",
                    "closed_by": interaction.user.id,
                    "closed_at": datetime.utcnow()
                }
            }
        )
        
        # Log closure
        try:
            user = self.bot.get_user(ticket_data["user_id"])
            await self._log_ticket_action(interaction.guild, "Ticket Closed", interaction.user, interaction.channel, user)
        except:
            pass
        
        # Wait and delete
        await asyncio.sleep(10)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
    
    @discord.ui.button(label="🏷️ Claim", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim the ticket"""
        # Check if user has permission to claim tickets
        server_settings = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id})
        can_claim = interaction.user.guild_permissions.manage_channels
        
        if server_settings and "support_role" in server_settings:
            support_role = interaction.guild.get_role(server_settings["support_role"])
            if support_role and support_role in interaction.user.roles:
                can_claim = True
        
        if not can_claim:
            embed = EmbedBuilder.error("You don't have permission to claim tickets!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update ticket in database
        await self.bot.db.tickets.update_one(
            {"channel_id": interaction.channel.id},
            {
                "$set": {
                    "claimed_by": interaction.user.id,
                    "claimed_at": datetime.utcnow()
                }
            }
        )
        
        embed = EmbedBuilder.success(f"Ticket claimed by {interaction.user.mention}!")
        await interaction.response.send_message(embed=embed)
        
        # Update channel topic
        await interaction.channel.edit(topic=f"Ticket claimed by {interaction.user.display_name}")
    
    async def _log_ticket_action(self, guild: discord.Guild, action: str, staff: discord.Member, channel: discord.TextChannel, user: discord.Member = None):
        """Log ticket actions"""
        try:
            log_data = await self.bot.db.server_settings.find_one({"guild_id": guild.id})
            if not log_data or "log_channel" not in log_data:
                return
            
            log_channel = guild.get_channel(log_data["log_channel"])
            if not log_channel:
                return
            
            embed = EmbedBuilder.create(
                title=f"🎫 {action}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Staff", value=staff.mention, inline=True)
            embed.add_field(name="Channel", value=channel.name, inline=True)
            if user:
                embed.add_field(name="Ticket Owner", value=user.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            
            await log_channel.send(embed=embed)
        except:
            pass


class Tickets(commands.Cog):
    """Support ticket system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Add persistent views
        self.bot.add_view(TicketView(bot))
        self.bot.add_view(TicketControlView(bot))
    
    @app_commands.command(name="ticket-setup", description="🎫 Setup the ticket system")
    @app_commands.describe(
        channel="Channel to send the ticket creation message",
        category="Category for ticket channels (optional)",
        support_role="Role that can manage tickets (optional)"
    )
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        category: Optional[discord.CategoryChannel] = None,
        support_role: Optional[discord.Role] = None
    ):
        """Setup the ticket system"""
        if not interaction.user.guild_permissions.manage_guild:
            embed = EmbedBuilder.error("You need Manage Server permission to setup tickets!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update server settings
        settings = {}
        if category:
            settings["ticket_category"] = category.id
        if support_role:
            settings["support_role"] = support_role.id
        
        if settings:
            await self.bot.db.server_settings.update_one(
                {"guild_id": interaction.guild.id},
                {"$set": settings},
                upsert=True
            )
        
        # Create ticket creation embed
        embed = EmbedBuilder.create(
            title="🎫 Support Tickets",
            description="Need help? Create a support ticket!\n\nClick the button below to open a private channel where our staff can assist you.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="How it works:",
            value="• Click 'Create Ticket'\n• A private channel will be created\n• Explain your issue\n• Staff will help you\n• Ticket will be closed when resolved",
            inline=False
        )
        
        view = TicketView(self.bot)
        await channel.send(embed=embed, view=view)
        
        success_embed = EmbedBuilder.success(f"Ticket system setup complete!\nTicket creation message sent to {channel.mention}")
        if category:
            success_embed.add_field(name="Ticket Category", value=category.mention, inline=True)
        if support_role:
            success_embed.add_field(name="Support Role", value=support_role.mention, inline=True)
        
        await interaction.response.send_message(embed=success_embed)
    
    @app_commands.command(name="ticket-close", description="🔒 Close the current ticket")
    async def ticket_close(self, interaction: discord.Interaction):
        """Close the current ticket (alternative to button)"""
        ticket_data = await self.bot.db.tickets.find_one({"channel_id": interaction.channel.id})
        
        if not ticket_data:
            embed = EmbedBuilder.error("This command can only be used in ticket channels!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check permissions (same logic as button)
        can_close = (
            interaction.user.id == ticket_data["user_id"] or
            interaction.user.guild_permissions.manage_channels or
            interaction.user.guild_permissions.administrator
        )
        
        if not can_close:
            server_settings = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id})
            if server_settings and "support_role" in server_settings:
                support_role = interaction.guild.get_role(server_settings["support_role"])
                if support_role and support_role in interaction.user.roles:
                    can_close = True
        
        if not can_close:
            embed = EmbedBuilder.error("You don't have permission to close this ticket!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Close ticket
        embed = EmbedBuilder.create(
            title="🔒 Closing Ticket",
            description="This ticket will be closed and deleted in 10 seconds.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        
        # Update database
        await self.bot.db.tickets.update_one(
            {"channel_id": interaction.channel.id},
            {
                "$set": {
                    "status": "closed",
                    "closed_by": interaction.user.id,
                    "closed_at": datetime.utcnow()
                }
            }
        )
        
        await asyncio.sleep(10)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Tickets(bot))
