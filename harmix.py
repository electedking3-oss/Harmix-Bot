import discord
from discord.ext import commands
import wavelink
import asyncio
import time
import os
from datetime import datetime
from dotenv import load_dotenv

# =============================================================================
# ========================= HARMIX BOT CONFIGURATION ==========================
# =============================================================================

load_dotenv()
TOKEN = os.getenv("TOKEN")

# -------------------- LAVALINK CONFIG --------------------
# Local Lavalink server on Termux
LAVALINK_HOST = "localhost"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "LkJhGfDsA19181716"  # Change this to match your application.yml
USE_SSL = False  # Set to False for local ws:// connection

# -------------------- DEBUGGING --------------------
DEBUG_MODE = True

def log(msg: str, level: str = "INFO"):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")

# -------------------- AUDIO CUSTOMIZATION --------------------
# Volume settings
VOLUME_ON_JOIN = 65
MAX_VOLUME = 200

# 15-Band Equalizer - Customize these values for your audio preference
# Band range: -0.25 to 1.0 (negative = cut, positive = boost)
CUSTOM_EQ_BANDS = [
    {"band": 0, "gain": 0.25},   # 20Hz - Sub-bass boost
    {"band": 1, "gain": 0.20},   # 40Hz - Deep bass
    {"band": 2, "gain": 0.15},   # 63Hz - Bass
    {"band": 3, "gain": 0.10},   # 100Hz - Low-mids
    {"band": 4, "gain": -0.05},  # 160Hz - Cut mud
    {"band": 5, "gain": 0.0},    # 250Hz - Flat
    {"band": 6, "gain": 0.0},    # 400Hz - Flat
    {"band": 7, "gain": 0.05},   # 630Hz - Slight presence
    {"band": 8, "gain": 0.10},   # 1kHz - Clarity
    {"band": 9, "gain": 0.12},   # 1.6kHz - Presence
    {"band": 10, "gain": 0.10},  # 2.5kHz - Brilliance
    {"band": 11, "gain": 0.08},  # 4kHz - Detail
    {"band": 12, "gain": 0.05},  # 6.3kHz - Air
    {"band": 13, "gain": 0.02},  # 10kHz - Sparkle
    {"band": 14, "gain": 0.0},   # 16kHz - Top end
]

# Filter settings - Enable/disable effects
FILTERS_VOLUME = 0.65        # Base volume for filters (0.0 - 1.0)
TIMESCALE_SPEED = 1.0        # Playback speed (0.5 - 2.0)
TIMESCALE_PITCH = 1.0        # Pitch shift (0.5 - 2.0)
TIMESCALE_RATE = 1.0         # Sample rate (0.5 - 2.0)

# Effect toggles - Set to True to enable
ENABLE_KARAOKE = False       # Removes vocals
ENABLE_TREMOLO = False       # Volume oscillation
ENABLE_VIBRATO = False       # Pitch oscillation
ENABLE_ROTATION = False      # Stereo rotation
ENABLE_DISTORTION = False    # Audio distortion
ENABLE_LOW_PASS = False      # Low pass filter

# Channel mix - Stereo balance (0.0 - 1.0)
LEFT_TO_LEFT = 1.0
LEFT_TO_RIGHT = 0.0
RIGHT_TO_LEFT = 0.0
RIGHT_TO_RIGHT = 1.0

# Embed colors - Change these hex colors
COLOR_NOW_PLAYING = 0x00ff88  # Green
COLOR_QUEUE = 0x7289da        # Blurple
COLOR_PAUSED = 0xffaa00       # Orange
COLOR_STOPPED = 0xff0000      # Red

# Bot activity
ACTIVITY_TYPE = discord.ActivityType.listening
ACTIVITY_TEXT = "/help | Harmix"

