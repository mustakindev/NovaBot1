"""
Embed utilities for Nova bot
Provides reusable embed templates with consistent styling.
"""

from typing import Optional

import discord


class EmbedBuilder:
    """Builder class for creating consistent embeds"""
    
    # Pastel color palette
    COLORS = {
        "primary": 0xB19CD9,    # Lavender
        "success": 0x98FB98,    # Pale green
        "warning": 0xFFB6C1,    # Light pink
        "error": 0xFFCCCB,      # Light coral
        "info": 0x87CEEB,       # Sky blue
        "music": 0xDDA0DD,      # Plum
        "economy": 0xF0E68C,    # Khaki
    }
    
    @staticmethod
    def create(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[int] = None,
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create a basic embed with Nova branding"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color or EmbedBuilder.COLORS["primary"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def success(
        message: str,
        title: str = "Success",
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create a success embed"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=message,
            color=EmbedBuilder.COLORS["success"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def error(
        message: str,
        title: str = "Error",
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create an error embed"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=message,
            color=EmbedBuilder.COLORS["error"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def warning(
        message: str,
        title: str = "Warning",
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create a warning embed"""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=message,
            color=EmbedBuilder.COLORS["warning"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def info(
        message: str,
        title: str = "Information",
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create an info embed"""
        embed = discord.Embed(
            title=f"ℹ️ {title}",
            description=message,
            color=EmbedBuilder.COLORS["info"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def music(
        title: str,
        description: Optional[str] = None,
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create a music-themed embed"""
        embed = discord.Embed(
            title=f"🎵 {title}",
            description=description,
            color=EmbedBuilder.COLORS["music"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def economy(
        title: str,
        description: Optional[str] = None,
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create an economy-themed embed"""
        embed = discord.Embed(
            title=f"💰 {title}",
            description=description,
            color=EmbedBuilder.COLORS["economy"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    @staticmethod
    def paginated_embed(
        items: list,
        title: str,
        items_per_page: int = 10,
        page: int = 0,
        color: Optional[int] = None
    ) -> discord.Embed:
        """Create a paginated embed"""
        start_index = page * items_per_page
        end_index = start_index + items_per_page
        page_items = items[start_index:end_index]
        
        total_pages = (len(items) + items_per_page - 1) // items_per_page
        
        embed = EmbedBuilder.create(
            title=title,
            color=color
        )
        
        if page_items:
            content = "\n".join(str(item) for item in page_items)
            embed.description = content
        else:
            embed.description = "No items found."
        
        embed.set_footer(text=f"🌸 Page {page + 1}/{max(1, total_pages)} • Powered by Nova")
        
        return embed
    
    @staticmethod
    def loading(
        message: str = "Loading...",
        footer_text: str = "🌸 Powered by Nova"
    ) -> discord.Embed:
        """Create a loading embed"""
        embed = discord.Embed(
            title="⏳ Please Wait",
            description=message,
            color=EmbedBuilder.COLORS["info"]
        )
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
