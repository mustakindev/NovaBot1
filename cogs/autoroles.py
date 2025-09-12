"""
Autoroles cog for Nova bot
Provides automatic role assignment functionality.
"""

from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class Autoroles(commands.Cog):
    """Automatic role assignment system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="autorole-add", description="➕ Add a role to be given to new members")
    @app_commands.describe(role="Role to automatically assign to new members")
    async def autorole_add(self, interaction: discord.Interaction, role: discord.Role):
        """Add an autorole"""
        if not interaction.user.guild_permissions.manage_roles:
            embed = EmbedBuilder.error("You need Manage Roles permission to use this command!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            embed = EmbedBuilder.error("You can't add roles equal to or higher than your highest role!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if role >= interaction.guild.me.top_role:
            embed = EmbedBuilder.error("I can't assign roles equal to or higher than my highest role!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if role.managed:
            embed = EmbedBuilder.error("I can't assign managed roles (bot roles, booster roles, etc.)!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if role is already an autorole
        existing = await self.bot.db.autoroles.find_one({
            "guild_id": interaction.guild.id,
            "role_id": role.id
        })
        
        if existing:
            embed = EmbedBuilder.error(f"{role.mention} is already an autorole!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Add to database
        await self.bot.db.autoroles.insert_one({
            "guild_id": interaction.guild.id,
            "role_id": role.id,
            "added_by": interaction.user.id
        })
        
        embed = EmbedBuilder.success(f"Added {role.mention} as an autorole!\nNew members will automatically receive this role.")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="autorole-remove", description="➖ Remove an autorole")
    @app_commands.describe(role="Role to remove from autoroles")
    async def autorole_remove(self, interaction: discord.Interaction, role: discord.Role):
        """Remove an autorole"""
        if not interaction.user.guild_permissions.manage_roles:
            embed = EmbedBuilder.error("You need Manage Roles permission to use this command!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if role is an autorole
        result = await self.bot.db.autoroles.delete_one({
            "guild_id": interaction.guild.id,
            "role_id": role.id
        })
        
        if result.deleted_count == 0:
            embed = EmbedBuilder.error(f"{role.mention} is not an autorole!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = EmbedBuilder.success(f"Removed {role.mention} from autoroles!")
        await interaction.response.send_message(embed=embed)

@app_commands.command(name="autorole-list", description="📋 List all autoroles")
    async def autorole_list(self, interaction: discord.Interaction):
        """List all autoroles for the server"""
        autoroles = await self.bot.db.autoroles.find({
            "guild_id": interaction.guild.id
        }).to_list(length=None)
        
        if not autoroles:
            embed = EmbedBuilder.create(
                title="📋 Autoroles",
                description="No autoroles configured!\nUse `/autorole-add` to add roles that will be given to new members.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        embed = EmbedBuilder.create(
            title="📋 Server Autoroles",
            description="Roles automatically given to new members:",
            color=discord.Color.blue()
        )
        
        role_list = ""
        valid_autoroles = []
        
        for autorole in autoroles:
            role = interaction.guild.get_role(autorole["role_id"])
            if role:
                role_list += f"• {role.mention}\n"
                valid_autoroles.append(autorole)
            else:
                # Clean up invalid autoroles
                await self.bot.db.autoroles.delete_one({"_id": autorole["_id"]})
        
        if not valid_autoroles:
            embed.description = "No valid autoroles found!\nSome roles may have been deleted."
        else:
            embed.add_field(name="Roles", value=role_list, inline=False)
            embed.add_field(name="Count", value=str(len(valid_autoroles)), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="autorole-clear", description="🗑️ Remove all autoroles")
    async def autorole_clear(self, interaction: discord.Interaction):
        """Clear all autoroles"""
        if not interaction.user.guild_permissions.manage_roles:
            embed = EmbedBuilder.error("You need Manage Roles permission to use this command!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Count current autoroles
        count = await self.bot.db.autoroles.count_documents({"guild_id": interaction.guild.id})
        
        if count == 0:
            embed = EmbedBuilder.error("There are no autoroles to clear!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create confirmation view
        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.confirmed = False
            
            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.red)
            async def confirm(self, interaction, button):
                self.confirmed = True
                await interaction.response.defer()
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction, button):
                await interaction.response.defer()
                self.stop()
        
        embed = EmbedBuilder.create(
            title="🗑️ Clear Autoroles",
            description=f"Are you sure you want to remove all {count} autoroles?\nThis action cannot be undone!",
            color=discord.Color.red()
        )
        
        view = ConfirmView()
        await interaction.response.send_message(embed=embed, view=view)
        await view.wait()
        
        if view.confirmed:
            result = await self.bot.db.autoroles.delete_many({"guild_id": interaction.guild.id})
            embed = EmbedBuilder.success(f"Cleared {result.deleted_count} autoroles!")
        else:
            embed = EmbedBuilder.create(
                title="Cancelled",
                description="Autorole clearing cancelled.",
                color=discord.Color.blue()
            )
        
        await interaction.edit_original_response(embed=embed, view=None)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Assign autoroles to new members"""
        try:
            # Get autoroles for the guild
            autoroles = await self.bot.db.autoroles.find({
                "guild_id": member.guild.id
            }).to_list(length=None)
            
            if not autoroles:
                return
            
            roles_to_add = []
            for autorole in autoroles:
                role = member.guild.get_role(autorole["role_id"])
                if role and role < member.guild.me.top_role and not role.managed:
                    roles_to_add.append(role)
                else:
                    # Clean up invalid autorole
                    await self.bot.db.autoroles.delete_one({"_id": autorole["_id"]})
            
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Autorole assignment")
                
                # Log the action if logging is enabled
                try:
                    log_data = await self.bot.db.server_settings.find_one({"guild_id": member.guild.id})
                    if log_data and "log_channel" in log_data:
                        log_channel = member.guild.get_channel(log_data["log_channel"])
                        if log_channel:
                            role_mentions = ", ".join([role.mention for role in roles_to_add])
                            embed = EmbedBuilder.create(
                                title="🎭 Autoroles Applied",
                                description=f"**{member}** joined and received autoroles",
                                color=discord.Color.green()
                            )
                            embed.add_field(name="Member", value=member.mention, inline=True)
                            embed.add_field(name="Roles Added", value=role_mentions, inline=False)
                            embed.timestamp = member.joined_at
                            
                            await log_channel.send(embed=embed)
                except:
                    pass  # Fail silently if logging fails
                    
        except Exception as e:
            print(f"Error in autorole assignment: {e}")


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Autoroles(bot))
