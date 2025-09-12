"""
Cogs package for Nova bot
Contains all command modules organized by functionality.
"""

# Import all cogs for easier access
from .moderation import Moderation
from .music import Music
from .ai_chat import AIChat
from .utility import Utility
from .fun import Fun
from .economy import Economy
from .tickets import Tickets
from .autoroles import Autoroles
from .logging_cog import Logging
from .leveling import Leveling
from .giveaways import Giveaways
from .custom import Custom

# List of all cog classes
ALL_COGS = [
    Moderation,
    Music,
    AIChat,
    Utility,
    Fun,
    Economy,
    Tickets,
    Autoroles,
    Logging,
    Leveling,
    Giveaways,
    Custom
]

__all__ = [
    'Moderation',
    'Music',
    'AIChat',
    'Utility',
    'Fun',
    'Economy',
    'Tickets',
    'Autoroles',
    'Logging',
    'Leveling',
    'Giveaways',
    'Custom',
    'ALL_COGS'
]
