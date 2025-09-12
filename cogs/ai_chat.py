"""
AI Chat cog for Nova bot
Provides OpenAI-powered conversation functionality.
"""

import asyncio
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import openai

from utils.embeds import EmbedBuilder
from utils.checks import has_permissions


class AIChat(commands.Cog):
    """AI-powered chat functionality using OpenAI"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.openai_client = None
        
        # Initialize OpenAI client if API key is available
        if bot.config.OPENAI_API_KEY:
            try:
                self.openai_client = openai.AsyncOpenAI(api_key=bot.config.OPENAI_API_KEY)
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
    
    @app_commands.command(name="ask", description="🤖 Ask Nova a question using AI")
    @app_commands.describe(question="Your question for the AI")
    async def ask(self, interaction: discord.Interaction, question: str):
        """Ask the AI a question"""
        if not self.openai_client:
            embed = EmbedBuilder.error("AI features are not available - missing OpenAI API key!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if len(question) > 1000:
            embed = EmbedBuilder.error("Question is too long! Please keep it under 1000 characters.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Create a kawaii system message
            system_message = """You are Nova, a cute and helpful Discord bot with a kawaii personality! 
            You should be friendly, enthusiastic, and use cute expressions occasionally. 
            Use emojis sparingly but appropriately. Keep responses concise but helpful.
            You love helping people and making them smile! 🌸"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": question}
                ],
                max_tokens=500,
                temperature=0.8
            )
            
            ai_response = response.choices[0].message.content
            
            # Create embed with the AI response
            embed = EmbedBuilder.create(
                title="🤖 Nova AI Response",
                description=ai_response,
                color=discord.Color.from_rgb(177, 156, 217)
            )
            embed.add_field(name="Question", value=question, inline=False)
            embed.set_footer(text=f"Asked by {interaction.user.display_name} | 🌸 Powered by Nova")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = EmbedBuilder.error(f"Failed to get AI response: {str(e)}")
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="chat", description="💬 Toggle AI chat responses in this server")
    async def chat_toggle(self, interaction: discord.Interaction):
        """Toggle AI chat responses for the server"""
        if not interaction.user.guild_permissions.manage_guild:
            embed = EmbedBuilder.error("You need Manage Server permission to use this command!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not self.openai_client:
            embed = EmbedBuilder.error("AI features are not available - missing OpenAI API key!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Get current setting from database
        guild_data = await self.bot.db.server_settings.find_one({"guild_id": interaction.guild.id})
        current_setting = guild_data.get("ai_chat_enabled", False) if guild_data else False
        
        # Toggle the setting
        new_setting = not current_setting
        
        await self.bot.db.server_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"ai_chat_enabled": new_setting}},
            upsert=True
        )
        
        status = "enabled" if new_setting else "disabled"
        embed = EmbedBuilder.success(f"AI chat responses have been **{status}** for this server!")
        
        if new_setting:
            embed.add_field(
                name="How it works",
                value="I'll respond to messages that mention me or start with 'nova'",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages to respond with AI"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Only respond in guilds
        if not message.guild:
            return
        
        # Check if AI chat is enabled for this server
        guild_data = await self.bot.db.server_settings.find_one({"guild_id": message.guild.id})
        if not guild_data or not guild_data.get("ai_chat_enabled", False):
            return
        
        # Check if bot was mentioned or message starts with "nova"
        mentioned = self.bot.user in message.mentions
        starts_with_nova = message.content.lower().startswith("nova")
        
        if not (mentioned or starts_with_nova):
            return
        
        # Don't respond if no OpenAI client
        if not self.openai_client:
            return
        
        # Clean the message content
        content = message.content
        if mentioned:
            content = content.replace(f"<@{self.bot.user.id}>", "").strip()
        if starts_with_nova:
            content = content[4:].strip()  # Remove "nova" prefix
        
        if not content:
            return
        
        # Limit message length
        if len(content) > 500:
            embed = EmbedBuilder.error("Message is too long for AI processing!")
            await message.reply(embed=embed)
            return
        
        # Show typing indicator
        async with message.channel.typing():
            try:
                system_message = """You are Nova, a cute and helpful Discord bot! 
                You're chatting casually in a Discord server. Be friendly, helpful, and kawaii!
                Keep responses short (under 200 characters) since this is casual chat.
                Use emojis occasionally but don't overdo it. You love helping and making friends! 🌸"""
                
                response = await self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": content}
                    ],
                    max_tokens=150,
                    temperature=0.9
                )
                
                ai_response = response.choices[0].message.content
                
                # Send response as a reply
                await message.reply(ai_response)
                
            except Exception as e:
                print(f"AI chat error: {e}")
                # Fail silently to avoid spamming error messages
    
    @app_commands.command(name="ai_info", description="ℹ️ Information about Nova's AI features")
    async def ai_info(self, interaction: discord.Interaction):
        """Show information about AI features"""
        embed = EmbedBuilder.create(
            title="🤖 Nova AI Features",
            description="Learn about my AI-powered capabilities!",
            color=discord.Color.from_rgb(177, 156, 217)
        )
        
        embed.add_field(
            name="📝 /ask Command",
            value="Ask me any question and I'll respond using AI! Perfect for getting help, information, or just having a conversation.",
            inline=False
        )
        
        embed.add_field(
            name="💬 AI Chat (Server Feature)",
            value="Admins can enable AI chat responses. When enabled, I'll respond to messages that mention me or start with 'nova'.",
            inline=False
        )
        
        embed.add_field(
            name="🌸 Personality",
            value="I have a cute, kawaii personality and love helping people! I try to be friendly and encouraging in all my responses.",
            inline=False
        )
        
        if not self.openai_client:
            embed.add_field(
                name="⚠️ Status",
                value="AI features are currently unavailable (missing API key)",
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Status",
                value="AI features are active and ready to help!",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(AIChat(bot))
