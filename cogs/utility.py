"""
Utility cog for Nova bot
Provides server management and utility commands.
"""

import asyncio
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class Utility(commands.Cog):
    """Utility commands for server management and information"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="serverinfo", description="📊 Get information about this server")
    async def serverinfo(self, interaction: discord.Interaction):
        """Display server information"""
        guild = interaction.guild
        
        embed = EmbedBuilder.create(
            title=f"📊 {guild.name}",
            color=discord.Color.from_rgb(135, 206, 235)
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="ID", value=str(guild.id), inline=True)
        
        # Member counts
        total_members = guild.member_count
        bots = len([m for m in guild.members if m.bot])
        humans = total_members - bots
        
        embed.add_field(name="Total Members", value=str(total_members), inline=True)
        embed.add_field(name="Humans", value=str(humans), inline=True)
        embed.add_field(name="Bots", value=str(bots), inline=True)
        
        # Counts
        embed.add_field(name="Text Channels", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
        
        # Boost info
        embed.add_field(name="Boost Level", value=str(guild.premium_tier), inline=True)
        embed.add_field(name="Boosts", value=str(guild.premium_subscription_count), inline=True)
        embed.add_field(name="Verification", value=str(guild.verification_level).title(), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="userinfo", description="👤 Get information about a user")
    @app_commands.describe(user="The user to get information about (defaults to you)")
    async def userinfo(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Display user information"""
        if user is None:
            user = interaction.user
        
        embed = EmbedBuilder.create(
            title=f"👤 {user.display_name}",
            color=user.color if user.color != discord.Color.default() else discord.Color.from_rgb(135, 206, 235)
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        # Basic info
        embed.add_field(name="Username", value=str(user), inline=True)
        embed.add_field(name="ID", value=str(user.id), inline=True)
        embed.add_field(name="Bot", value="Yes" if user.bot else "No", inline=True)
        
        # Dates
        embed.add_field(name="Account Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(user.joined_at.timestamp())}:R>", inline=True)
        
        # Server specific info
        if hasattr(user, 'premium_since') and user.premium_since:
            embed.add_field(name="Boosting Since", value=f"<t:{int(user.premium_since.timestamp())}:R>", inline=True)
        
        # Roles (limit to prevent embed being too long)
        if len(user.roles) > 1:
            roles = [role.mention for role in user.roles[1:]]  # Skip @everyone
            if len(roles) > 10:
                role_text = ", ".join(roles[:10]) + f" (+{len(roles) - 10} more)"
            else:
                role_text = ", ".join(roles)
            embed.add_field(name=f"Roles ({len(user.roles) - 1})", value=role_text, inline=False)
        
        # Permissions
        if user.guild_permissions.administrator:
            embed.add_field(name="Key Permissions", value="Administrator", inline=False)
        else:
            key_perms = []
            perm_checks = [
                ("Manage Server", user.guild_permissions.manage_guild),
                ("Manage Channels", user.guild_permissions.manage_channels),
                ("Manage Messages", user.guild_permissions.manage_messages),
                ("Kick Members", user.guild_permissions.kick_members),
                ("Ban Members", user.guild_permissions.ban_members),
            ]
            
            for perm_name, has_perm in perm_checks:
                if has_perm:
                    key_perms.append(perm_name)
            
            if key_perms:
                embed.add_field(name="Key Permissions", value=", ".join(key_perms), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="avatar", description="🖼️ Get someone's avatar")
    @app_commands.describe(user="The user whose avatar to display (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Display a user's avatar"""
        if user is None:
            user = interaction.user
        
        embed = EmbedBuilder.create(
            title=f"🖼️ {user.display_name}'s Avatar",
            color=discord.Color.from_rgb(135, 206, 235)
        )
        
        if user.avatar:
            embed.set_image(url=user.avatar.url)
            embed.add_field(
                name="Links",
                value=f"[PNG]({user.avatar.replace(format='png').url}) | [JPEG]({user.avatar.replace(format='jpeg').url}) | [WEBP]({user.avatar.url})",
                inline=False
            )
        else:
            embed.description = "This user has no custom avatar."
            embed.set_image(url=user.default_avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="ping", description="🏓 Check Nova's latency")
    async def ping(self, interaction: discord.Interaction):
        """Check bot latency"""
        # Calculate API latency
        start_time = datetime.utcnow()
        await interaction.response.defer()
        api_latency = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        embed = EmbedBuilder.create(
            title="🏓 Pong!",
            color=discord.Color.from_rgb(135, 206, 235)
        )
        
        embed.add_field(name="WebSocket Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="API Latency", value=f"{round(api_latency)}ms", inline=True)
        
        # Add status indicator
        ws_latency = self.bot.latency * 1000
        if ws_latency < 100:
            status = "🟢 Excellent"
        elif ws_latency < 200:
            status = "🟡 Good"
        elif ws_latency < 500:
          status = "🟠 Poor"
        else:
            status = "🔴 Very Poor"
        
        embed.add_field(name="Status", value=status, inline=True)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="invite", description="🔗 Get Nova's invite link")
    async def invite(self, interaction: discord.Interaction):
        """Get bot invite link"""
        permissions = discord.Permissions(
            read_messages=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            use_external_emojis=True,
            add_reactions=True,
            connect=True,
            speak=True,
            manage_messages=True,
            manage_channels=True,
            kick_members=True,
            ban_members=True,
            moderate_members=True,
            manage_roles=True,
            use_slash_commands=True
        )
        
        invite_url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=permissions,
            scopes=["bot", "applications.commands"]
        )
        
        embed = EmbedBuilder.create(
            title="🔗 Invite Nova to Your Server!",
            description="Click the button below to add me to your server with all necessary permissions!",
            color=discord.Color.from_rgb(177, 156, 217)
        )
        
        embed.add_field(
            name="What I can do:",
            value="🎵 Music playback\n🤖 AI conversations\n🛡️ Moderation tools\n🎫 Ticket system\n🎉 Giveaways\n💰 Economy system\n📊 Leveling system\n🎮 Fun commands\n⚙️ Utility commands",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Add Nova to Server",
            url=invite_url,
            style=discord.ButtonStyle.link,
            emoji="🌸"
        ))
        view.add_item(discord.ui.Button(
            label="Support Server",
            url=self.bot.config.SUPPORT_SERVER,
            style=discord.ButtonStyle.link,
            emoji="💖"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="support", description="💖 Get support and join Nova's community")
    async def support(self, interaction: discord.Interaction):
        """Get support information"""
        embed = EmbedBuilder.create(
            title="💖 Nova Support",
            description="Need help or want to join our community? We're here for you!",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        
        embed.add_field(
            name="🎫 Get Help",
            value="Join our support server for assistance with commands, setup, or troubleshooting.",
            inline=False
        )
        
        embed.add_field(
            name="💬 Community",
            value="Chat with other Nova users, share feedback, and stay updated on new features!",
            inline=False
        )
        
        embed.add_field(
            name="🌟 Feature Requests",
            value="Have an idea for Nova? We'd love to hear it in our support server!",
            inline=False
        )
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Join Support Server",
            url=self.bot.config.SUPPORT_SERVER,
            style=discord.ButtonStyle.link,
            emoji="💖"
        ))
        
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="stats", description="📈 View Nova's statistics")
    async def stats(self, interaction: discord.Interaction):
        """Display bot statistics"""
        embed = EmbedBuilder.create(
            title="📈 Nova Statistics",
            color=discord.Color.from_rgb(135, 206, 235)
        )
        
        # Basic stats
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Users", value=str(len(self.bot.users)), inline=True)
        embed.add_field(name="Commands", value=str(len(self.bot.tree.get_commands())), inline=True)
        
        # Uptime calculation (placeholder - would need actual startup time tracking)
        embed.add_field(name="Uptime", value="N/A (not implemented)", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Version", value=self.bot.config.BOT_VERSION, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="❓ Get help with Nova's commands")
    async def help_command(self, interaction: discord.Interaction):
        """Display help information with category selection"""
        embed = EmbedBuilder.create(
            title="❓ Nova Help",
            description="Select a category below to see available commands!",
            color=discord.Color.from_rgb(177, 156, 217)
        )
        
        embed.add_field(
            name="🌸 About Nova",
            value="Nova is a multipurpose Discord bot with 150+ slash commands to enhance your server experience!",
            inline=False
        )
        
        # Create select menu for categories
        class HelpSelect(discord.ui.Select):
            def __init__(self):
                options = [
                    discord.SelectOption(label="🎵 Music", description="Music playback and queue management", value="music"),
                    discord.SelectOption(label="🤖 AI Chat", description="AI-powered conversations", value="ai_chat"),
                    discord.SelectOption(label="🛡️ Moderation", description="Server moderation tools", value="moderation"),
                    discord.SelectOption(label="🎫 Tickets", description="Support ticket system", value="tickets"),
                    discord.SelectOption(label="🎉 Fun", description="Entertainment and games", value="fun"),
                    discord.SelectOption(label="💰 Economy", description="Virtual currency system", value="economy"),
                    discord.SelectOption(label="📊 Leveling", description="XP and ranking system", value="leveling"),
                    discord.SelectOption(label="⚙️ Utility", description="Server management tools", value="utility"),
                ]
                super().__init__(placeholder="Choose a category...", options=options)
            
            async def callback(self, interaction):
                category_embeds = {
                    "music": self._create_music_embed(),
                    "ai_chat": self._create_ai_embed(),
                    "moderation": self._create_moderation_embed(),
                    "tickets": self._create_tickets_embed(),
                    "fun": self._create_fun_embed(),
                    "economy": self._create_economy_embed(),
                    "leveling": self._create_leveling_embed(),
                    "utility": self._create_utility_embed(),
                }
                
                embed = category_embeds.get(self.values[0])
                await interaction.response.edit_message(embed=embed, view=self.view)
            
            def _create_music_embed(self):
                embed = EmbedBuilder.create(
                    title="🎵 Music Commands",
                    description="Control music playback in voice channels",
                    color=discord.Color.from_rgb(221, 160, 221)
                )
                embed.add_field(name="/play", value="Play music from YouTube or Spotify", inline=True)
                embed.add_field(name="/pause", value="Pause the current song", inline=True)
                embed.add_field(name="/resume", value="Resume playback", inline=True)
                embed.add_field(name="/skip", value="Skip the current song", inline=True)
                embed.add_field(name="/stop", value="Stop music and disconnect", inline=True)
                embed.add_field(name="/queue", value="View the music queue", inline=True)
                embed.add_field(name="/loop", value="Set loop mode", inline=True)
                embed.add_field(name="/volume", value="Adjust playback volume", inline=True)
                embed.add_field(name="/lyrics", value="Get song lyrics", inline=True)
                return embed
            
            def _create_ai_embed(self):
                embed = EmbedBuilder.create(
                    title="🤖 AI Chat Commands",
                    description="AI-powered conversation features",
                    color=discord.Color.from_rgb(177, 156, 217)
                )
                embed.add_field(name="/ask", value="Ask Nova a question", inline=True)
                embed.add_field(name="/chat", value="Toggle AI responses in server", inline=True)
                embed.add_field(name="/ai_info", value="Learn about AI features", inline=True)
                return embed
            
            def _create_moderation_embed(self):
                embed = EmbedBuilder.create(
                    title="🛡️ Moderation Commands",
                    description="Tools for server management",
                    color=discord.Color.red()
                )
                embed.add_field(name="/ban", value="Ban a user from the server", inline=True)
                embed.add_field(name="/kick", value="Kick a user from the server", inline=True)
                embed.add_field(name="/mute", value="Timeout a user", inline=True)
                embed.add_field(name="/unmute", value="Remove timeout from user", inline=True)
                embed.add_field(name="/warn", value="Warn a user", inline=True)
                embed.add_field(name="/clear", value="Delete multiple messages", inline=True)
                return embed
            
            def _create_tickets_embed(self):
                embed = EmbedBuilder.create(
                    title="🎫 Ticket Commands",
                    description="Support ticket system",
                    color=discord.Color.blue()
                )
                embed.add_field(name="/ticket create", value="Create a new support ticket", inline=True)
                embed.add_field(name="/ticket close", value="Close a ticket", inline=True)
                embed.add_field(name="/ticket claim", value="Claim a ticket", inline=True)
                return embed
            
            def _create_fun_embed(self):
                embed = EmbedBuilder.create(
                    title="🎉 Fun Commands",
                    description="Entertainment and games (examples)",
                    color=discord.Color.from_rgb(255, 192, 203)
                )
                embed.add_field(name="Coming Soon!", value="Fun commands are being developed", inline=False)
                return embed
            
            def _create_economy_embed(self):
                embed = EmbedBuilder.create(
                    title="💰 Economy Commands",
                    description="Virtual currency system (examples)",
                    color=discord.Color.from_rgb(240, 230, 140)
                )
                embed.add_field(name="Coming Soon!", value="Economy commands are being developed", inline=False)
                return embed
            
            def _create_leveling_embed(self):
                embed = EmbedBuilder.create(
                    title="📊 Leveling Commands",
                    description="XP and ranking system (examples)",
                    color=discord.Color.from_rgb(144, 238, 144)
                )
                embed.add_field(name="Coming Soon!", value="Leveling commands are being developed", inline=False)
                return embed
            
            def _create_utility_embed(self):
                embed = EmbedBuilder.create(
                    title="⚙️ Utility Commands",
                    description="Server management and info tools",
                    color=discord.Color.from_rgb(135, 206, 235)
                )
                embed.add_field(name="/serverinfo", value="Get server information", inline=True)
                embed.add_field(name="/userinfo", value="Get user information", inline=True)
                embed.add_field(name="/avatar", value="Display user's avatar", inline=True)
                embed.add_field(name="/ping", value="Check bot latency", inline=True)
                embed.add_field(name="/invite", value="Get bot invite link", inline=True)
                embed.add_field(name="/support", value="Get support information", inline=True)
                embed.add_field(name="/stats", value="View bot statistics", inline=True)
                embed.add_field(name="/help", value="This help command", inline=True)
                return embed
        
        class HelpView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=300)
                self.add_item(HelpSelect())
            
            @discord.ui.button(label="🏠 Back to Main", style=discord.ButtonStyle.secondary)
            async def back_to_main(self, interaction, button):
                main_embed = EmbedBuilder.create(
                    title="❓ Nova Help",
                    description="Select a category below to see available commands!",
                    color=discord.Color.from_rgb(177, 156, 217)
                )
                main_embed.add_field(
                    name="🌸 About Nova",
                    value="Nova is a multipurpose Discord bot with 150+ slash commands to enhance your server experience!",
                    inline=False
                )
                await interaction.response.edit_message(embed=main_embed, view=self)
        
        view = HelpView()
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Utility(bot))
