import discord
from discord.ext import commands
import wavelink
import asyncio
import time
from typing import Optional

# ============== CONFIGURATION ==============
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv("TOKEN")

LAVALINK_HOST = "lavalinkv4.serenetia.com"
LAVALINK_PORT = 443
LAVALINK_PASSWORD = "https://dsc.gg/ajidevserver"

# ============== INTENTS & BOT SETUP ==============
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class HarmixBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        self.loop_mode = {}
        self.user_playlists = {}
        self.start_time = time.time()
        
    async def setup_hook(self):
        node = wavelink.Node(
            uri=f"wss://{LAVALINK_HOST}:{LAVALINK_PORT}",
            password=LAVALINK_PASSWORD
        )
        await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
        synced = await self.tree.sync()
    
    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/help | Audiophile Quality"
            )
        )

bot = HarmixBot()

# ============== OPTIMIZED 256k AUDIO SETTINGS ==============
# Professional-grade EQ optimized for 256k bitrate streaming
EQ_BANDS = [
    # Sub-bass (20-60Hz) - Slight boost for depth without muddiness
    {"band": 0, "gain": 0.25}, {"band": 1, "gain": 0.2},
    # Bass (60-250Hz) - Controlled warmth
    {"band": 2, "gain": 0.15}, {"band": 3, "gain": 0.1},
    # Low-mids (250-500Hz) - Clarity cut to reduce boominess
    {"band": 4, "gain": -0.05},
    # Mids (500Hz-2kHz) - Flat for natural vocals
    {"band": 5, "gain": 0.0}, {"band": 6, "gain": 0.0},
    # High-mids (2-4kHz) - Slight presence boost
    {"band": 7, "gain": 0.05},
    # Presence (4-6kHz) - Clarity for vocals
    {"band": 8, "gain": 0.1},
    # Brilliance (6-8kHz) - Air and detail
    {"band": 9, "gain": 0.12},
    # High treble (8-10kHz) - Sparkle
    {"band": 10, "gain": 0.1},
    # Very high (10-12kHz) - Detail
    {"band": 11, "gain": 0.08},
    # Ultra-high (12-14kHz) - Air
    {"band": 12, "gain": 0.05},
    # Top (14-16kHz) - Gentle roll-off to prevent fatigue
    {"band": 13, "gain": 0.02},
    # Extreme high (16-20kHz) - Subtle presence
    {"band": 14, "gain": 0.0},
]

def format_duration(ms: int) -> str:
    if ms is None or ms < 0:
        return "Unknown"
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    if hours > 0:
        return f"{hours}:{minutes % 60:02d}:{seconds % 60:02d}"
    return f"{minutes}:{seconds % 60:02d}"

def get_loop_emoji(mode: str) -> str:
    return {"off": "⏹️", "track": "🔂", "queue": "🔁"}.get(mode, "⏹️")

def detect_source(query: str) -> str:
    q = query.lower()
    if "spotify.com" in q:
        return "spotify"
    elif "music.apple.com" in q or "apple.co" in q:
        return "applemusic"
    return "youtube"

async def apply_audiophile_settings(player: wavelink.Player):
    """Apply optimized 256k bitrate audio settings"""
    try:
        filters = wavelink.Filters()
        
        # Volume at 0.65 (65%) for 256k - prevents clipping while maintaining dynamic range
        filters.volume = 0.65
        
        # Apply optimized equalizer
        filters.equalizer = wavelink.Equalizer(name="256k_Optimized", bands=EQ_BANDS)
        
        # Timescale for pitch accuracy
        filters.timescale = wavelink.Timescale(speed=1.0, pitch=1.0, rate=1.0)
        
        # Disable all effects for clean 256k
        filters.karaoke = None
        filters.tremolo = None
        filters.vibrato = None
        filters.rotation = None
        filters.distortion = None
        
        # Pure stereo channel mix
        filters.channel_mix = wavelink.ChannelMix(
            left_to_left=1.0, left_to_right=0.0,
            right_to_left=0.0, right_to_right=1.0
        )
        
        # Full frequency range for 256k
        filters.low_pass = None
        
        await player.set_filters(filters)
    except:
        pass

