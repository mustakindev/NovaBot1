"""
Configuration module for Nova bot
Loads environment variables and provides configuration constants.
"""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class holding all environment variables and constants"""
    
    # Discord
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    
    # Database
    MONGO_URL: str = os.getenv("MONGO_URL", "mongodb://localhost:27017/nova")
    
    # AI Services
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Music Services
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    
    # Support
    SUPPORT_SERVER: str = os.getenv("SUPPORT_SERVER", "https://discord.gg/D3jUAQSjJx")
    
    # Bot Configuration
    BOT_NAME: str = "Nova"
    BOT_VERSION: str = "1.0.0"
    
    # Embed Colors (Pastel Theme)
    COLORS = {
        "primary": 0xB19CD9,    # Lavender
        "success": 0x98FB98,    # Pale green
        "warning": 0xFFB6C1,    # Light pink
        "error": 0xFFCCCB,      # Light coral
        "info": 0x87CEEB,       # Sky blue
        "music": 0xDDA0DD,      # Plum
        "economy": 0xF0E68C,    # Khaki
    }
    
    # Emojis
    EMOJIS = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "music": "🎵",
        "loading": "⏳",
        "star": "⭐",
        "heart": "💖",
        "cherry": "🌸",
    }
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that required environment variables are set"""
        required = ["DISCORD_TOKEN"]
        missing = [var for var in required if not getattr(cls, var)]
        
        if missing:
            print(f"Missing required environment variables: {', '.join(missing)}")
            return False
        
        return True


# Validate configuration on import
if not Config.validate():
    exit(1)
