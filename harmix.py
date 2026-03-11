import discord
from discord import app_commands
from discord.ext import commands
import pomice
import asyncio
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
VOLUME_ON_JOIN = 100
MAX_VOLUME = 1000  # Pomice supports up to 1000%

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
        self.pomice = pomice.NodePool()
        self.loop_mode = {}

    async def setup_hook(self):
        log("🚀 Starting Harmix...", "START")

        # Connect to Lavalink with Pomice
        try:
            log("🔄 Connecting to Lavalink...")
            await self.pomice.create_node(
                bot=self,
                host=LAVALINK_HOST,
                port=LAVALINK_PORT,
                password=LAVALINK_PASSWORD,
                identifier="MAIN_NODE"
            )
            log("✅ Lavalink connected with Pomice")
        except Exception as e:
            log(f"❌ Lavalink failed: {e}", "ERROR")
            traceback.print_exc()

        # Sync commands
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

def get_loop_emoji(mode):
    return {"off": "⏹️", "track": "🔂", "queue": "🔁"}.get(mode, "⏹️")

# Pomice event handlers
@bot.event
async def on_pomice_track_start(player: pomice.Player, track: pomice.Track):
    log(f"▶️ Now Playing: '{track.title}'")
    
    if hasattr(player, 'home') and player.home:
        embed = discord.Embed(
            title="🎵 Now Playing", 
            description=f"**[{track.title}]({track.uri})**",
            color=COLOR_NOW_PLAYING
        )
        embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        try:
            await player.home.send(embed=embed)
        except:
            pass

@bot.event
async def on_pomice_track_end(player: pomice.Player, track: pomice.Track, reason: str):
    log(f"⏹️ Track ended: {track.title} | Reason: {reason}")
    
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
            log(f"✅ Already connected to {channel.name}")
            return player, None
        log(f"🔄 Moving to {channel.name}")
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
        await player.set_volume(VOLUME_ON_JOIN)
        
        log(f"✅ Connected to {channel.name}")
        return player, None

    except Exception as e:
        log(f"❌ Connection failed: {e}", "ERROR")
        return None, f"❌ Connection failed: {str(e)[:100]}"

@bot.tree.command(name="help", description="📖 Show commands")
async def help_cmd(interaction: discord.Interaction):
    try:
        embed = discord.Embed(title="🎶 Harmix", description="Pomice-powered music bot", color=COLOR_QUEUE)
        cmds = [
            ("🎵 `/play <query>`", "Play music (YouTube/Spotify/Apple Music)"),
            ("⏸️ `/pause`", "Pause"),
            ("▶️ `/resume`", "Resume"),
            ("⏭️ `/skip`", "Skip"),
            ("📋 `/queue`", "Queue"),
            ("🎧 `/nowplaying`", "Current track"),
            ("🔊 `/volume <0-1000>`", "Volume"),
            ("🔁 `/loop`", "Loop mode"),
            ("⏹️ `/stop`", "Stop"),
            ("👋 `/disconnect`", "Disconnect"),
        ]
        for name, value in cmds:
            embed.add_field(name=name, value=value, inline=False)

        embed.add_field(name="🎧 Status", value="✅ Online (Pomice)", inline=False)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        log(f"❌ Help error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error showing help", ephemeral=True)

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
                await interaction.followup.send(f"📋 Added {len(results.tracks)} tracks from playlist")
            else:
                track = results[0]
                
                if not player.is_playing:
                    await player.play(track)
                    title, color = "🎵 Now Playing", COLOR_NOW_PLAYING
                else:
                    player.queue.put(track)
                    title, color = "📝 Added", COLOR_QUEUE

                embed = discord.Embed(title=title, description=f"**[{track.title}]({track.uri})**", color=color)
                embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
                embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
                if track.thumbnail:
                    embed.set_thumbnail(url=track.thumbnail)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            error_str = str(e)
            log(f"❌ Play error: {error_str}", "ERROR")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {error_str[:200]}")

    except Exception as e:
        log(f"❌ Critical play error: {e}", "ERROR")
        traceback.print_exc()
        try:
            await interaction.followup.send("❌ Critical error occurred")
        except:
            pass

