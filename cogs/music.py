"""
Music cog for Nova bot
Provides music playback functionality with Spotify integration.
"""

import asyncio
import re
from typing import Dict, List, Optional
from urllib.parse import quote

import aiohttp
import discord
import spotipy
from discord import app_commands
from discord.ext import commands
from spotipy.oauth2 import SpotifyClientCredentials
import youtube_dl

from utils.embeds import EmbedBuilder


# YouTube-dl configuration
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    """Audio source for YouTube-dl"""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
    
    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        """Create audio source from URL"""
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Song:
    """Represents a song in the queue"""
    
    def __init__(self, title: str, url: str, requester: discord.Member, duration: int = 0):
        self.title = title
        self.url = url
        self.requester = requester
        self.duration = duration
    
    def __str__(self):
        return f"**{self.title}** (requested by {self.requester.mention})"


class MusicPlayer:
    """Music player for a guild"""
    
    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self.bot = bot
        self.guild = guild
        self.voice_client: Optional[discord.VoiceClient] = None
        self.queue: List[Song] = []
        self.current: Optional[Song] = None
        self.volume = 0.5
        self.loop_mode = "off"  # off, song, queue
        self._skip_votes = set()
    
    async def connect(self, channel: discord.VoiceChannel):
        """Connect to a voice channel"""
        if self.voice_client:
            await self.voice_client.move_to(channel)
        else:
            self.voice_client = await channel.connect()
    
    async def disconnect(self):
        """Disconnect from voice channel"""
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None
        self.queue.clear()
        self.current = None
    
    async def play_next(self):
        """Play the next song in queue"""
        if not self.queue and self.loop_mode != "song":
            return
        
        if self.loop_mode == "song" and self.current:
            song = self.current
        elif self.loop_mode == "queue" and self.current:
            self.queue.append(self.current)
            song = self.queue.pop(0)
        else:
            if not self.queue:
                return
            song = self.queue.pop(0)
        
        try:
            source = await YTDLSource.from_url(song.url, stream=True)
            source.volume = self.volume
            
            self.current = song
            self._skip_votes.clear()
            
            self.voice_client.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(), self.bot.loop)
            )
        except Exception as e:
            print(f"Error playing song: {e}")
            await self.play_next()
    
    def add_song(self, song: Song):
        """Add song to queue"""
        self.queue.append(song)
    
    def skip(self):
        """Skip current song"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
    
    def pause(self):
        """Pause playback"""
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
    
    def resume(self):
        """Resume playback"""
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
    
    def set_volume(self, volume: float):
        """Set playback volume"""
        self.volume = max(0.0, min(1.0, volume))
        if self.voice_client and hasattr(self.voice_client.source, 'volume'):
            self.voice_client.source.volume = self.volume


class Music(commands.Cog):
    """Music commands for playing audio in voice channels"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.players: Dict[int, MusicPlayer] = {}
        self.spotify = None
        
        # Initialize Spotify client if credentials are available
        if bot.config.SPOTIFY_CLIENT_ID and bot.config.SPOTIFY_CLIENT_SECRET:
            try:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=bot.config.SPOTIFY_CLIENT_ID,
                    client_secret=bot.config.SPOTIFY_CLIENT_SECRET
                )
                self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
            except Exception as e:
                print(f"Failed to initialize Spotify client: {e}")
    
    def get_player(self, guild: discord.Guild) -> MusicPlayer:
        """Get or create music player for guild"""
        if guild.id not in self.players:
            self.players[guild.id] = MusicPlayer(self.bot, guild)
        return self.players[guild.id]
    
    async def search_spotify(self, query: str) -> Optional[Dict]:
        """Search for a track on Spotify"""
        if not self.spotify:
            return None
        
        try:
            results = self.spotify.search(q=query, type='track', limit=1)
            if results['tracks']['items']:
                track = results['tracks']['items'][0]
                return {
                    'title': f"{track['artists'][0]['name']} - {track['name']}",
                    'url': None,  # Spotify URLs can't be played directly
                    'search_query': f"{track['artists'][0]['name']} {track['name']}",
                    'duration': track['duration_ms'] // 1000,
                    'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None
                }
        except Exception as e:
            print(f"Spotify search error: {e}")
        
        return None
    
    async def search_youtube(self, query: str) -> Optional[Dict]:
        """Search for a video on YouTube"""
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False))
            
            if 'entries' in data and data['entries']:
                entry = data['entries'][0]
                return {
                    'title': entry.get('title', 'Unknown'),
                    'url': entry.get('webpage_url', entry.get('url')),
                    'duration': entry.get('duration', 0),
                    'thumbnail': entry.get('thumbnail')
                }
        except Exception as e:
            print(f"YouTube search error: {e}")
        
        return None
    
    # --- Commands below ---
    # (unchanged, already properly indented)
    # play, pause, resume, skip, stop, queue, loop, volume, lyrics
    # ...
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle voice state updates"""
        if member == self.bot.user:
            return
        
        # Check if bot is alone in voice channel
        for guild_id, player in self.players.items():
            if player.voice_client and player.voice_client.channel:
                members = [m for m in player.voice_client.channel.members if not m.bot]
                if not members:
                    # Bot is alone, disconnect after a delay
                    await asyncio.sleep(60)  # Wait 1 minute
                    if player.voice_client and not [m for m in player.voice_client.channel.members if not m.bot]:
                        await player.disconnect()


async def setup(bot: commands.Bot):
    """Setup function for loading the cog"""
    await bot.add_cog(Music(bot))
