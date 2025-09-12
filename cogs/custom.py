"""
Custom tags cog for Nova bot
Provides server-specific custom command functionality.
"""

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class Custom(commands.Cog):
    """Custom tags and commands system"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="tag-create", description="🏷️ Create a custom tag")
    @app_commands.describe(
        name="Name of the tag",
        content="Content of the tag"
    )
    async def tag_create(self, interaction: discord.Interaction, name: str, content: str):
        """Create a custom tag"""
        if not interaction.user.guild_permissions.manage_messages:
            embed = EmbedBuilder.error("You need Manage Messages permission to create tags!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate tag name
        name = name.lower()
        if len(name) < 2 or len(name) > 32:
            embed = EmbedBuilder.error("Tag name must be between 2 and 32 characters!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check for invalid characters
        if not name.isalnum() and not all(c in '-_' for c in name if not c.isalnum()):
            embed = EmbedBuilder.error("Tag name can only contain letters, numbers, hyphens, and underscores!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if tag already exists
        existing_tag = await self.bot.db.tags.find_one({
            "guild_id": interaction.guild.id,
            "name": name
        })
        
        if existing_tag:
            embed = EmbedBuilder.error(f"Tag `{name}` already exists!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate content
        if len(content) > 2000:
            embed = EmbedBuilder.error("Tag content cannot exceed 2000 characters!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create tag
        await self.bot.db.tags.insert_one({
            "guild_id": interaction.guild.id,
            "name": name,
            "content": content,
            "author_id": interaction.user.id,
            "created_at": discord.utils.utcnow(),
            "uses": 0
        })
        
        embed = EmbedBuilder.success(f"Tag `{name}` created successfully!")
        embed.add_field(name="Usage", value=f"`/tag {name}`", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="tag", description="🏷️ Use a custom tag")
    @app_commands.describe(name="Name of the tag to display")
    async def tag_use(self, interaction: discord.Interaction, name: str):
        """Use a custom tag"""
        name = name.lower()
        
        tag = await self.bot.db.tags.find_one({
            "guild_id": interaction.guild.id,
            "name": name
        })
        
        if not tag:
            embed = EmbedBuilder.error(f"Tag `{name}` not found!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Increment usage counter
        await self.bot.db.tags.update_one(
            {"_id": tag["_id"]},
            {"$inc": {"uses": 1}}
        )
        
        # Send tag content
        await interaction.response.send_message(tag["content"])
    
    @app_commands.command(name="tag-edit", description="✏️ Edit a custom tag")
    @app_commands.describe(
        name="Name of the tag to edit",
        content="New content for the tag"
    )
    async def tag_edit(self, interaction: discord.Interaction, name: str, content: str):
        """Edit a custom tag"""
        name = name.lower()
        
        tag = await self.bot.db.tags.find_one({
            "guild_id": interaction.guild.id,
            "name": name
        })
        
        if not tag:
            embed = EmbedBuilder.error(f"Tag `{name}` not found!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check permissions
        can_edit = (
            interaction.user.id == tag["author_id"] or
            interaction.user.guild_permissions.manage_messages
        )
        
        if not can_edit:
            embed = EmbedBuilder.error("You can only edit tags you created, or you need Manage Messages permission!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Validate new content
        if len(content) > 2000:
            embed = EmbedBuilder.error("Tag content cannot exceed 2000 characters!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Update tag
        await self.bot.db.tags.update_one(
            {"_id": tag["_id"]},
            {
                "$set": {
                    "content": content,
                    "edited_at": discord.utils.utcnow(),
                    "edited_by": interaction.user.id
                }
            }
        )
        
        embed = EmbedBuilder.success(f"Tag `{name}` updated successfully!")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="tag-delete", description="🗑️ Delete a custom tag")
    @app_commands.describe(name="Name of the tag to delete")
    async def tag_delete(self, interaction: discord.Interaction, name: str):
        """Delete a custom tag"""
        name = name.lower()
        
        tag = await self.bot.db.tags.find_one({
            "guild_id": interaction.guild.id,
            "name": name
        })
        
        if not tag:
            embed = EmbedBuilder.error(f"Tag `{name}` not found!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check permissions
        can_delete = (
            interaction.user.id == tag["author_id"] or
            interaction.user.guild_permissions.manage_messages
        )
        
        if not can_delete:
            embed = EmbedBuilder.error("You can only delete tags you created, or you need Manage Messages permission!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Delete tag
        await self.bot.db.tags.delete_one({"_id": tag["_id"]})
        
        embed = EmbedBuilder.success(f"Tag `{name}` deleted successfully!")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="tag-info", description="ℹ️ Get information about a tag")
    @app_commands.describe(name="Name of the tag to get info about")
    async def tag_info(self, interaction: discord.Interaction, name: str):
        """Get information about a tag"""
        name = name.lower()
        
        tag = await self.bot.db.tags.find_one({
            "guild_id": interaction.guild.id,
            "name": name
        })
        
        if not tag:
            embed = EmbedBuilder.error(f"Tag `{name}` not found!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = EmbedBuilder.create(
            title=f"🏷️ Tag: {name}",
            color=discord.Color.blue()
        )
        
        # Get author
        author = self.bot.get_user(tag["author_id"])
        author_name = author.display_name if author else "Unknown User"
        
        embed.add_field(name="Author", value=author_name, inline=True)
        embed.add_field(name="Uses", value=str(tag["uses"]), inline=True)
        embed.add_field(name="Created", value=f"<t:{int(tag['created_at'].timestamp())}:R>", inline=True)
        
        if "edited_at" in tag:
            editor = self.bot.get_user(tag["edited_by"]) if "edited_by" in tag else None
            editor_name = editor.display_name if editor else "Unknown User"
            embed.add_field(name="Last Edited", value=f"<t:{int(tag['edited_at'].timestamp())}:R> by {editor_name}", inline=False)
        
        # Show content preview
        content_preview = tag["content"][:200] + "..." if len(tag["content"]) > 200 else tag["content"]
        embed.add_field(name="Content Preview", value=f"```{content_preview}```", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="tag-list", description="📋 List all tags in this server")
    async def tag_list(self, interaction: discord.Interaction):
        """List all tags in the server"""
        await interaction.response.defer()
        
        tags = await self.bot.db.tags.find({
            "guild_id": interaction.guild.id
        }).sort("uses", -1).to_list(length=None)
        
        if not tags:
            embed = EmbedBuilder.create(
                title="📋 Server Tags",
                description="No tags found! Use `/tag-create` to create one.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = EmbedBuilder.create(
          title="📋 Server Tags",
            description=f"Found {len(tags)} tag{'s' if len(tags) != 1 else ''} in this server",
            color=discord.Color.blue()
        )
        
        # Group tags by usage for better display
        popular_tags = [tag for tag in tags if tag["uses"] > 5][:10]
        recent_tags = tags[:15]  # Show up to 15 most used tags
        
        if popular_tags:
            popular_text = ""
            for tag in popular_tags:
                author = self.bot.get_user(tag["author_id"])
                author_name = author.display_name if author else "Unknown"
                popular_text += f"• `{tag['name']}` ({tag['uses']} uses) - by {author_name}\n"
            
            embed.add_field(name="🔥 Popular Tags", value=popular_text, inline=False)
        
        # Show all tags (or first 15)
        tag_list = ""
        for i, tag in enumerate(recent_tags):
            if i >= 15:
                tag_list += f"... and {len(tags) - 15} more"
                break
            tag_list += f"`{tag['name']}` "
        
        if tag_list:
            embed.add_field(name="All Tags", value=tag_list, inline=False)
        
        embed.add_field(name="Usage", value="Use `/tag <name>` to display a tag", inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="tag-search", description="🔍 Search for tags")
    @app_commands.describe(query="Search query for tag names or content")
    async def tag_search(self, interaction: discord.Interaction, query: str):
        """Search for tags by name or content"""
        await interaction.response.defer()
        
        # Search in both name and content
        tags = await self.bot.db.tags.find({
            "guild_id": interaction.guild.id,
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"content": {"$regex": query, "$options": "i"}}
            ]
        }).to_list(length=20)  # Limit to 20 results
        
        if not tags:
            embed = EmbedBuilder.error(f"No tags found matching '{query}'")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        embed = EmbedBuilder.create(
            title="🔍 Tag Search Results",
            description=f"Found {len(tags)} tag{'s' if len(tags) != 1 else ''} matching '{query}'",
            color=discord.Color.blue()
        )
        
        results_text = ""
        for tag in tags[:10]:  # Show top 10
            author = self.bot.get_user(tag["author_id"])
            author_name = author.display_name if author else "Unknown"
            results_text += f"• `{tag['name']}` ({tag['uses']} uses) - by {author_name}\n"
        
        if len(tags) > 10:
            results_text += f"... and {len(tags) - 10} more results"
        
        embed.add_field(name="Results", value=results_text, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="tag-stats", description="📊 View tag statistics for this server")
    async def tag_stats(self, interaction: discord.Interaction):
        """Show tag statistics"""
        await interaction.response.defer()
        
        # Get tag statistics
        pipeline = [
            {"$match": {"guild_id": interaction.guild.id}},
            {"$group": {
                "_id": None,
                "total_tags": {"$sum": 1},
                "total_uses": {"$sum": "$uses"},
                "avg_uses": {"$avg": "$uses"}
            }}
        ]
        
        stats = await self.bot.db.tags.aggregate(pipeline).to_list(length=1)
        
        if not stats:
            embed = EmbedBuilder.error("No tag statistics available!")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        stats = stats[0]
        
        embed = EmbedBuilder.create(
            title="📊 Tag Statistics",
            color=discord.Color.from_rgb(135, 206, 235)
        )
        
        embed.add_field(name="Total Tags", value=str(stats["total_tags"]), inline=True)
        embed.add_field(name="Total Uses", value=f"{stats['total_uses']:,}", inline=True)
        embed.add_field(name="Average Uses", value=f"{stats['avg_uses']:.1f}", inline=True)
        
        # Get top authors
        author_pipeline = [
            {"$match": {"guild_id": interaction.guild.id}},
            {"$group": {
                "_id": "$author_id",
                "tag_count": {"$sum": 1},
                "total_uses": {"$sum": "$uses"}
            }},
            {"$sort": {"tag_count": -1}},
            {"$limit": 5}
        ]
        
        top_authors = await self.bot.db.tags.aggregate(author_pipeline).to_list(length=5)
        
        if top_authors:
            author_text = ""
            for author_data in top_authors:
                author = self.bot.get_user(author_data["_id"])
                author_name = author.display_name if author else "Unknown User"
                author_text += f"• {author_name}: {author_data['tag_count']} tags ({author_data['total_uses']} uses)\n"
            
            embed.add_field(name="🏆 Top Tag Creators", value=author_text, inline=False)
        
        # Get most used tags
        most_used = await self.bot.db.tags.find({
            "guild_id": interaction.guild.id
        }).sort("uses", -1).limit(5).to_list(length=5)
        
        if most_used:
            used_text = ""
            for tag in most_used:
                if tag["uses"] > 0:
                    used_text += f"• `{tag['name']}`: {tag['uses']} uses\n"
            
            if used_text:
                embed.add_field(name="📈 Most Used Tags", value=used_text, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    # Autocomplete for tag commands
    @tag_use.autocomplete('name')
    @tag_edit.autocomplete('name')
    @tag_delete.autocomplete('name')
    @tag_info.autocomplete('name')
    async def tag_name_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete tag names"""
        try:
            # Get matching tags
            tags = await self.bot.db.tags.find({
                "guild_id": interaction.guild.id,
                "name": {"$regex": f"^{current}", "$options": "i"}
            }).sort("uses", -1).limit(25).to_list(length=25)
            
            return [
                app_commands.Choice(name=tag["name"], value=tag["name"])
                for tag in tags
            ]
        except:
            return []


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Custom(bot))