# ============== EVENTS ==============
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    pass

@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload):
    player = payload.player
    track = payload.track
    
    if player.home:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{track.title}]({track.uri})**",
            color=0x00ff88
        )
        embed.add_field(name="👤 Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="⏱️ Duration", value=format_duration(track.length), inline=True)
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await player.home.send(embed=embed)

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player = payload.player
    track = payload.track
    
    if bot.loop_mode.get(player.guild.id) == "track":
        await player.queue.put_wait(track)
    
    if not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)
        await apply_audiophile_settings(player)

# ============== COMMANDS ==============
@bot.tree.command(name="help", description="📖 Show all Harmix commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎶 Harmix Music Bot",
        description="Premium 256k audiophile-grade music bot",
        color=0x7289da
    )
    cmds = [
        ("🎵 `/play <query>`", "Play music from URL or search"),
        ("⏸️ `/pause`", "Pause playback"),
        ("▶️ `/resume`", "Resume playback"),
        ("⏭️ `/skip`", "Skip track"),
        ("📋 `/queue`", "View queue"),
        ("🎧 `/nowplaying`", "Current track info"),
        ("🔊 `/volume <0-200>`", "Adjust volume (max 200%)"),
        ("🔁 `/loop <mode>`", "Loop: off/track/queue"),
        ("⏹️ `/stop`", "Stop and clear"),
        ("👋 `/disconnect`", "Disconnect bot"),
    ]
    for n, v in cmds:
        embed.add_field(name=n, value=v, inline=False)
    
    embed.add_field(
        name="🎧 Audio Features",
        value="• Optimized for 256k bitrate\n• Professional EQ curve\n• Max volume: 200%\n• Audiophile-grade processing",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="play", description="🎵 Play music from YouTube, Spotify, or Apple Music")
