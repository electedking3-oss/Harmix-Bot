import discord
from discord.ext import commands
import wavelink
import asyncio
import time
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv

# =============================================================================
# ========================= HARMIX BOT CONFIGURATION ==========================
# =============================================================================

load_dotenv()
TOKEN = os.getenv("TOKEN")

LAVALINK_HOST = "localhost"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "LkJhGfDsA19181716"

DEBUG_MODE = True

def log(msg: str, level: str = "INFO"):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")

# -------------------- AUDIO CUSTOMIZATION --------------------
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
        self.lavalink_connected = False
        
    async def setup_hook(self):
        log("🚀 Starting Harmix...", "START")
        
        # Connect to Lavalink v4
        try:
            log("🔄 Connecting to Lavalink v4...")
            node = wavelink.Node(
                uri=f"ws://{LAVALINK_HOST}:{LAVALINK_PORT}",
                password=LAVALINK_PASSWORD
            )
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
            self.lavalink_connected = True
            log(f"✅ Lavalink v4 connected")
        except Exception as e:
            self.lavalink_connected = False
            log(f"❌ Lavalink failed: {e}", "ERROR")
            traceback.print_exc()
        
        try:
            synced = await self.tree.sync()
            log(f"✅ Synced {len(synced)} commands")
        except Exception as e:
            log(f"⚠️ Sync error: {e}", "WARN")
        
        self.loop.create_task(self.monitor())
        
    async def on_ready(self):
        status = "✅ OK" if self.lavalink_connected else "❌ FAIL"
        log(f"🎶 Harmix Online | {self.user} | {status}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))
        
    async def monitor(self):
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                active = sum(1 for g in self.guilds if g.voice_client)
                log(f"📊 Servers: {len(self.guilds)} | Voice: {active}")
            except:
                pass
            await asyncio.sleep(30)
    
    async def on_error(self, event, *args, **kwargs):
        log(f"❌ Error in {event}: {traceback.format_exc()}", "ERROR")

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
        log(f"⚠️ Audio error: {e}", "ERROR")

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

async def connect_voice(interaction):
    """Connect to voice channel with full error handling"""
    log(f"🔊 Voice request from {interaction.user}")
    
    if not bot.lavalink_connected:
        return None, "❌ **Music system offline!**"
    
    if not interaction.user.voice:
        return None, "❌ Join a voice channel first!"
    
    channel = interaction.user.voice.channel
    log(f"🎯 Target: {channel.name}")
    
    # Check permissions
    perms = channel.permissions_for(interaction.guild.me)
    if not perms.connect or not perms.speak:
        return None, "❌ I need Connect and Speak permissions!"
    
    # Check if already connected
    if interaction.guild.voice_client:
        try:
            player = interaction.guild.voice_client
            if player.channel.id != channel.id:
                await player.move_to(channel)
            return player, None
        except Exception as e:
            log(f"⚠️ Error checking existing connection: {e}", "ERROR")
    
    # Connect with retry
    for attempt in range(3):
        try:
            log(f"🚀 Connection attempt {attempt+1}/3...")
            
            player = await channel.connect(cls=wavelink.Player, self_deaf=True)
            
            # Wait for connection
            await asyncio.sleep(1)
            
            if not player.connected:
                await asyncio.sleep(2)
                if not player.connected:
                    if attempt < 2:
                        continue
                    return None, "❌ **Connection failed!**"
            
            player.home = interaction.channel
            await player.set_volume(VOLUME_ON_JOIN)
            await apply_audio_settings(player)
            
            log(f"✅ Connected to {channel.name}")
            return player, None
            
        except Exception as e:
            error_str = str(e)
            log(f"❌ Attempt {attempt+1} failed: {error_str}", "ERROR")
            traceback.print_exc()
            
            if attempt == 2:
                return None, f"❌ **Connection failed:** {error_str[:100]}"
            
            await asyncio.sleep(1)
    
    return None, "❌ Unknown error"

@bot.tree.command(name="help", description="📖 Show commands")
async def help_cmd(interaction):
    try:
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
        
        status = "✅ Online" if bot.lavalink_connected else "❌ Offline"
        embed.add_field(name="🎧 Music System", value=status, inline=False)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        log(f"❌ Help error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error showing help", ephemeral=True)

@bot.tree.command(name="play", description="🎵 Play music")
async def play(interaction, query: str):
    try:
        log(f"🎵 Play: '{query[:50]}...'")
        await interaction.response.defer(thinking=True)
        
        player, error = await connect_voice(interaction)
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
                return await interaction.followup.send("❌ No tracks found!")
            
            if isinstance(tracks, wavelink.Playlist):
                for i, track in enumerate(tracks.tracks):
                    if not player.playing and i == 0:
                        await player.play(track)
                        await apply_audio_settings(player)
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
            error_str = str(e)
            log(f"❌ Play error: {error_str}", "ERROR")
            traceback.print_exc()
            
            if "Failed to load tracks" in error_str:
                await interaction.followup.send("❌ **YouTube blocked this request!**\\n\\nTry using a Spotify link instead:\\n`/play https://open.spotify.com/track/...`")
            else:
                await interaction.followup.send(f"❌ Error: {error_str[:200]}")
    except Exception as e:
        log(f"❌ Critical play error: {e}", "ERROR")
        traceback.print_exc()
        try:
            await interaction.followup.send("❌ Critical error occurred")
        except:
            pass

@bot.tree.command(name="pause", description="⏸️ Pause")
async def pause(interaction):
    try:
        player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message("❌ Not playing!", ephemeral=True)
        await player.pause(True)
        await interaction.response.send_message(embed=discord.Embed(title="⏸️ Paused", color=COLOR_PAUSED))
    except Exception as e:
        log(f"❌ Pause error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error pausing", ephemeral=True)

@bot.tree.command(name="resume", description="▶️ Resume")
async def resume(interaction):
    try:
        player = interaction.guild.voice_client
        if not player or not player.paused:
            return await interaction.response.send_message("❌ Not paused!", ephemeral=True)
        await player.pause(False)
        await interaction.response.send_message(embed=discord.Embed(title="▶️ Resumed", color=COLOR_NOW_PLAYING))
    except Exception as e:
        log(f"❌ Resume error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error resuming", ephemeral=True)

@bot.tree.command(name="skip", description="⏭️ Skip")
async def skip(interaction):
    try:
        player = interaction.guild.voice_client
        if not player or not player.playing:
            return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
        await player.skip()
        await interaction.response.send_message(embed=discord.Embed(title="⏭️ Skipped", color=COLOR_QUEUE))
    except Exception as e:
        log(f"❌ Skip error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error skipping", ephemeral=True)

@bot.tree.command(name="queue", description="📋 Queue")
async def queue(interaction):
    try:
        player = interaction.guild.voice_client
        if not player or (player.queue.is_empty and not player.current):
            return await interaction.response.send_message("📭 Empty!", ephemeral=True)
        embed = discord.Embed(title="📋 Queue", color=COLOR_QUEUE)
        if player.current:
            embed.add_field(name="Now Playing", value=f"**{player.current.title}**", inline=False)
        if not player.queue.is_empty:
            q = "\\n".join([f"`{i+1}.` {t.title[:50]}" for i, t in enumerate(list(player.queue)[:10])])
            embed.add_field(name=f"Up Next ({len(player.queue)})", value=q, inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        log(f"❌ Queue error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error showing queue", ephemeral=True)

@bot.tree.command(name="nowplaying", description="🎧 Current track")
async def nowplaying(interaction):
    try:
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
    except Exception as e:
        log(f"❌ NP error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="volume", description="🔊 Volume (0-200)")
async def volume(interaction, volume: int):
    try:
        if not 0 <= volume <= 200:
            return await interaction.response.send_message("❌ 0-200!", ephemeral=True)
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        await player.set_volume(volume)
        emoji = "🔇" if volume == 0 else "🔈" if volume < 30 else "🔉" if volume < 70 else "🔊"
        await interaction.response.send_message(embed=discord.Embed(title=f"{emoji} {volume}%", color=COLOR_QUEUE))
    except Exception as e:
        log(f"❌ Volume error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error setting volume", ephemeral=True)

@bot.tree.command(name="loop", description="🔁 Loop mode")
async def loop(interaction, mode: discord.app_commands.Choice[str]):
    try:
        bot.loop_mode[interaction.guild.id] = mode.value
        desc = {"off": "Off", "track": "Track", "queue": "Queue"}
        await interaction.response.send_message(embed=discord.Embed(title=f"{get_loop_emoji(mode.value)} {mode.name}", description=desc[mode.value], color=COLOR_QUEUE))
    except Exception as e:
        log(f"❌ Loop error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="stop", description="⏹️ Stop")
async def stop(interaction):
    try:
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        player.queue.clear()
        bot.loop_mode[interaction.guild.id] = "off"
        await player.stop()
        await interaction.response.send_message(embed=discord.Embed(title="⏹️ Stopped", color=COLOR_STOPPED))
    except Exception as e:
        log(f"❌ Stop error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error stopping", ephemeral=True)

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction):
    try:
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        await player.disconnect()
        await interaction.response.send_message(embed=discord.Embed(title="👋 Disconnected", color=COLOR_QUEUE))
    except Exception as e:
        log(f"❌ Disconnect error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error disconnecting", ephemeral=True)

log("=" * 50)
log("🎶 HARMIX STARTING - ULTRA STABLE VERSION")
log("=" * 50)

bot.run(TOKEN)

