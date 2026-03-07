Import discord
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
LAVALINK_HOST = "localhost"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "LkJhGfDsA19181716"

# -------------------- DEBUGGING --------------------
DEBUG_MODE = True

def log(msg: str, level: str = "INFO"):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")

# -------------------- AUDIO CUSTOMIZATION --------------------
VOLUME_ON_JOIN = 65
MAX_VOLUME = 200

CUSTOM_EQ_BANDS = [
    {"band": 0, "gain": 0.25},
    {"band": 1, "gain": 0.20},
    {"band": 2, "gain": 0.15},
    {"band": 3, "gain": 0.10},
    {"band": 4, "gain": -0.05},
    {"band": 5, "gain": 0.0},
    {"band": 6, "gain": 0.0},
    {"band": 7, "gain": 0.05},
    {"band": 8, "gain": 0.10},
    {"band": 9, "gain": 0.12},
    {"band": 10, "gain": 0.10},
    {"band": 11, "gain": 0.08},
    {"band": 12, "gain": 0.05},
    {"band": 13, "gain": 0.02},
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

COLOR_NOW_PLAYING = 0x00ff88
COLOR_QUEUE = 0x7289da
COLOR_PAUSED = 0xffaa00
COLOR_STOPPED = 0xff0000

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
        
    async def setup_hook(self):
        log("🚀 Starting Harmix...", "START")
        
        # CRITICAL FIX: Connect to local Lavalink with proper ws:// (not wss://)
        try:
            node = wavelink.Node(
                uri=f"ws://{LAVALINK_HOST}:{LAVALINK_PORT}",
                password=LAVALINK_PASSWORD
            )
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
            log(f"✅ Lavalink connected to ws://{LAVALINK_HOST}:{LAVALINK_PORT}")
        except Exception as e:
            log(f"❌ Lavalink connection failed: {e}", "ERROR")
            import traceback
            traceback.print_exc()
        
        try:
            synced = await self.tree.sync()
            log(f"✅ Synced {len(synced)} commands")
        except Exception as e:
            log(f"⚠️ Sync error: {e}", "WARN")
        
        self.loop.create_task(self.monitor())
        
    async def on_ready(self):
        log(f"🎶 Harmix Online | {self.user}")
        log(f"📡 Latency: {round(self.latency * 1000)}ms | Servers: {len(self.guilds)}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))
        
    async def monitor(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                active = sum(1 for g in self.guilds if g.voice_client)
                log(f"📊 Voice: {active} | Servers: {len(self.guilds)}")
            except:
                pass
            await asyncio.sleep(30)

bot = HarmixBot()

def format_duration(ms):
    if not ms or ms < 0:
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
    try:
        filters = wavelink.Filters()
        filters.volume = FILTERS_VOLUME
        filters.equalizer = wavelink.Equalizer(name="Custom_EQ", bands=CUSTOM_EQ_BANDS)
        filters.timescale = wavelink.Timescale(speed=TIMESCALE_SPEED, pitch=TIMESCALE_PITCH, rate=TIMESCALE_RATE)
        
        if ENABLE_KARAOKE:
            filters.karaoke = wavelink.Karaoke(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
        else:
            filters.karaoke = None
            
        if ENABLE_TREMOLO:
            filters.tremolo = wavelink.Tremolo(frequency=5.0, depth=0.5)
        else:
            filters.tremolo = None
            
        if ENABLE_VIBRATO:
            filters.vibrato = wavelink.Vibrato(frequency=5.0, depth=0.5)
        else:
            filters.vibrato = None
            
        if ENABLE_ROTATION:
            filters.rotation = wavelink.Rotation(speed=0.0)
        else:
            filters.rotation = None
            
        if ENABLE_DISTORTION:
            filters.distortion = wavelink.Distortion(sin_offset=0.0, sin_scale=1.0, cos_offset=0.0, cos_scale=1.0, tan_offset=0.0, tan_scale=1.0, offset=0.0, scale=1.0)
        else:
            filters.distortion = None
            
        filters.channel_mix = wavelink.ChannelMix(left_to_left=LEFT_TO_LEFT, left_to_right=LEFT_TO_RIGHT, right_to_left=RIGHT_TO_LEFT, right_to_right=RIGHT_TO_RIGHT)
        
        if ENABLE_LOW_PASS:
            filters.low_pass = wavelink.LowPass(smoothing=0.0)
        else:
            filters.low_pass = None
            
        await player.set_filters(filters)
        log(f"✅ Audio filters applied")
    except Exception as e:
        log(f"⚠️ Audio filters error: {e}", "ERROR")

@bot.event
async def on_wavelink_node_ready(payload):
    log(f"🎵 Lavalink node ready: {payload.node.uri}")

@bot.event
async def on_wavelink_track_start(payload):
    player = payload.player
    track = payload.track
    log(f"▶️ Playing: '{track.title}'")
    
    if hasattr(player, 'home') and player.home:
        embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=COLOR_NOW_PLAYING)
        embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        try:
            await player.home.send(embed=embed)
        except:
            pass

@bot.event
async def on_wavelink_track_end(payload):
    player = payload.player
    track = payload.track
    
    if bot.loop_mode.get(player.guild.id) == "track":
        await player.queue.put_wait(track)
    
    if not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)
        await apply_audio_settings(player)

# CRITICAL FIX: Proper voice connection with retry logic
async def connect_voice(interaction):
    log(f"🔊 Voice request from {interaction.user}")
    
    if not interaction.user.voice:
        return None, "❌ Join a voice channel first!"
    
    channel = interaction.user.voice.channel
    log(f"🎯 Target: {channel.name}")
    
    # Check perms
    perms = channel.permissions_for(interaction.guild.me)
    log(f"🔐 Connect: {perms.connect}, Speak: {perms.speak}")
    if not perms.connect or not perms.speak:
        return None, "❌ I need Connect and Speak permissions!"
    
    # Check if already connected
    if interaction.guild.voice_client:
        log(f"🔄 Already connected")
        player = interaction.guild.voice_client
        if player.channel.id != channel.id:
            await player.move_to(channel)
            log(f"🔄 Moved to {channel.name}")
        return player, None
    
    # Connect with retry
    for attempt in range(3):
        try:
            log(f"🚀 Connection attempt {attempt+1}/3...")
            player = await channel.connect(cls=wavelink.Player, self_deaf=True)
            
            # Wait for stable connection
            await asyncio.sleep(2)
            
            if not player.connected:
                log(f"⚠️ Not connected after delay")
                if attempt < 2:
                    continue
                return None, "❌ Connection failed!"
            
            player.home = interaction.channel
            await player.set_volume(VOLUME_ON_JOIN)
            await apply_audio_settings(player)
            
            log(f"✅ Connected to {channel.name}")
            return player, None
            
        except Exception as e:
            log(f"❌ Attempt {attempt+1} failed: {e}", "ERROR")
            if attempt == 2:
                return None, f"❌ Voice error: {str(e)}"
            await asyncio.sleep(1)
    
    return None, "❌ Unknown error"

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
        ("🔊 `/volume <0-200>`", "Volume"),
        ("🔁 `/loop`", "Loop mode"),
        ("⏹️ `/stop`", "Stop"),
        ("👋 `/disconnect`", "Disconnect"),
    ]
    for name, value in cmds:
        embed.add_field(name=name, value=value, inline=False)
    await interactio
