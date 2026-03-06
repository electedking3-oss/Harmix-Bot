# Create completely fixed version with proper voice state handling
# The issue is that the bot connects then leaves - this is usually because
# the voice state isn't being maintained or there's an issue with the player

harmix_v3 = '''import discord
from discord.ext import commands
import wavelink
import asyncio
import time
import os
import sys
import platform
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

# =============================================================================
# ========================= HARMIX BOT CONFIGURATION ==========================
# =============================================================================

load_dotenv()
TOKEN = os.getenv("TOKEN")

LAVALINK_HOST = "lavalinkv4.serenetia.com"
LAVALINK_PORT = 443
LAVALINK_PASSWORD = "https://dsc.gg/ajidevserver"

# -------------------- DEBUGGING --------------------
DEBUG_MODE = True

# -------------------- AUDIO SETTINGS --------------------
VOLUME_ON_JOIN = 65
MAX_VOLUME = 200

CUSTOM_EQ_BANDS = [
    {"band": 0, "gain": 0.25}, {"band": 1, "gain": 0.20},
    {"band": 2, "gain": 0.15}, {"band": 3, "gain": 0.10},
    {"band": 4, "gain": -0.05}, {"band": 5, "gain": 0.0},
    {"band": 6, "gain": 0.0}, {"band": 7, "gain": 0.05},
    {"band": 8, "gain": 0.10}, {"band": 9, "gain": 0.12},
    {"band": 10, "gain": 0.10}, {"band": 11, "gain": 0.08},
    {"band": 12, "gain": 0.05}, {"band": 13, "gain": 0.02},
    {"band": 14, "gain": 0.0},
]

FILTERS_VOLUME = 0.65
TIMESCALE_SPEED = 1.0
TIMESCALE_PITCH = 1.0
TIMESCALE_RATE = 1.0
ENABLE_KARAOKE = False
ENABLE_TREMOLO = False
ENABLE_VIBRATO = False
ENABLE_ROTATION = False
ENABLE_DISTORTION = False
ENABLE_LOW_PASS = False
LEFT_TO_LEFT = 1.0
LEFT_TO_RIGHT = 0.0
RIGHT_TO_LEFT = 0.0
RIGHT_TO_RIGHT = 1.0

ACTIVITY_TYPE = discord.ActivityType.listening
ACTIVITY_TEXT = "/help | Audiophile Quality"
COLOR_NOW_PLAYING = 0x00ff88
COLOR_QUEUE = 0x7289da
COLOR_PAUSED = 0xffaa00
COLOR_STOPPED = 0xff0000

# =============================================================================
# ======================== END OF CONFIGURATION ===============================
# =============================================================================

bot_stats = {
    "start_time": time.time(),
    "commands_synced": 0,
    "total_servers": 0,
    "voice_connections": 0,
    "tracks_played": 0,
    "failed_connections": 0,
    "lavalink_connected": False,
    "current_streams": 0
}

def log(msg: str, level: str = "INFO"):
    if DEBUG_MODE or level in ["ERROR", "WARN"]:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")

# CRITICAL: Proper intents for voice
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # REQUIRED for voice
intents.guilds = True  # REQUIRED for guild info

class HarmixBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.loop_mode = {}
        
    async def setup_hook(self):
        log("🚀 Starting Harmix v3.0...", "START")
        log(f"🎯 Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        log(f"💻 Platform: {platform.system()} {platform.release()}")
        
        # Connect Lavalink with better error handling
        try:
            node = wavelink.Node(
                uri=f"wss://{LAVALINK_HOST}:{LAVALINK_PORT}",
                password=LAVALINK_PASSWORD
            )
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
            bot_stats["lavalink_connected"] = True
            log("✅ Lavalink connected")
        except Exception as e:
            log(f"❌ Lavalink failed: {e}", "ERROR")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            bot_stats["commands_synced"] = len(synced)
            log(f"✅ Synced {len(synced)} commands")
        except Exception as e:
            log(f"⚠️ Sync error: {e}", "WARN")
        
        # Start monitor
        self.loop.create_task(self.monitor_loop())
        
    async def on_ready(self):
        bot_stats["total_servers"] = len(self.guilds)
        log("=" * 50, "READY")
        log(f"🎶 Harmix ONLINE | {self.user}", "READY")
        log(f"📡 Latency: {round(self.latency * 1000)}ms", "READY")
        log(f"🌐 Servers: {len(self.guilds)}", "READY")
        log(f"⚡ Commands: {bot_stats['commands_synced']}", "READY")
        log("=" * 50, "READY")
        await self.change_presence(activity=discord.Activity(type=ACTIVITY_TYPE, name=ACTIVITY_TEXT))
        
    async def monitor_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                active = sum(1 for g in self.guilds if g.voice_client)
                bot_stats["current_streams"] = active
                log(f"📊 Latency: {round(self.latency * 1000)}ms | Voice: {active} | Servers: {len(self.guilds)}")
            except:
                pass
            await asyncio.sleep(30)

bot = HarmixBot()

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

async def apply_audio_settings(player: wavelink.Player):
    try:
        filters = wavelink.Filters()
        filters.volume = FILTERS_VOLUME
        filters.equalizer = wavelink.Equalizer(name="Custom_EQ", bands=CUSTOM_EQ_BANDS)
        filters.timescale = wavelink.Timescale(speed=TIMESCALE_SPEED, pitch=TIMESCALE_PITCH, rate=TIMESCALE_RATE)
        
        if ENABLE_KARAOKE:
            filters.karaoke = wavelink.Karaoke(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
        if ENABLE_TREMOLO:
            filters.tremolo = wavelink.Tremolo(frequency=5.0, depth=0.5)
        if ENABLE_VIBRATO:
            filters.vibrato = wavelink.Vibrato(frequency=5.0, depth=0.5)
        if ENABLE_ROTATION:
            filters.rotation = wavelink.Rotation(speed=0.0)
        if ENABLE_DISTORTION:
            filters.distortion = wavelink.Distortion(sin_offset=0.0, sin_scale=1.0, cos_offset=0.0, cos_scale=1.0, tan_offset=0.0, tan_scale=1.0, offset=0.0, scale=1.0)
            
        filters.channel_mix = wavelink.ChannelMix(left_to_left=LEFT_TO_LEFT, left_to_right=LEFT_TO_RIGHT, right_to_left=RIGHT_TO_LEFT, right_to_right=RIGHT_TO_RIGHT)
        
        if ENABLE_LOW_PASS:
            filters.low_pass = wavelink.LowPass(smoothing=0.0)
            
        await player.set_filters(filters)
    except Exception as e:
        log(f"⚠️ Filters error: {e}", "ERROR")

# ============== EVENTS ==============
@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    log(f"🎵 Node ready: {payload.node.uri}")

@bot.event
async def on_wavelink_track_start(payload: wavelink.TrackStartEventPayload):
    player = payload.player
    track = payload.track
    bot_stats["tracks_played"] += 1
    log(f"▶️ Playing: '{track.title}'")
    
    if hasattr(player, 'home') and player.home:
        embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=COLOR_NOW_PLAYING)
        embed.add_field(name="👤 Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="⏱️ Duration", value=format_duration(track.length), inline=True)
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        try:
            await player.home.send(embed=embed)
        except:
            pass

@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player = payload.player
    track = payload.track
    
    if bot.loop_mode.get(player.guild.id) == "track":
        await player.queue.put_wait(track)
    
    if not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)
        await apply_audio_settings(player)
    else:
        # Auto-disconnect when queue empty (optional - remove if you want it to stay)
        pass

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """Handle voice state updates - check if bot is alone"""
    if member.id == bot.user.id:
        return
    
    # Check if bot is in a voice channel
    if not member.guild.voice_client:
        return
    
    voice_channel = member.guild.voice_client.channel
    if not voice_channel:
        return
    
    # Count non-bot members
    members = [m for m in voice_channel.members if not m.bot]
    
    # If alone, disconnect after 30 seconds
    if len(members) == 0 and before.channel and not after.channel:
        log(f"👋 Alone in {voice_channel.name}, disconnecting in 30s...")
        await asyncio.sleep(30)
        
        # Check again
        if member.guild.voice_client:
            current_members = [m for m in voice_channel.members if not m.bot]
            if len(current_members) == 0:
                await member.guild.voice_client.disconnect()
                log("👋 Auto-disconnected (alone)")

# ============== FIXED VOICE CONNECTION ==============
async def get_voice_player(interaction: discord.Interaction, connect: bool = True) -> tuple[Optional[wavelink.Player], Optional[str]]:
    """
    Get or create voice player.
    Returns: (player, error_message)
    """
    guild_id = interaction.guild.id
    
    # Check existing player
    try:
        node = wavelink.Pool.get_node()
        existing = node.get_player(guild_id)
        if existing and existing.connected:
            # Check if user is in same channel
            if interaction.user.voice and interaction.user.voice.channel:
                if existing.channel.id != interaction.user.voice.channel.id:
                    # Move to new channel
                    log(f"🔄 Moving to {interaction.user.voice.channel.name}")
                    await existing.move_to(interaction.user.voice.channel)
            return existing, None
    except:
        pass
    
    if not connect:
        return None, "❌ Not connected!"
    
    # Need to connect
    if not interaction.user.voice:
        return None, "❌ **Join a voice channel first!**"
    
    channel = interaction.user.voice.channel
    
    # Check permissions
    permissions = channel.permissions_for(interaction.guild.me)
    if not permissions.connect or not permissions.speak:
        return None, "❌ **I need Connect and Speak permissions!**"
    
    # Disconnect any existing stale connection
    if interaction.guild.voice_client:
        try:
            await interaction.guild.voice_client.disconnect(force=True)
        except:
            pass
        await asyncio.sleep(0.5)
    
    # Connect with retry
    for attempt in range(3):
        try:
            log(f"🔄 Connecting to '{channel.name}' (attempt {attempt+1}/3)")
            
            player = await channel.connect(cls=wavelink.Player, self_deaf=True)
            
            # Wait for connection to establish
            await asyncio.sleep(1.5)
            
            # Verify
            if not player.connected:
                log(f"⚠️ Player not connected after attempt {attempt+1}")
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                return None, "❌ **Connection failed - check Voice State Intent!**"
            
            player.home = interaction.channel
            await player.set_volume(VOLUME_ON_JOIN)
            await apply_audio_settings(player)
            
            bot_stats["voice_connections"] += 1
            log(f"✅ Connected to {channel.name}")
            return player, None
            
        except Exception as e:
            error_str = str(e)
            log(f"❌ Connection error: {error_str}", "ERROR")
            
            if "timeout" in error_str.lower():
                if attempt < 2:
                    await asyncio.sleep(2)
                    continue
                return None, "❌ **Voice timeout!** Check: Developer Portal → Bot → Voice State Intent ON"
            
            if attempt == 2:
                bot_stats["failed_connections"] += 1
                return None, f"❌ **Connection failed:** {error_str}"
            
            await asyncio.sleep(1)
    
    return None, "❌ **Unknown error**"

# ============== COMMANDS ==============
@bot.tree.command(name="help", description="📖 Show commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🎶 Harmix", description="Premium music bot", color=COLOR_QUEUE)
    cmds = [
        ("🎵 `/play <query>`", "Play music"),
        ("⏸️ `/pause`", "Pause"),
        ("▶️ `/resume`", "Resume"),
        ("⏭️ `/skip`", "Skip"),
        ("📋 `/queue`", "Queue"),
        ("🎧 `/nowplaying`", "Current"),
        (f"🔊 `/volume <0-{MAX_VOLUME}>`", "Volume"),
        ("🔁 `/loop`", "Loop"),
        ("📊 `/stats`", "Stats"),
        ("⏹️ `/stop`", "Stop"),
        ("👋 `/disconnect`", "Disconnect"),
    ]
    for n, v in cmds:
        embed.add_field(name=n, value=v, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stats", description="📊 Bot stats")
async def stats_cmd(interaction: discord.Interaction):
    uptime = time.time() - bot_stats["start_time"]
    hours, rem = divmod(int(uptime), 3600)
    mins, secs = divmod(rem, 60)
    
    embed = discord.Embed(title="📊 Stats", color=COLOR_QUEUE)
    embed.add_field(name="Bot", value=f"Servers: {len(bot.guilds)}\\nLatency: {round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Audio", value=f"Tracks: {bot_stats['tracks_played']}\\nVoice: {bot_stats['current_streams']}", inline=True)
    embed.add_field(name="Uptime", value=f"{hours}h {mins}m {secs}s", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="play", description="🎵 Play music")
@discord.app_commands.describe(query="Song name or URL")
async def play(interaction: discord.Interaction, query: str):
    log(f"🎵 Play: '{query[:50]}...'")
    await interaction.response.defer(thinking=True)
    
    player, error = await get_voice_player(interaction, connect=True)
    if error:
        return await interaction.followup.send(error)
    
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
                    await apply_audio_settings(player)
                    embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=COLOR_NOW_PLAYING)
                    embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
                    embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
                    if track.artwork:
                        embed.set_thumbnail(url=track.artwork)
                    await interaction.followup.send(embed=embed)
                else:
                    await player.queue.put_wait(track)
            await interaction.followup.send(f"📋 Added {len(tracks.tracks)} tracks")
        else:
            track = tracks[0]
            if not player.playing:
                await player.play(track)
                await apply_audio_settings(player)
                title, color = "🎵 Now Playing", COLOR_NOW_PLAYING
            else:
                await player.queue.put_wait(track)
                title, color = "📝 Added", COLOR_QUEUE
            
            embed = discord.Embed(title=title, description=f"**[{track.title}]({track.uri})**", color=color)
            embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
            embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
            await interaction.followup.send(embed=embed)
            
    except Exception as e:
        log(f"❌ Play error: {e}", "ERROR")
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="pause", description="⏸️ Pause")
async def pause(interaction: discord.Interaction):
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    if not player.playing:
        return await interaction.response.send_message("❌ Not playing!", ephemeral=True)
    await player.pause(True)
    await interaction.response.send_message(embed=discord.Embed(title="⏸️ Paused", color=COLOR_PAUSED))

@bot.tree.command(name="resume", description="▶️ Resume")
async def resume(interaction: discord.Interaction):
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    if not player.paused:
        return await interaction.response.send_message("❌ Not paused!", ephemeral=True)
    await player.pause(False)
    await interaction.response.send_message(embed=discord.Embed(title="▶️ Resumed", color=COLOR_NOW_PLAYING))

@bot.tree.command(name="skip", description="⏭️ Skip")
async def skip(interaction: discord.Interaction):
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    if not player.playing:
        return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
    await player.skip()
    await interaction.response.send_message(embed=discord.Embed(title="⏭️ Skipped", color=COLOR_QUEUE))

@bot.tree.command(name="queue", description="📋 Queue")
async def queue(interaction: discord.Interaction):
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    if player.queue.is_empty and not player.current:
        return await interaction.response.send_message("📭 Empty!", ephemeral=True)
    
    embed = discord.Embed(title="📋 Queue", color=COLOR_QUEUE)
    if player.current:
        embed.add_field(name="Now Playing", value=f"**{player.current.title}**", inline=False)
    if not player.queue.is_empty:
        q = "\\n".join([f"`{i+1}.` {t.title[:45]}" for i, t in enumerate(list(player.queue)[:10])])
        embed.add_field(name=f"Up Next ({len(player.queue)})", value=q, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="🎧 Current")
async def nowplaying(interaction: discord.Interaction):
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    if not player.current:
        return await interaction.response.send_message("❌ Nothing playing!", ephemeral=True)
    
    track = player.current
    embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=COLOR_NOW_PLAYING)
    embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
    embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="volume", description=f"🔊 Volume (0-{MAX_VOLUME})")
async def volume(interaction: discord.Interaction, volume: int):
    if not 0 <= volume <= MAX_VOLUME:
        return await interaction.response.send_message(f"❌ 0-{MAX_VOLUME}!", ephemeral=True)
    
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    
    await player.set_volume(volume)
    emoji = "🔇" if volume == 0 else "🔈" if volume < 30 else "🔉" if volume < 70 else "🔊"
    await interaction.response.send_message(embed=discord.Embed(title=f"{emoji} {volume}%", color=COLOR_QUEUE))

@bot.tree.command(name="loop", description="🔁 Loop")
@discord.app_commands.choices(mode=[
    discord.app_commands.Choice(name="⏹️ Off", value="off"),
    discord.app_commands.Choice(name="🔂 Track", value="track"),
    discord.app_commands.Choice(name="🔁 Queue", value="queue")
])
async def loop(interaction: discord.Interaction, mode: discord.app_commands.Choice[str]):
    bot.loop_mode[interaction.guild.id] = mode.value
    desc = {"off": "Off", "track": "Track repeat", "queue": "Queue repeat"}
    await interaction.response.send_message(embed=discord.Embed(title=f"{get_loop_emoji(mode.value)} {mode.name}", description=desc[mode.value], color=COLOR_QUEUE))

@bot.tree.command(name="stop", description="⏹️ Stop")
async def stop(interaction: discord.Interaction):
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    
    player.queue.clear()
    bot.loop_mode[interaction.guild.id] = "off"
    await player.stop()
    await interaction.response.send_message(embed=discord.Embed(title="⏹️ Stopped", color=COLOR_STOPPED))

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction: discord.Interaction):
    player, error = await get_voice_player(interaction, connect=False)
    if error:
        return await interaction.response.send_message(error, ephemeral=True)
    
    await player.disconnect()
    bot_stats["current_streams"] = max(0, bot_stats["current_streams"] - 1)
    await interaction.response.send_message(embed=discord.Embed(title="👋 Disconnected", color=COLOR_QUEUE))

log("=" * 50)
log("🎶 HARMIX v3.0 - VOICE CONNECTION STABLE")
log("=" * 50)

bot.run(TOKEN)
'''

with open('/mnt/kimi/output/harmix_v3.py', 'w', encoding='utf-8') as f:
    f.write(harmix_v3)
