"""
Permission checks for Nova bot
Provides decorators and functions for command permission checking.
"""

from typing import Callable, Union

import discord
from discord.ext import commands


def is_owner():
    """Check if user is bot owner"""
    async def predicate(ctx):
        return await ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


def has_permissions(**perms):
    """Check if user has specific permissions"""
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        
        permissions = ctx.channel.permissions_for(ctx.author)
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]
        
        if not missing:
            return True
        
        raise commands.MissingPermissions(missing)
    
    return commands.check(predicate)


def has_role(role_name: str):
    """Check if user has a specific role"""
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        
        if isinstance(ctx.author, discord.Member):
            role = discord.utils.get(ctx.author.roles, name=role_name)
            return role is not None
        
        return False
    
    return commands.check(predicate)


def has_any_role(*role_names):
    """Check if user has any of the specified roles"""
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        
        if isinstance(ctx.author, discord.Member):
            return any(discord.utils.get(ctx.author.roles, name=role_name) for role_name in role_names)
        
        return False
    
    return commands.check(predicate)


def is_in_guilds(*guild_ids):
    """Check if command is used in specific guilds"""
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id in guild_ids
    return commands.check(predicate)


def bot_has_permissions(**perms):
    """Check if bot has specific permissions"""
    async def predicate(ctx):
        permissions = ctx.channel.permissions_for(ctx.me)
        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]
        
        if not missing:
            return True
        
        raise commands.BotMissingPermissions(missing)
    
    return commands.check(predicate)


def is_mod():
    """Check if user is a moderator (has kick/ban permissions)"""
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        
        return (
            ctx.author.guild_permissions.kick_members or
            ctx.author.guild_permissions.ban_members or
            ctx.author.guild_permissions.manage_messages
        )
    
    return commands.check(predicate)


def is_admin():
    """Check if user is an administrator"""
    async def predicate(ctx):
        if await ctx.bot.is_owner(ctx.author):
            return True
        
        return (
            ctx.author.guild_permissions.administrator or
            ctx.author.guild_permissions.manage_guild
        )
    
    return commands.check(predicate)


# Interaction-based checks for slash commands
class InteractionChecks:
    """Checks for slash commands (app_commands)"""
    
    @staticmethod
    def has_permissions(**perms) -> Callable:
        """Check if user has permissions in an interaction"""
        def decorator(func):
            async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
                if not interaction.user.guild_permissions.administrator:
                    permissions = interaction.channel.permissions_for(interaction.user)
                    missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]
                    
                    if missing:
                        from utils.embeds import EmbedBuilder
                        missing_perms = ", ".join(perm.replace("_", " ").title() for perm in missing)
                        embed = EmbedBuilder.error(f"You need the following permissions: {missing_perms}")
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                
                return await func(self, interaction, *args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def is_owner() -> Callable:
        """Check if user is bot owner in an interaction"""
        def decorator(func):
            async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
                app_info = await interaction.client.application_info()
                if interaction.user.id != app_info.owner.id:
                    from utils.embeds import EmbedBuilder
                    embed = EmbedBuilder.error("This command is restricted to the bot owner!")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                return await func(self, interaction, *args, **kwargs)
            return wrapper
        return decorator
    
    @staticmethod
    def is_mod() -> Callable:
        """Check if user is a moderator in an interaction"""
        def decorator(func):
            async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
                is_moderator = (
                    interaction.user.guild_permissions.kick_members or
                    interaction.user.guild_permissions.ban_members or
                    interaction.user.guild_permissions.manage_messages or
                    interaction.user.guild_permissions.administrator
                )
                
                if not is_moderator:
                    from utils.embeds import EmbedBuilder
                    embed = EmbedBuilder.error("You need moderator permissions to use this command!")
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                
                return await func(self, interaction, *args, **kwargs)
            return wrapper
        return decorator


# Cooldown helpers
def cooldown(rate: int, per: float, type: commands.BucketType = commands.BucketType.user):
    """Apply cooldown to command"""
    return commands.cooldown(rate, per, type)


def max_concurrency(number: int, per: commands.BucketType = commands.BucketType.user, wait: bool = False):
    """Limit concurrent uses of command"""
    return commands.max_concurrency(number, per, wait)


# Custom error handling
class InsufficientPermissions(commands.CheckFailure):
    """Raised when user lacks required permissions"""
    pass


class NotModerator(commands.CheckFailure):
    """Raised when user is not a moderator"""
    pass


class NotAdministrator(commands.CheckFailure):
    """Raised when user is not an administrator"""
    pass
