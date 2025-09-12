"""
Economy cog for Nova bot
Provides virtual currency system commands.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import EmbedBuilder


class Economy(commands.Cog):
    """Virtual economy system with currency and shops"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def get_user_balance(self, user_id: int, guild_id: int) -> int:
        """Get user's current balance"""
        user_data = await self.bot.db.economy.find_one({
            "user_id": user_id,
            "guild_id": guild_id
        })
        return user_data.get("balance", 0) if user_data else 0
    
    async def update_balance(self, user_id: int, guild_id: int, amount: int) -> int:
        """Update user's balance and return new balance"""
        result = await self.bot.db.economy.find_one_and_update(
            {"user_id": user_id, "guild_id": guild_id},
            {"$inc": {"balance": amount}},
            upsert=True,
            return_document=True
        )
        return result["balance"]
    
    async def can_daily(self, user_id: int, guild_id: int) -> bool:
        """Check if user can claim daily reward"""
        user_data = await self.bot.db.economy.find_one({
            "user_id": user_id,
            "guild_id": guild_id
        })
        
        if not user_data or "last_daily" not in user_data:
            return True
        
        last_daily = user_data["last_daily"]
        next_daily = last_daily + timedelta(hours=24)
        return datetime.utcnow() >= next_daily
    
    @app_commands.command(name="balance", description="💰 Check your or someone's balance")
    @app_commands.describe(user="User to check balance for (optional)")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Check balance"""
        target = user if user else interaction.user
        balance = await self.get_user_balance(target.id, interaction.guild.id)
        
        embed = EmbedBuilder.create(
            title="💰 Balance",
            color=discord.Color.from_rgb(240, 230, 140)
        )
        
        if target == interaction.user:
            embed.description = f"You have **{balance:,}** Nova Coins! 🪙"
        else:
            embed.description = f"{target.display_name} has **{balance:,}** Nova Coins! 🪙"
        
        # Add wealth tier
        if balance >= 100000:
            tier = "💎 Diamond Tier"
        elif balance >= 50000:
            tier = "🏆 Gold Tier"
        elif balance >= 25000:
            tier = "🥈 Silver Tier"
        elif balance >= 10000:
            tier = "🥉 Bronze Tier"
        else:
            tier = "🌱 Starter"
        
        embed.add_field(name="Wealth Tier", value=tier, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="daily", description="🎁 Claim your daily reward")
    async def daily(self, interaction: discord.Interaction):
        """Claim daily reward"""
        if not await self.can_daily(interaction.user.id, interaction.guild.id):
            user_data = await self.bot.db.economy.find_one({
                "user_id": interaction.user.id,
                "guild_id": interaction.guild.id
            })
            last_daily = user_data["last_daily"]
            next_daily = last_daily + timedelta(hours=24)
            time_left = next_daily - datetime.utcnow()
            
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            
            embed = EmbedBuilder.error(f"You already claimed your daily reward!\nNext reward in: {hours}h {minutes}m")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Calculate reward (base 500 + bonus)
        base_reward = 500
        bonus = random.randint(0, 200)
        total_reward = base_reward + bonus
        
        # Check for streak bonus (simplified)
        user_data = await self.bot.db.economy.find_one({
            "user_id": interaction.user.id,
            "guild_id": interaction.guild.id
        })
        
        streak = 1
        if user_data and "last_daily" in user_data:
            last_daily = user_data["last_daily"]
            if datetime.utcnow() - last_daily <= timedelta(hours=48):  # Within 48 hours = streak continues
                streak = user_data.get("daily_streak", 1) + 1
        
        # Streak bonus (up to 7 days)
        streak_bonus = min(streak - 1, 6) * 50
        total_reward += streak_bonus
        
        # Update balance and daily info
        new_balance = await self.update_balance(interaction.user.id, interaction.guild.id, total_reward)
        
        await self.bot.db.economy.update_one(
            {"user_id": interaction.user.id, "guild_id": interaction.guild.id},
            {
                "$set": {
                    "last_daily": datetime.utcnow(),
                    "daily_streak": streak
                }
            },
            upsert=True
        )
        
        embed = EmbedBuilder.create(
            title="🎁 Daily Reward Claimed!",
            description=f"You received **{total_reward:,}** Nova Coins!",
            color=discord.Color.from_rgb(240, 230, 140)
        )
        
        embed.add_field(name="Base Reward", value=f"{base_reward:,} coins", inline=True)
        if bonus > 0:
            embed.add_field(name="Bonus", value=f"{bonus:,} coins", inline=True)
        if streak_bonus > 0:
            embed.add_field(name="Streak Bonus", value=f"{streak_bonus:,} coins", inline=True)
        
        embed.add_field(name="Daily Streak", value=f"{streak} day{'s' if streak != 1 else ''}", inline=True)
      
      embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="work", description="💼 Work to earn money")
    async def work(self, interaction: discord.Interaction):
        """Work to earn money"""
        # Check cooldown (1 hour)
        user_data = await self.bot.db.economy.find_one({
            "user_id": interaction.user.id,
            "guild_id": interaction.guild.id
        })
        
        if user_data and "last_work" in user_data:
            last_work = user_data["last_work"]
            if datetime.utcnow() - last_work < timedelta(hours=1):
                time_left = timedelta(hours=1) - (datetime.utcnow() - last_work)
                minutes = int(time_left.total_seconds() // 60)
                
                embed = EmbedBuilder.error(f"You're too tired to work right now!\nTry again in {minutes} minutes.")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Work scenarios
        jobs = [
            ("You delivered packages for Nova Express", random.randint(100, 250)),
            ("You helped at the local café", random.randint(80, 200)),
            ("You walked dogs in the park", random.randint(60, 150)),
            ("You did freelance coding", random.randint(150, 300)),
            ("You tutored someone in Discord", random.randint(90, 180)),
            ("You cleaned windows downtown", random.randint(70, 160)),
            ("You helped an elderly neighbor", random.randint(50, 120)),
            ("You organized a local event", random.randint(200, 400)),
        ]
        
        job_description, earnings = random.choice(jobs)
        
        # Update balance and work time
        new_balance = await self.update_balance(interaction.user.id, interaction.guild.id, earnings)
        
        await self.bot.db.economy.update_one(
            {"user_id": interaction.user.id, "guild_id": interaction.guild.id},
            {"$set": {"last_work": datetime.utcnow()}},
            upsert=True
        )
        
        embed = EmbedBuilder.create(
            title="💼 Work Complete!",
            description=job_description,
            color=discord.Color.from_rgb(144, 238, 144)
        )
        embed.add_field(name="Earned", value=f"{earnings:,} coins", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="gamble", description="🎲 Gamble your coins (risky!)")
    @app_commands.describe(amount="Amount to gamble")
    async def gamble(self, interaction: discord.Interaction, amount: int):
        """Gamble coins"""
        if amount < 10:
            embed = EmbedBuilder.error("Minimum bet is 10 coins!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if amount > 10000:
            embed = EmbedBuilder.error("Maximum bet is 10,000 coins!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        current_balance = await self.get_user_balance(interaction.user.id, interaction.guild.id)
        
        if amount > current_balance:
            embed = EmbedBuilder.error(f"You don't have enough coins! You have {current_balance:,} coins.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Gambling logic (45% win chance)
        win = random.random() < 0.45
        
        if win:
            # Win 1.5x to 2x the bet
            multiplier = random.uniform(1.5, 2.0)
            winnings = int(amount * multiplier) - amount
            new_balance = await self.update_balance(interaction.user.id, interaction.guild.id, winnings)
            
            embed = EmbedBuilder.create(
                title="🎉 You Won!",
                description=f"Lucky you! You won **{winnings:,}** coins!",
                color=discord.Color.green()
            )
            embed.add_field(name="Bet", value=f"{amount:,} coins", inline=True)
            embed.add_field(name="Won", value=f"{winnings:,} coins", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
        else:
            new_balance = await self.update_balance(interaction.user.id, interaction.guild.id, -amount)
            
            embed = EmbedBuilder.create(
                title="💸 You Lost!",
                description=f"Better luck next time! You lost **{amount:,}** coins.",
                color=discord.Color.red()
            )
            embed.add_field(name="Lost", value=f"{amount:,} coins", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="give", description="💝 Give coins to another user")
    @app_commands.describe(
        user="User to give coins to",
        amount="Amount of coins to give"
    )
    async def give(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        """Give coins to another user"""
        if user == interaction.user:
            embed = EmbedBuilder.error("You can't give coins to yourself!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if user.bot:
            embed = EmbedBuilder.error("You can't give coins to bots!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if amount < 1:
            embed = EmbedBuilder.error("You must give at least 1 coin!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        current_balance = await self.get_user_balance(interaction.user.id, interaction.guild.id)
        
        if amount > current_balance:
            embed = EmbedBuilder.error(f"You don't have enough coins! You have {current_balance:,} coins.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Transfer coins
        sender_balance = await self.update_balance(interaction.user.id, interaction.guild.id, -amount)
        receiver_balance = await self.update_balance(user.id, interaction.guild.id, amount)
        
        embed = EmbedBuilder.create(
            title="💝 Coins Transferred!",
            description=f"{interaction.user.mention} gave **{amount:,}** coins to {user.mention}!",
            color=discord.Color.from_rgb(255, 182, 193)
        )
        embed.add_field(name="Your Balance", value=f"{sender_balance:,} coins", inline=True)
        embed.add_field(name=f"{user.display_name}'s Balance", value=f"{receiver_balance:,} coins", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="🏆 View the server's richest users")
    async def leaderboard(self, interaction: discord.Interaction):
        """Show economy leaderboard"""
        await interaction.response.defer()
        
        # Get top 10 users by balance
        cursor = self.bot.db.economy.find(
            {"guild_id": interaction.guild.id}
        ).sort("balance", -1).limit(10)
        
        users = await cursor.to_list(length=10)
        
        if not users:
            embed = EmbedBuilder.create(
                title="🏆 Economy Leaderboard",
                description="No one has earned coins yet! Use `/daily` or `/work` to get started!",
                color=discord.Color.from_rgb(255, 215, 0)
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = EmbedBuilder.create(
            title="🏆 Economy Leaderboard",
            description="The richest users in this server!",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        
        leaderboard_text = ""
        for i, user_data in enumerate(users, 1):
            try:
                user = self.bot.get_user(user_data["user_id"])
                if user:
                    if i == 1:
                        emoji = "🥇"
                    elif i == 2:
                        emoji = "🥈"
                    elif i == 3:
                        emoji = "🥉"
                    else:
                        emoji = f"{i}."
                    
                    balance = user_data["balance"]
                    leaderboard_text += f"{emoji} **{user.display_name}** - {balance:,} coins\n"
            except:
                continue
        
        if leaderboard_text:
            embed.add_field(name="Top Users", value=leaderboard_text, inline=False)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="shop", description="🛒 View or buy items from the shop")
    async def shop(self, interaction: discord.Interaction):
        """View the shop (placeholder implementation)"""
        embed = EmbedBuilder.create(
            title="🛒 Nova Shop",
            description="Welcome to the Nova Shop! (Coming Soon)",
            color=discord.Color.from_rgb(240, 230, 140)
        )
        
        # Placeholder shop items
        shop_items = [
            {"name": "🌟 VIP Role", "price": 50000, "description": "Get a special VIP role!"},
            {"name": "🎨 Custom Color", "price": 25000, "description": "Choose your role color!"},
            {"name": "💝 Gift Box", "price": 10000, "description": "Random rewards inside!"},
            {"name": "🏆 Trophy", "price": 15000, "description": "Show off your wealth!"},
            {"name": "🌸 Nova Badge", "price": 5000, "description": "Cute Nova badge for your profile!"},
        ]
        
        shop_text = ""
        for item in shop_items:
            shop_text += f"**{item['name']}** - {item['price']:,} coins\n{item['description']}\n\n"
        
        embed.add_field(name="Available Items", value=shop_text, inline=False)
        embed.add_field(
            name="Note", 
            value="Shop functionality is coming soon! Items will be purchasable in a future update.", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Economy(bot))
