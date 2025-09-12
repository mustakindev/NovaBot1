"""
Giveaways cog for Nova bot
Provides giveaway management functionality.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

from utils.embeds import EmbedBuilder


class GiveawayView(discord.ui.View):
    """Persistent view for giveaway participation"""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
    
    @discord.ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.green, custom_id="enter_giveaway")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Enter the giveaway"""
        # Get giveaway data
        giveaway = await self.bot.db.giveaways.find_one({
            "message_id": interaction.message.id,
            "guild_id": interaction.guild.id,
            "status": "active"
        })
        
        if not giveaway:
            embed = EmbedBuilder.error("This giveaway is no longer active!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if giveaway has ended
        if datetime.utcnow() > giveaway["end_time"]:
            embed = EmbedBuilder.error("This giveaway has already ended!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if user is already entered
        if interaction.user.id in giveaway.get("entries", []):
            embed = EmbedBuilder.error("You're already entered in this giveaway!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check requirements (placeholder for role requirements, etc.)
        # This could be extended to check for required roles, server boosts, etc.
        
        # Add user to entries
        await self.bot.db.giveaways.update_one(
            {"message_id": interaction.message.id},
            {"$push": {"entries": interaction.user.id}}
        )
        
        # Update giveaway embed
        await self.update_giveaway_embed(interaction.message, giveaway)
        
        embed = EmbedBuilder.success("🎉 You've entered the giveaway! Good luck!")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def update_giveaway_embed(self, message: discord.Message, giveaway: dict):
        """Update the giveaway embed with current entry count"""
        try:
            # Get updated data
            updated_giveaway = await self.bot.db.giveaways.find_one({"_id": giveaway["_id"]})
            entry_count = len(updated_giveaway.get("entries", []))
            
            embed = EmbedBuilder.create(
                title="🎉 Giveaway!",
                description=f"**Prize:** {giveaway['prize']}\n**Hosted by:** <@{giveaway['host_id']}>",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            
            embed.add_field(name="Ends", value=f"<t:{int(giveaway['end_time'].timestamp())}:R>", inline=True)
            embed.add_field(name="Winners", value=str(giveaway['winner_count']), inline=True)
            embed.add_field(name="Entries", value=str(entry_count), inline=True)
            
            embed.set_footer(text="Click the button below to enter!")
            
            await message.edit(embed=embed)
        except:
            pass


class Giveaways(commands.Cog):
    """Giveaway management system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(GiveawayView(bot))
        self.check_giveaways.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.check_giveaways.cancel()
    
    @tasks.loop(minutes=1)
    async def check_giveaways(self):
        """Check for ended giveaways"""
        try:
            # Find ended giveaways
            ended_giveaways = await self.bot.db.giveaways.find({
                "status": "active",
                "end_time": {"$lte": datetime.utcnow()}
            }).to_list(length=None)
            
            for giveaway in ended_giveaways:
                await self.end_giveaway(giveaway)
        except Exception as e:
            print(f"Error checking giveaways: {e}")
    
    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait until bot is ready"""
        await self.bot.wait_until_ready()
    
    async def end_giveaway(self, giveaway: dict):
        """End a giveaway and pick winners"""
        try:
            guild = self.bot.get_guild(giveaway["guild_id"])
            if not guild:
                return
            
            channel = guild.get_channel(giveaway["channel_id"])
            if not channel:
                return
            
            try:
                message = await channel.fetch_message(giveaway["message_id"])
            except:
                # Message was deleted
                await self.bot.db.giveaways.update_one(
                    {"_id": giveaway["_id"]},
                    {"$set": {"status": "ended"}}
                )
                return
            
            entries = giveaway.get("entries", [])
            winner_count = min(giveaway["winner_count"], len(entries))
            
            if winner_count == 0:
                # No entries
                embed = EmbedBuilder.create(
                    title="🎉 Giveaway Ended",
                    description=f"**Prize:** {giveaway['prize']}\n\n❌ No valid entries! No winners this time.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Hosted by", value=f"<@{giveaway['host_id']}>", inline=True)
            else:
                # Pick winners
                winners = random.sample(entries, winner_count)
                winner_mentions = [f"<@{winner_id}>" for winner_id in winners]
                
                embed = EmbedBuilder.create(
                    title="🎉 Giveaway Ended",
                    description=f"**Prize:** {giveaway['prize']}\n\n🏆 **Winner{'s' if len(winners) > 1 else ''}:** {', '.join(winner_mentions)}",
                    color=discord.Color.from_rgb(255, 215, 0)
                )
                embed.add_field(name="Hosted by", value=f"<@{giveaway['host_id']}>", inline=True)
                embed.add_field(name="Total Entries", value=str(len(entries)), inline=True)
                
                # Store winners
                await self.bot.db.giveaways.update_one(
                    {"_id": giveaway["_id"]},
                    {"$set": {"winners": winners}}
                )
                
                # Send congratulations message
                congrats_embed = EmbedBuilder.create(
                    title="🎊 Congratulations!",
                    description=f"You won the giveaway for **{giveaway['prize']}**!\n\nPlease contact <@{giveaway['host_id']}> to claim your prize!",
                    color=discord.Color.from_rgb(255, 215, 0)
                )
                
                for winner_id in winners:
                    try:
                        winner = guild.get_member(winner_id)
                        if winner:
                            await winner.send(embed=congrats_embed)
                    except:
                        pass
            
            # Update original message
            await message.edit(embed=embed, view=None)
            
            # Mark as ended in database
            await self.bot.db.giveaways.update_one(
                {"_id": giveaway["_id"]},
                {"$set": {"status": "ended", "ended_at": datetime.utcnow()}}
            )
            
        except Exception as e:
            print(f"Error ending giveaway: {e}")
    
    @app_commands.command(name="gstart", description="🎉 Start a giveaway")
    @app_commands.describe(
        prize="What you're giving away",
        duration="How long the giveaway runs (e.g., '1h', '2d', '30m')",
        winners="Number of winners (default: 1)",
        channel="Channel to post giveaway in (optional)"
    )
    async def giveaway_start(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: str,
        winners: int = 1,
        channel: Optional[discord.TextChannel] = None
    ):
        """Start a new giveaway"""
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedBuilder.error("You need Manage Messages permission to start giveaways!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if winners < 1 or winners > 20:
            embed = EmbedBuilder.error("Winner count must be between 1 and 20!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Parse duration
        try:
            duration_seconds = self.parse_duration(duration)
        except ValueError as e:
            embed = EmbedBuilder.error(str(e))
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if duration_seconds < 60:  # Minimum 1 minute
            embed = EmbedBuilder.error("Giveaway duration must be at least 1 minute!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if duration_seconds > 2419200:  # Maximum 28 days
            embed = EmbedBuilder.error("Giveaway duration cannot exceed 28 days!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        target_channel = channel if channel else interaction.channel
        
        if not target_channel.permissions_for(interaction.guild.me).send_messages:
            embed = EmbedBuilder.error("I don't have permission to send messages in that channel!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Calculate end time
        end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        # Create giveaway embed
        embed = EmbedBuilder.create(
            title="🎉 Giveaway!",
            description=f"**Prize:** {prize}\n**Hosted by:** {interaction.user.mention}",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        
        embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
        embed.add_field(name="Winners", value=str(winners), inline=True)
        embed.add_field(name="Entries", value="0", inline=True)
        
        embed.set_footer(text="Click the button below to enter!")
        
        view = GiveawayView(self.bot)
        
        await interaction.response.send_message("Giveaway starting...", ephemeral=True)
        message = await target_channel.send(embed=embed, view=view)
        
        # Store in database
        await self.bot.db.giveaways.insert_one({
            "guild_id": interaction.guild.id,
            "channel_id": target_channel.id,
            "message_id": message.id,
            "host_id": interaction.user.id,
            "prize": prize,
            "winner_count": winners,
            "start_time": datetime.utcnow(),
            "end_time": end_time,
            "entries": [],
            "status": "active"
        })
        
        success_embed = EmbedBuilder.success(f"Giveaway started in {target_channel.mention}!")
        success_embed.add_field(name="Prize", value=prize, inline=True)
        success_embed.add_field(name="Duration", value=duration, inline=True)
        success_embed.add_field(name="Winners", value=str(winners), inline=True)
        
        await interaction.edit_original_response(content=None, embed=success_embed)
    
    @app_commands.command(name="gend", description="🏁 End a giveaway early")
    @app_commands.describe(message_id="Message ID of the giveaway to end")
    async def giveaway_end(self, interaction: discord.Interaction, message_id: str):
        """End a giveaway early"""
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedBuilder.error("You need Manage Messages permission to end giveaways!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            message_id = int(message_id)
        except ValueError:
            embed = EmbedBuilder.error("Invalid message ID!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        giveaway = await self.bot.db.giveaways.find_one({
            "message_id": message_id,
            "guild_id": interaction.guild.id,
            "status": "active"
        })
        
        if not giveaway:
            embed = EmbedBuilder.error("No active giveaway found with that message ID!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.send_message("Ending giveaway...", ephemeral=True)
        
        # End the giveaway
        await self.end_giveaway(giveaway)
        
        embed = EmbedBuilder.success("Giveaway ended successfully!")
        await interaction.edit_original_response(embed=embed)
    
    @app_commands.command(name="greroll", description="🔄 Reroll giveaway winners")
    @app_commands.describe(message_id="Message ID of the giveaway to reroll")
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str):
        """Reroll giveaway winners"""
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedBuilder.error("You need Manage Messages permission to reroll giveaways!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            message_id = int(message_id)
        except ValueError:
            embed = EmbedBuilder.error("Invalid message ID!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        giveaway = await self.bot.db.giveaways.find_one({
            "message_id": message_id,
            "guild_id": interaction.guild.id,
            "status": "ended"
        })
        
        if not giveaway:
            embed = EmbedBuilder.error("No ended giveaway found with that message ID!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        entries = giveaway.get("entries", [])
        winner_count = min(giveaway["winner_count"], len(entries))
        
        if winner_count == 0:
            embed = EmbedBuilder.error("Cannot reroll - no entries in this giveaway!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Pick new winners
        new_winners = random.sample(entries, winner_count)
        winner_mentions = [f"<@{winner_id}>" for winner_id in new_winners]
        
        # Update database
        await self.bot.db.giveaways.update_one(
            {"_id": giveaway["_id"]},
            {"$set": {"winners": new_winners, "rerolled": True}}
        )
        
        embed = EmbedBuilder.create(
            title="🔄 Giveaway Rerolled!",
            description=f"**Prize:** {giveaway['prize']}\n\n🏆 **New Winner{'s' if len(new_winners) > 1 else ''}:** {', '.join(winner_mentions)}",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        
        await interaction.response.send_message(embed=embed)
    
    def parse_duration(self, duration_str: str) -> int:
        """Parse duration string into seconds"""
        duration_str = duration_str.lower().strip()
        
        # Extract number and unit
        import re
        match = re.match(r'^(\d+)([smhdw])$', duration_str)
        if not match:
            raise ValueError("Invalid duration format! Use: 30s, 5m, 2h, 3d, 1w")
        
        amount, unit = match.groups()
        amount = int(amount)
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        return amount * multipliers[unit]


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Giveaways(bot))
