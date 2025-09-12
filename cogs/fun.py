"""
Fun cog for Nova bot
Provides entertainment and game commands.
"""

import random
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class Fun(commands.Cog):
    """Fun and entertainment commands"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="8ball", description="🎱 Ask the magic 8-ball a question")
    @app_commands.describe(question="Your question for the magic 8-ball")
    async def eight_ball(self, interaction: discord.Interaction, question: str):
        """Magic 8-ball command"""
        responses = [
            "It is certain! ✨",
            "Without a doubt! 💫",
            "Yes definitely! 🌟",
            "You may rely on it! 💖",
            "As I see it, yes! 👀",
            "Most likely! 🌸",
            "Outlook good! 🌺",
            "Yes! 💕",
            "Signs point to yes! 👍",
            "Reply hazy, try again... 🌫️",
            "Ask again later! ⏰",
            "Better not tell you now... 🤫",
            "Cannot predict now! 🔮",
            "Concentrate and ask again! 🧘",
            "Don't count on it! 😅",
            "My reply is no! ❌",
            "My sources say no! 📚",
            "Outlook not so good... 😰",
            "Very doubtful! 🤔",
        ]
        
        response = random.choice(responses)
        
        embed = EmbedBuilder.create(
            title="🎱 Magic 8-Ball",
            color=discord.Color.from_rgb(255, 192, 203)
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=response, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="roll", description="🎲 Roll dice")
    @app_commands.describe(
        sides="Number of sides on the die (default: 6)",
        count="Number of dice to roll (default: 1)"
    )
    async def roll(self, interaction: discord.Interaction, sides: int = 6, count: int = 1):
        """Roll dice"""
        if sides < 2 or sides > 100:
            embed = EmbedBuilder.error("Number of sides must be between 2 and 100!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if count < 1 or count > 10:
            embed = EmbedBuilder.error("Number of dice must be between 1 and 10!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        
        embed = EmbedBuilder.create(
            title="🎲 Dice Roll",
            color=discord.Color.from_rgb(255, 192, 203)
        )
        
        if count == 1:
            embed.add_field(name="Result", value=f"**{rolls[0]}** (1d{sides})", inline=False)
        else:
            rolls_text = " + ".join(map(str, rolls))
            embed.add_field(name="Rolls", value=rolls_text, inline=False)
            embed.add_field(name="Total", value=f"**{total}** ({count}d{sides})", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="flip", description="🪙 Flip a coin")
    async def flip(self, interaction: discord.Interaction):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        emoji = "🟡" if result == "Heads" else "🟢"
        
        embed = EmbedBuilder.create(
            title="🪙 Coin Flip",
            description=f"{emoji} **{result}**!",
            color=discord.Color.from_rgb(255, 192, 203)
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="choose", description="🤔 Let Nova choose between options")
    @app_commands.describe(options="Options separated by commas (e.g., pizza, burger, tacos)")
    async def choose(self, interaction: discord.Interaction, options: str):
        """Choose between options"""
        choices = [choice.strip() for choice in options.split(",")]
        
        if len(choices) < 2:
            embed = EmbedBuilder.error("Please provide at least 2 options separated by commas!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if len(choices) > 10:
            embed = EmbedBuilder.error("Please provide no more than 10 options!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        choice = random.choice(choices)
        
        embed = EmbedBuilder.create(
            title="🤔 Nova's Choice",
            description=f"I choose... **{choice}**! 🌸",
            color=discord.Color.from_rgb(255, 192, 203)
        )
        
        embed.add_field(name="Options", value=", ".join(choices), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="joke", description="😂 Get a random joke")
    async def joke(self, interaction: discord.Interaction):
        """Tell a random joke"""
        jokes = [
            ("Why don't scientists trust atoms?", "Because they make up everything! 😄"),
            ("Why did the scarecrow win an award?", "He was outstanding in his field! 🌾"),
            ("Why don't eggs tell jokes?", "They'd crack each other up! 🥚"),
            ("What do you call a fake noodle?", "An impasta! 🍝"),
            ("Why did the math book look so sad?", "Because it had too many problems! 📚"),
            ("What do you call a bear with no teeth?", "A gummy bear! 🐻"),
            ("Why don't skeletons fight each other?", "They don't have the guts! 💀"),
            ("What do you call a dinosaur that crashes his car?", "Tyrannosaurus Wrecks! 🦕"),
            ("Why can't a bicycle stand up by itself?", "It's two tired! 🚲"),
            ("What do you call a fish wearing a crown?", "A king fish! 👑🐟"),
        ]
        
        setup, punchline = random.choice(jokes)
        
        embed = EmbedBuilder.create(
            title="😂 Here's a joke for you!",
            color=discord.Color.from_rgb(255, 192, 203)
        )
        embed.add_field(name="Setup", value=setup, inline=False)
        embed.add_field(name="Punchline", value=punchline, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="compliment", description="💖 Get a wholesome compliment")
    @app_commands.describe(user="User to compliment (optional)")
    async def compliment(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Give someone a compliment"""
        target = user if user else interaction.user
        
        compliments = [
            "You're absolutely amazing! ✨",
            "Your smile could light up the whole server! 😊",
            "You have such a wonderful personality! 💖",
            "You're incredibly thoughtful and kind! 🌸",
            "Your creativity is inspiring! 🎨",
            "You make everyone around you happier! 🌟",
            "You're stronger than you know! 💪",
            "Your positive energy is contagious! ⚡",
            "You're a true gem! 💎",
            "You have an amazing sense of humor! 😄",
            "You're so talented! 🌺",
            "Your kindness makes the world better! 🌍",
            "You're absolutely fabulous! ✨",
            "You have such a beautiful heart! 💝",
            "You're one of a kind! 🦄",
        ]
        
        compliment = random.choice(compliments)
        
        embed = EmbedBuilder.create(
            title="💖 Compliment Time!",
            description=f"{target.mention}, {compliment}",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="rate", description="⭐ Rate something on a scale of 1-10")
    @app_commands.describe(thing="What do you want me to rate?")
    async def rate(self, interaction: discord.Interaction, thing: str):
        """Rate something"""
        rating = random.randint(1, 10)
        
        # Special cases for fun
        if "nova" in thing.lower():
            rating = 10
        elif any(word in thing.lower() for word in ["pizza", "cat", "dog", "music"]):
            rating = random.randint(8, 10)
        
        stars = "⭐" * rating + "☆" * (10 - rating)
        
        embed = EmbedBuilder.create(
            title="⭐ Rating Time!",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.add_field(name="Item", value=thing, inline=False)
        embed.add_field(name="Rating", value=f"{rating}/10\n{stars}", inline=False)
        
        # Add flavor text based on rating
        if rating >= 9:
            flavor = "Absolutely amazing! 🤩"
        elif rating >= 7:
            flavor = "Pretty great! 😊"
        elif rating >= 5:
            flavor = "Not bad! 👍"
        elif rating >= 3:
            flavor = "Could be better... 🤔"
        else:
            flavor = "Oof, that's rough! 😅"
        
        embed.add_field(name="Verdict", value=flavor, inline=False)
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Fun(bot))