@discord.app_commands.describe(query="Song name or URL")
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a voice channel first!", ephemeral=True)
    
    await interaction.response.defer(thinking=True)
    
    player = interaction.guild.voice_client
    if not player:
        player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        player.home = interaction.channel
        await apply_audiophile_settings(player)
    
    source = detect_source(query)
    
    try:
        if source == "spotify":
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.Spotify)
        elif source == "applemusic":
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.AppleMusic)
        else:
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
        
        if not tracks:
            return await interaction.followup.send("❌ No tracks found!")
        
        if isinstance(tracks, wavelink.Playlist):
            for i, track in enumerate(tracks.tracks):
                if not player.playing and i == 0:
                    await player.play(track)
                    await apply_audiophile_settings(player)
                else:
                    await player.queue.put_wait(track)
            await interaction.followup.send(f"📋 Added **{len(tracks.tracks)}** tracks from playlist")
        else:
            track = tracks[0]
            if not player.playing:
                await player.play(track)
                await apply_audiophile_settings(player)
                title, color = "🎵 Now Playing", 0x00ff88
            else:
                await player.queue.put_wait(track)
                title, color = "📝 Added to Queue", 0x7289da
            
            embed = discord.Embed(title=title, description=f"**[{track.title}]({track.uri})**", color=color)
            embed.add_field(name="👤 Artist", value=track.author or "Unknown", inline=True)
            embed.add_field(name="⏱️ Duration", value=format_duration(track.length), inline=True)
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="pause", description="⏸️ Pause the current track")
async def pause(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player or not player.playing:
        return await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
    await player.pause(True)
    await interaction.response.send_message(embed=discord.Embed(title="⏸️ Paused", color=0xffaa00))

@bot.tree.command(name="resume", description="▶️ Resume playback")
async def resume(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player or not player.paused:
        return await interaction.response.send_message("❌ Not paused!", ephemeral=True)
    await player.pause(False)
    await interaction.response.send_message(embed=discord.Embed(title="▶️ Resumed", color=0x00ff88))

@bot.tree.command(name="skip", description="⏭️ Skip to the next track")
async def skip(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player or not player.playing:
        return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
    await player.skip()
    await interaction.response.send_message(embed=discord.Embed(title="⏭️ Skipped", color=0x7289da))

@bot.tree.command(name="queue", description="📋 View the current queue")
async def queue(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player or (player.queue.is_empty and not player.current):
        return await interaction.response.send_message("📭 Queue is empty!", ephemeral=True)
    
    embed = discord.Embed(title="📋 Music Queue", color=0x7289da)
    if player.current:
        embed.add_field(name="🎵 Now Playing", value=f"**{player.current.title}**", inline=False)
    if not player.queue.is_empty:
        q_text = "\n".join([f"`{i+1}.` {t.title[:50]}" for i, t in enumerate(list(player.queue)[:10])])
        embed.add_field(name=f"📝 Up Next ({len(player.queue)} tracks)", value=q_text, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="🎧 Show currently playing track")
async def nowplaying(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player or not player.current:
        return await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
    
    track = player.current
    embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=0x00ff88)
    embed.add_field(name="👤 Artist", value=track.author or "Unknown", inline=True)
    embed.add_field(name="⏱️ Duration", value=format_duration(track.length), inline=True)
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="volume", description="🔊 Adjust volume (0-200)")
@discord.app_commands.describe(volume="Volume level 0-200 (default 100)")
async def volume(interaction: discord.Interaction, volume: int):
    # Max volume changed to 200
    if not 0 <= volume <= 200:
        return await interaction.response.send_message("❌ Volume must be 0-200!", ephemeral=True)
    
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    
    await player.set_volume(volume)
    
    # Volume emoji mapping
    if volume == 0:
        emoji, desc = "🔇", "Muted"
    elif volume <= 30:
        emoji, desc = "🔈", "Quiet"
    elif volume <= 65:
        emoji, desc = "🔉", "Normal (Optimal for 256k)"
    elif volume <= 100:
        emoji, desc = "🔊", "Loud"
    elif volume <= 150:
        emoji, desc = "🎧", "Very Loud"
    else:
        emoji, desc = "⚠️", "Maximum (May cause distortion)"
    
    embed = discord.Embed(
        title=f"{emoji} Volume: {volume}%",
        description=f"**{desc}**",
        color=0x7289da
    )
    
    if volume > 100:
        embed.add_field(
            name="⚠️ Warning",
            value="Volume above 100% may reduce audio quality",
            inline=False
        )
    elif 60 <= volume <= 70:
        embed.set_footer(text="✅ Sweet spot for 256k bitrate")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="loop", description="🔁 Set loop mode")
@discord.app_commands.choices(mode=[
    discord.app_commands.Choice(name="⏹️ Off", value="off"),
    discord.app_commands.Choice(name="🔂 Track", value="track"),
    discord.app_commands.Choice(name="🔁 Queue", value="queue")
])
async def loop(interaction: discord.Interaction, mode: discord.app_commands.Choice[str]):
    bot.loop_mode[interaction.guild.id] = mode.value
    desc = {"off": "Looping disabled", "track": "Current track will repeat", "queue": "Queue will repeat"}
    await interaction.response.send_message(embed=discord.Embed(title=f"{get_loop_emoji(mode.value)} Loop: {mode.name}", description=desc[mode.value], color=0x7289da))

@bot.tree.command(name="stop", description="⏹️ Stop playback and clear queue")
async def stop(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    player.queue.clear()
    bot.loop_mode[interaction.guild.id] = "off"
    await player.stop()
    await interaction.response.send_message(embed=discord.Embed(title="⏹️ Stopped", color=0xff0000))

@bot.tree.command(name="disconnect", description="👋 Disconnect the bot")
async def disconnect(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    await player.disconnect()
    await interaction.response.send_message(embed=discord.Embed(title="👋 Disconnected", color=0x7289da))

bot.run(TOKEN)