# =============================================================================
# ======================== END OF CONFIGURATION ===============================
# =============================================================================

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class HarmixBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.loop_mode = {}
        self.start_time = time.time()
        
    async def setup_hook(self):
        log("🚀 Starting Harmix...", "START")
        
        # Connect to local Lavalink
        try:
            protocol = "wss" if USE_SSL else "ws"
            node = wavelink.Node(
                uri=f"{protocol}://{LAVALINK_HOST}:{LAVALINK_PORT}",
                password=LAVALINK_PASSWORD
            )
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
            log(f"✅ Connected to Lavalink at {LAVALINK_HOST}:{LAVALINK_PORT}")
        except Exception as e:
            log(f"❌ Lavalink connection failed: {e}", "ERROR")
            log("Make sure Lavalink.jar is running in Termux!", "ERROR")
        
        # Sync commands
        try:
            synced = await self.tree.sync()
            log(f"✅ Synced {len(synced)} commands")
        except Exception as e:
            log(f"⚠️ Command sync failed: {e}", "WARN")
        
        # Start status monitor
        self.loop.create_task(self.status_loop())
        
    async def on_ready(self):
        log(f"🎶 Harmix Online | {self.user}")
        log(f"📡 Latency: {round(self.latency * 1000)}ms")
        await self.change_presence(activity=discord.Activity(type=ACTIVITY_TYPE, name=ACTIVITY_TEXT))
        
    async def status_loop(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                active = sum(1 for g in self.guilds if g.voice_client)
                log(f"📊 Servers: {len(self.guilds)} | Voice: {active} | Ping: {round(self.latency * 1000)}ms")
            except Exception as e:
                log(f"Status error: {e}", "ERROR")
            await asyncio.sleep(30)

bot = HarmixBot()

def format_duration(ms):
    if ms is None or ms < 0:
        return "Unknown"
    seconds = ms // 1000
    minutes = seconds // 60
    hours = minutes // 60
    if hours > 0:
        return f"{hours}:{minutes % 60:02d}:{seconds % 60:02d}"
    return f"{minutes}:{seconds % 60:02d}"

def get_loop_emoji(mode):
    return {"off": "⏹️", "track": "🔂", "queue": "🔁"}.get(mode, "⏹️")

def detect_source(query):
    q = query.lower()
    if "spotify.com" in q:
        return "spotify"
    elif "music.apple.com" in q or "apple.co" in q:
        return "applemusic"
    return "youtube"

async def apply_audio_settings(player):
    """Apply customized audio filters"""
    try:
        log(f"🔧 Applying audio settings to player...")
        filters = wavelink.Filters()
        
        # Volume
        filters.volume = FILTERS_VOLUME
        log(f"  Volume: {FILTERS_VOLUME}")
        
        # Equalizer
        filters.equalizer = wavelink.Equalizer(name="Custom_EQ", bands=CUSTOM_EQ_BANDS)
        log(f"  EQ: 15-band custom")
        
        # Timescale
        filters.timescale = wavelink.Timescale(
            speed=TIMESCALE_SPEED,
            pitch=TIMESCALE_PITCH,
            rate=TIMESCALE_RATE
        )
        log(f"  Timescale: speed={TIMESCALE_SPEED}, pitch={TIMESCALE_PITCH}, rate={TIMESCALE_RATE}")
        
        # Effects
        if ENABLE_KARAOKE:
            filters.karaoke = wavelink.Karaoke(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
            log(f"  Karaoke: ON")
        else:
            filters.karaoke = None
            
        if ENABLE_TREMOLO:
            filters.tremolo = wavelink.Tremolo(frequency=5.0, depth=0.5)
            log(f"  Tremolo: ON")
        else:
            filters.tremolo = None
            
        if ENABLE_VIBRATO:
            filters.vibrato = wavelink.Vibrato(frequency=5.0, depth=0.5)
            log(f"  Vibrato: ON")
        else:
            filters.vibrato = None
            
        if ENABLE_ROTATION:
            filters.rotation = wavelink.Rotation(speed=0.0)
            log(f"  Rotation: ON")
        else:
            filters.rotation = None
            
        if ENABLE_DISTORTION:
            filters.distortion = wavelink.Distortion(
                sin_offset=0.0, sin_scale=1.0, cos_offset=0.0, cos_scale=1.0,
                tan_offset=0.0, tan_scale=1.0, offset=0.0, scale=1.0
            )
            log(f"  Distortion: ON")
        else:
            filters.distortion = None
        
        # Channel mix
        filters.channel_mix = wavelink.ChannelMix(
            left_to_left=LEFT_TO_LEFT,
            left_to_right=LEFT_TO_RIGHT,
            right_to_left=RIGHT_TO_LEFT,
            right_to_right=RIGHT_TO_RIGHT
        )
        log(f"  Channel Mix: LL={LEFT_TO_LEFT}, LR={LEFT_TO_RIGHT}, RL={RIGHT_TO_LEFT}, RR={RIGHT_TO_RIGHT}")
        
        if ENABLE_LOW_PASS:
            filters.low_pass = wavelink.LowPass(smoothing=0.0)
            log(f"  Low Pass: ON")
        else:
            filters.low_pass = None
            
        await player.set_filters(filters)
        log(f"✅ Audio settings applied successfully")
    except Exception as e:
        log(f"⚠️ Audio settings error: {e}", "ERROR")

# ============== LAVALINK EVENTS ==============
@bot.event
async def on_wavelink_node_ready(payload):
    log(f"🎵 Lavalink node ready: {payload.node.uri}")

@bot.event
async def on_wavelink_track_start(payload):
    player = payload.player
    track = payload.track
    log(f"▶️ Now playing: '{track.title}' by {track.author}")
    
    if hasattr(player, 'home') and player.home:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{track.title}]({track.uri})**",
            color=COLOR_NOW_PLAYING
        )
        embed.add_field(name="👤 Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="⏱️ Duration", value=format_duration(track.length), inline=True)
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        try:
            await player.home.send(embed=embed)
        except Exception as e:
            log(f"Failed to send now playing message: {e}", "ERROR")

@bot.event
async def on_wavelink_track_end(payload):
    player = payload.player
    track = payload.track
    log(f"⏹️ Track ended: '{track.title}'")
    
    if bot.loop_mode.get(player.guild.id) == "track":
        log(f"🔂 Looping track")
        await player.queue.put_wait(track)
    
    if not player.queue.is_empty:
        next_track = player.queue.get()
        log(f"⏭️ Auto-playing next: '{next_track.title}'")
        await player.play(next_track)
        await apply_audio_settings(player)
    else:
        log(f"📭 Queue empty")

# ============== VOICE CONNECTION ==============
async def connect_to_voice(interaction):
    """Connect to voice with debug logging"""
    log(f"🔊 Voice connection requested by {interaction.user}")
    
    if not interaction.user.voice:
        log(f"❌ User not in voice channel", "ERROR")
        return None, "❌ Join a voice channel first!"
    
    channel = interaction.user.voice.channel
    log(f"🎯 Target channel: {channel.name} (ID: {channel.id})")
    
    # Check permissions
    perms = channel.permissions_for(interaction.guild.me)
    log(f"🔐 Permissions - Connect: {perms.connect}, Speak: {perms.speak}")
    
    if not perms.connect or not perms.speak:
        return None, "❌ I need Connect and Speak permissions!"
    
    # Check existing connection
    if interaction.guild.voice_client:
        log(f"🔄 Already connected, checking player...")
        player = interaction.guild.voice_client
        if player.channel.id != channel.id:
            log(f"🔄 Moving to new channel")
            await player.move_to(channel)
        return player, None
    
    # Connect
    try:
        log(f"🚀 Connecting to {channel.name}...")
        player = await channel.connect(cls=wavelink.Player, self_deaf=True)
        log(f"⏳ Waiting for connection to stabilize...")
        await asyncio.sleep(2)
        
        if not player.connected:
            log(f"❌ Connection failed - not connected after delay", "ERROR")
            return None, "❌ Voice connection failed!"
        
        player.home = interaction.channel
        log(f"✅ Connected successfully!")
        
        # Apply settings
        await player.set_volume(VOLUME_ON_JOIN)
        await apply_audio_settings(player)
        
        return player, None
        
    except Exception as e:
        log(f"❌ Voice connection error: {e}", "ERROR")
        return None, f"❌ Connection error: {str(e)}"

# ============== COMMANDS ==============
@bot.tree.command(name="help", description="📖 Show commands")
async def help_cmd(interaction):
    embed = discord.Embed(title="🎶 Harmix", description="Local Lavalink music bot", color=COLOR_QUEUE)
    cmds = [
        ("🎵 `/play <query>`", "Play music"),
        ("⏸️ `/pause`", "Pause"),
        ("▶️ `/resume`", "Resume"),
        ("⏭️ `/skip`", "Skip"),
        ("📋 `/queue`", "Queue"),
        ("🎧 `/nowplaying`", "Current track"),
        (f"🔊 `/volume <0-{MAX_VOLUME}>`", "Volume"),
        ("🔁 `/loop`", "Loop mode"),
        ("⏹️ `/stop`", "Stop"),
        ("👋 `/disconnect`", "Disconnect"),
    ]
    for name, value in cmds:
        embed.add_field(name=name, value=value, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="play", description="🎵 Play music")
async def play(interaction, query: str):
    log(f"🎵 Play command: '{query[:50]}...'")
    await interaction.response.defer(thinking=True)
    
    player, error = await connect_to_voice(interaction)
    if error:
        return await interaction.followup.send(error)
    
    source = detect_source(query)
    log(f"🔍 Source: {source}")
    
    try:
        if source == "spotify":
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.Spotify)
        elif source == "applemusic":
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.AppleMusic)
        else:
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
        
        if not tracks:
            log(f"❌ No tracks found for query", "ERROR")
            return await interaction.followup.send("❌ No tracks found!")
        
        if isinstance(tracks, wavelink.Playlist):
            log(f"📋 Playlist detected: {len(tracks.tracks)} tracks")
            for i, track in enumerate(tracks.tracks):
                if not player.playing and i == 0:
                    await player.play(track)
                    await apply_audio_settings(player)
                else:
                    await player.queue.put_wait(track)
            await interaction.followup.send(f"📋 Added {len(tracks.tracks)} tracks")
        else:
            track = tracks[0]
            log(f"🎵 Single track: '{track.title}'")
            
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
async def pause(interaction):
    player = interaction.guild.voice_client
    if not player or not player.playing:
        return await interaction.response.send_message("❌ Not playing!", ephemeral=True)
    log(f"⏸️ Paused by {interaction.user}")
    await player.pause(True)
    await interaction.response.send_message(embed=discord.Embed(title="⏸️ Paused", color=COLOR_PAUSED))

