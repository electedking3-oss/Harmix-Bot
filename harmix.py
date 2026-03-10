import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import asyncio
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv

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

log(f"Wavelink version: {wavelink.__version__}")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class HarmixBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.loop_mode = {}

    async def setup_hook(self):
        log("🚀 Starting Harmix...")
        try:
            node = wavelink.Node(
                uri=f"ws://{LAVALINK_HOST}:{LAVALINK_PORT}",
                password=LAVALINK_PASSWORD
            )
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
            log("✅ Lavalink connected")
        except Exception as e:
            log(f"❌ Lavalink failed: {e}", "ERROR")
            traceback.print_exc()

        try:
            synced = await self.tree.sync()
            log(f"✅ Synced {len(synced)} commands")
        except Exception as e:
            log(f"⚠️ Sync error: {e}", "WARN")

    async def on_ready(self):
        log(f"🎶 Harmix Online | {self.user}")
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))

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

@bot.event
async def on_wavelink_node_ready(payload):
    log(f"🎵 Lavalink node ready: {payload.node.uri}")

# SIMPLIFIED: Minimal track start event
@bot.event
async def on_wavelink_track_start(payload):
    try:
        track = payload.track
        log(f"▶️ Now Playing: '{track.title}'")
    except Exception as e:
        log(f"⚠️ Track start error: {e}", "ERROR")

# SIMPLIFIED: Minimal track end event  
@bot.event
async def on_wavelink_track_end(payload):
    try:
        log(f"⏹️ Track ended")
    except Exception as e:
        log(f"⚠️ Track end error: {e}", "ERROR")

async def connect_voice(interaction):
    """Simple voice connection"""
    log(f"🔊 Connect request from {interaction.user}")

    if not interaction.user.voice:
        return None, "❌ Join a voice channel first!"

    channel = interaction.user.voice.channel

    # Check existing connection
    if interaction.guild.voice_client:
        player = interaction.guild.voice_client
        if player.channel.id == channel.id:
            return player, None
        await player.move_to(channel)
        return player, None

    # Connect
    try:
        player = await channel.connect(cls=wavelink.Player, self_deaf=False)
        await asyncio.sleep(0.5)
        
        if not player.connected:
            await player.disconnect()
            return None, "❌ Connection failed!"
        
        # Just set volume, no filters
        await player.set_volume(100)
        log(f"✅ Connected to {channel.name}")
        return player, None
        
    except Exception as e:
        log(f"❌ Connection error: {e}", "ERROR")
        return None, f"❌ Connection failed: {str(e)[:100]}"

@bot.tree.command(name="play", description="🎵 Play music")
async def play(interaction, query: str):
    try:
        log(f"🎵 Play: '{query[:50]}...'")
        
        # Connect first
        player, error = await connect_voice(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        
        await interaction.response.defer(thinking=True)
        
        # Simple search
        log("🔍 Searching...")
        tracks = await wavelink.Playable.search(query)
        
        if not tracks:
            return await interaction.followup.send("❌ No tracks found!")
        
        track = tracks[0]
        log(f"🎵 Found: {track.title}")
        
        # Play with NO extra processing
        log("▶️ Starting playback...")
        await player.play(track)
        log("✅ Play command sent")
        
        # Simple embed
        embed = discord.Embed(
            title="🎵 Now Playing", 
            description=f"**[{track.title}]({track.uri})**",
            color=0x00ff88
        )
        embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
        
        await interaction.followup.send(embed=embed)
        log("✅ Message sent")
        
    except Exception as e:
        log(f"❌ Play error: {e}", "ERROR")
        traceback.print_exc()
        try:
            await interaction.followup.send(f"❌ Error: {str(e)[:200]}")
        except:
            pass

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction):
    try:
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        await player.disconnect()
        await interaction.response.send_message("👋 Disconnected")
    except Exception as e:
        log(f"❌ Disconnect error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="stop", description="⏹️ Stop")
async def stop(interaction):
    try:
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        await player.stop()
        await interaction.response.send_message("⏹️ Stopped")
    except Exception as e:
        log(f"❌ Stop error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error", ephemeral=True)

log("=" * 50)
log("🎶 HARMIX MINIMAL TEST VERSION")
log("=" * 50)

bot.run(TOKEN)