@bot.tree.command(name="pause", description="⏸️ Pause")
async def pause(interaction: discord.Interaction):
    try:
        player = interaction.guild.voice_client
        if not player or not player.is_playing:
            return await interaction.response.send_message("❌ Not playing!", ephemeral=True)
        await player.set_pause(True)
        await interaction.response.send_message(embed=discord.Embed(title="⏸️ Paused", color=COLOR_PAUSED))
    except Exception as e:
        log(f"❌ Pause error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error pausing", ephemeral=True)

@bot.tree.command(name="resume", description="▶️ Resume")
async def resume(interaction: discord.Interaction):
    try:
        player = interaction.guild.voice_client
        if not player or not player.is_paused:
            return await interaction.response.send_message("❌ Not paused!", ephemeral=True)
        await player.set_pause(False)
        await interaction.response.send_message(embed=discord.Embed(title="▶️ Resumed", color=COLOR_NOW_PLAYING))
    except Exception as e:
        log(f"❌ Resume error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error resuming", ephemeral=True)

@bot.tree.command(name="skip", description="⏭️ Skip")
async def skip(interaction: discord.Interaction):
    try:
        player = interaction.guild.voice_client
        if not player or not player.is_playing:
            return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
        await player.stop()
        await interaction.response.send_message(embed=discord.Embed(title="⏭️ Skipped", color=COLOR_QUEUE))
    except Exception as e:
        log(f"❌ Skip error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error skipping", ephemeral=True)

@bot.tree.command(name="queue", description="📋 Queue")
async def queue(interaction: discord.Interaction):
    try:
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
    except Exception as e:
        log(f"❌ Queue error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error showing queue", ephemeral=True)

@bot.tree.command(name="nowplaying", description="🎧 Current track")
async def nowplaying(interaction: discord.Interaction):
    try:
        player = interaction.guild.voice_client
        if not player or not player.current:
            return await interaction.response.send_message("❌ Nothing playing!", ephemeral=True)
        
        track = player.current
        embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=COLOR_NOW_PLAYING)
        embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        log(f"❌ NP error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="volume", description="🔊 Volume (0-1000)")
async def volume(interaction: discord.Interaction, volume: int):
    try:
        if not 0 <= volume <= 1000:
            return await interaction.response.send_message("❌ 0-1000!", ephemeral=True)
        
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
@app_commands.choices(mode=[
    app_commands.Choice(name="Off", value="off"),
    app_commands.Choice(name="Track", value="track"),
    app_commands.Choice(name="Queue", value="queue")
])
async def loop(interaction: discord.Interaction, mode: discord.app_commands.Choice[str]):
    try:
        bot.loop_mode[interaction.guild.id] = mode.value
        desc = {"off": "Off", "track": "Track", "queue": "Queue"}
        await interaction.response.send_message(embed=discord.Embed(title=f"{get_loop_emoji(mode.value)} {mode.name}", description=desc[mode.value], color=COLOR_QUEUE))
    except Exception as e:
        log(f"❌ Loop error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error", ephemeral=True)

@bot.tree.command(name="stop", description="⏹️ Stop")
async def stop(interaction: discord.Interaction):
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
async def disconnect(interaction: discord.Interaction):
    try:
        player = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
        
        player.queue.clear()
        bot.loop_mode[interaction.guild.id] = "off"
        
        if player.is_playing:
            await player.stop()
        
        await player.destroy()
        await interaction.response.send_message(embed=discord.Embed(title="👋 Disconnected", color=COLOR_QUEUE))
    except Exception as e:
        log(f"❌ Disconnect error: {e}", "ERROR")
        await interaction.response.send_message("❌ Error disconnecting", ephemeral=True)

log("=" * 50)
log("🎶 HARMIX STARTING - POMICE VERSION")
log("Python 3.13 compatible!")
log("=" * 50)

bot.run(TOKEN)
