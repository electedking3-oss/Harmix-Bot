import discord
from discord import app_commands
from discord.ext import commands
import pomice
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

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class HarmixBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.pomice = pomice.NodePool()
        self.loop_mode = {}

    async def setup_hook(self):
        log("🚀 Starting Harmix...", "START")
        
        # Don't block here - start connection in background
        self.loop.create_task(self.connect_lavalink())
        
        try:
            synced = await self.tree.sync()
            log(f"✅ Synced {len(synced)} commands")
        except Exception as e:
            log(f"⚠️ Sync error: {e}", "WARN")

    async def connect_lavalink(self):
        """Connect to Lavalink with retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                log(f"🔄 Connecting to Lavalink (attempt {attempt+1}/{max_retries})...")
                
                # Try to connect with timeout
                await asyncio.wait_for(
                    self.pomice.create_node(
                        bot=self,
                        host=LAVALINK_HOST,
                        port=LAVALINK_PORT,
                        password=LAVALINK_PASSWORD,
                        identifier="MAIN_NODE"
                    ),
                    timeout=10.0
                )
                
                log("✅ Lavalink connected with Pomice")
                return
                
            except asyncio.TimeoutError:
                log(f"⏱️ Connection timeout (attempt {attempt+1})", "WARN")
            except Exception as e:
                log(f"❌ Connection error: {e}", "ERROR")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(3)  # Wait before retry
        
        log("❌ Failed to connect to Lavalink after all retries", "ERROR")

    async def on_ready(self):
        log(f"🎶 Harmix Online | {self.user}")

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

@bot.event
async def on_pomice_track_start(player: pomice.Player, track: pomice.Track):
    log(f"▶️ Now Playing: '{track.title}'")

@bot.event
async def on_pomice_track_end(player: pomice.Player, track: pomice.Track, reason: str):
    log(f"⏹️ Track ended: {reason}")
    
    if bot.loop_mode.get(player.guild.id) == "track":
        await player.play(track)
        return
    
    if not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)

async def connect_voice(interaction):
    """Connect to voice channel"""
    log(f"🔊 Voice request from {interaction.user}")

    if not interaction.user.voice:
        return None, "❌ Join a voice channel first!"

    channel = interaction.user.voice.channel

    if interaction.guild.voice_client:
        player = interaction.guild.voice_client
        if player.channel.id == channel.id:
            return player, None
        await player.move_to(channel)
        return player, None

    try:
        log(f"🚀 Connecting to {channel.name}...")
        player = await channel.connect(cls=pomice.Player, self_deaf=False)
        await asyncio.sleep(0.5)
        
        if not player.is_connected:
            await player.destroy()
            return None, "❌ Connection failed!"

        player.home = interaction.channel
        await player.set_volume(100)
        
        log(f"✅ Connected to {channel.name}")
        return player, None

    except Exception as e:
        log(f"❌ Connection failed: {e}", "ERROR")
        return None, f"❌ Connection failed: {str(e)[:100]}"

@bot.tree.command(name="play", description="🎵 Play music")
async def play(interaction: discord.Interaction, query: str):
    try:
        log(f"🎵 Play: '{query[:50]}...'")

        player, error = await connect_voice(interaction)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)
        
        await interaction.response.defer(thinking=True)

        try:
            log(f"🔍 Searching: {query}")
            results = await player.get_tracks(query=query)
            
            if not results:
                return await interaction.followup.send("❌ No tracks found!")

            if isinstance(results, pomice.Playlist):
                for i, track in enumerate(results.tracks):
                    if not player.is_playing and i == 0:
                        await player.play(track)
                    else:
                        player.queue.put(track)
                await interaction.followup.send(f"📋 Added {len(results.tracks)} tracks")
            else:
                track = results[0]
                
                if not player.is_playing:
                    await player.play(track)
                    title = "🎵 Now Playing"
                else:
                    player.queue.put(track)
                    title = "📝 Added"

                await interaction.followup.send(f"{title}: **{track.title}**")

        except Exception as e:
            log(f"❌ Play error: {e}", "ERROR")
            await interaction.followup.send(f"❌ Error: {str(e)[:200]}")

    except Exception as e:
        log(f"❌ Critical error: {e}", "ERROR")
        try:
            await interaction.followup.send("❌ Critical error")
        except:
            pass

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction: discord.Interaction):
    try:
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        await player.destroy()
        await interaction.response.send_message("👋 Disconnected")
    except Exception as e:
        log(f"❌ Disconnect error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error", ephemeral=True)

log("=" * 50)
log("🎶 HARMIX - POMICE VERSION")
log("=" * 50)

bot.run(TOKEN)