@bot.tree.command(name="resume", description="▶️ Resume")
async def resume(interaction):
    player = interaction.guild.voice_client
    if not player or not player.paused:
        return await interaction.response.send_message("❌ Not paused!", ephemeral=True)
    log(f"▶️ Resumed by {interaction.user}")
    await player.pause(False)
    await interaction.response.send_message(embed=discord.Embed(title="▶️ Resumed", color=COLOR_NOW_PLAYING))

@bot.tree.command(name="skip", description="⏭️ Skip")
async def skip(interaction):
    player = interaction.guild.voice_client
    if not player or not player.playing:
        return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
    log(f"⏭️ Skipped by {interaction.user}")
    await player.skip()
    await interaction.response.send_message(embed=discord.Embed(title="⏭️ Skipped", color=COLOR_QUEUE))

@bot.tree.command(name="queue", description="📋 Queue")
async def queue(interaction):
    player = interaction.guild.voice_client
    if not player or (player.queue.is_empty and not player.current):
        return await interaction.response.send_message("📭 Empty!", ephemeral=True)
    
    embed = discord.Embed(title="📋 Queue", color=COLOR_QUEUE)
    if player.current:
        embed.add_field(name="Now Playing", value=f"**{player.current.title}**", inline=False)
    if not player.queue.is_empty:
        q = "\n".join([f"`{i+1}.` {t.title[:50]}" for i, t in enumerate(list(player.queue)[:10])])
        embed.add_field(name=f"Up Next ({len(player.queue)})", value=q, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nowplaying", description="🎧 Current track")
async def nowplaying(interaction):
    player = interaction.guild.voice_client
    if not player or not player.current:
        return await interaction.response.send_message("❌ Nothing playing!", ephemeral=True)
    
    track = player.current
    embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=COLOR_NOW_PLAYING)
    embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
    embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="volume", description=f"🔊 Volume (0-{MAX_VOLUME})")
async def volume(interaction, volume: int):
    if not 0 <= volume <= MAX_VOLUME:
        return await interaction.response.send_message(f"❌ 0-{MAX_VOLUME}!", ephemeral=True)
    
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    
    log(f"🔊 Volume set to {volume}% by {interaction.user}")
    await player.set_volume(volume)
    emoji = "🔇" if volume == 0 else "🔈" if volume < 30 else "🔉" if volume < 70 else "🔊"
    await interaction.response.send_message(embed=discord.Embed(title=f"{emoji} {volume}%", color=COLOR_QUEUE))

@bot.tree.command(name="loop", description="🔁 Loop mode")
async def loop(interaction, mode: discord.app_commands.Choice[str]):
    bot.loop_mode[interaction.guild.id] = mode.value
    desc = {"off": "Off", "track": "Track", "queue": "Queue"}
    log(f"🔁 Loop set to {mode.value} by {interaction.user}")
    await interaction.response.send_message(embed=discord.Embed(
        title=f"{get_loop_emoji(mode.value)} {mode.name}",
        description=desc[mode.value],
        color=COLOR_QUEUE
    ))

@bot.tree.command(name="stop", description="⏹️ Stop")
async def stop(interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    log(f"⏹️ Stopped by {interaction.user}")
    player.queue.clear()
    bot.loop_mode[interaction.guild.id] = "off"
    await player.stop()
    await interaction.response.send_message(embed=discord.Embed(title="⏹️ Stopped", color=COLOR_STOPPED))

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    log(f"👋 Disconnected by {interaction.user}")
    await player.disconnect()
    await interaction.response.send_message(embed=discord.Embed(title="👋 Disconnected", color=COLOR_QUEUE))

log("=" * 50)
log("🎶 HARMIX STARTING")
log("=" * 50)

bot.run(TOKEN)
