import discord
from discord.ext import commands
import wavelink
import asyncio
import time
import os
from dotenv import load_dotenv

# ============== CONFIGURATION ==============
load_dotenv()
TOKEN = os.getenv("TOKEN")

LAVALINK_HOST = "lavalinkv4.serenetia.com"
LAVALINK_PORT = 443
LAVALINK_PASSWORD = "https://dsc.gg/ajidevserver"

# ============== INTENTS ==============
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class HarmixBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.loop_mode = {}
        self.start_time = time.time()

    async def setup_hook(self):
        node = wavelink.Node(
            uri=f"wss://{LAVALINK_HOST}:{LAVALINK_PORT}",
            password=LAVALINK_PASSWORD
        )
        await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
        await self.tree.sync()

    async def on_ready(self):
        print(f"🎶 Harmix Online | {self.user}")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="/help")
        )

bot = HarmixBot()

# ============== AUDIO SETTINGS ==============
EQ_BANDS = [
    {"band": 0, "gain": 0.25}, {"band": 1, "gain": 0.2},
    {"band": 2, "gain": 0.15}, {"band": 3, "gain": 0.1},
    {"band": 4, "gain": -0.05}, {"band": 5, "gain": 0.0},
    {"band": 6, "gain": 0.0}, {"band": 7, "gain": 0.05},
    {"band": 8, "gain": 0.1}, {"band": 9, "gain": 0.12},
    {"band": 10, "gain": 0.1}, {"band": 11, "gain": 0.08},
    {"band": 12, "gain": 0.05}, {"band": 13, "gain": 0.02},
    {"band": 14, "gain": 0.0},
]

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
    try:
        filters = wavelink.Filters()
        filters.volume = 0.65
        filters.equalizer = wavelink.Equalizer(name="Custom_EQ", bands=EQ_BANDS)
        filters.timescale = wavelink.Timescale(speed=1.0, pitch=1.0, rate=1.0)
        filters.karaoke = None
        filters.tremolo = None
        filters.vibrato = None
        filters.rotation = None
        filters.distortion = None
        filters.channel_mix = wavelink.ChannelMix(
            left_to_left=1.0, left_to_right=0.0,
            right_to_left=0.0, right_to_right=1.0
        )
        filters.low_pass = None
        await player.set_filters(filters)
    except:
        pass

# ============== EVENTS ==============
@bot.event
async def on_wavelink_track_start(payload):
    player = payload.player
    track = payload.track
    if hasattr(player, 'home') and player.home:
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**[{track.title}]({track.uri})**",
            color=0x00ff88
        )
        embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
        embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await player.home.send(embed=embed)

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

# ============== COMMANDS ==============
@bot.tree.command(name="help", description="📖 Show commands")
async def help_cmd(interaction):
    embed = discord.Embed(title="🎶 Harmix", description="Premium music bot", color=0x7289da)
    cmds = [
        ("🎵 /play", "Play music"),
        ("⏸️ /pause", "Pause"),
        ("▶️ /resume", "Resume"),
        ("⏭️ /skip", "Skip"),
        ("📋 /queue", "Queue"),
        ("🎧 /nowplaying", "Current track"),
        ("🔊 /volume", "Volume (0-200)"),
        ("🔁 /loop", "Loop mode"),
        ("⏹️ /stop", "Stop"),
        ("👋 /disconnect", "Disconnect"),
    ]
    for name, value in cmds:
        embed.add_field(name=name, value=value, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="play", description="🎵 Play music")
async def play(interaction, query: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Join a voice channel!", ephemeral=True)

    await interaction.response.defer(thinking=True)

    player = interaction.guild.voice_client
    if not player:
        player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        player.home = interaction.channel
        await apply_audio_settings(player)

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
                else:
                    await player.queue.put_wait(track)
            await interaction.followup.send(f"📋 Added {len(tracks.tracks)} tracks")
        else:
            track = tracks[0]
            if not player.playing:
                await player.play(track)
                await apply_audio_settings(player)
                title, color = "🎵 Now Playing", 0x00ff88
            else:
                await player.queue.put_wait(track)
                title, color = "📝 Added", 0x7289da

            embed = discord.Embed(title=title, description=f"**[{track.title}]({track.uri})**", color=color)
            embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
            embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {str(e)}")

@bot.tree.command(name="pause", description="⏸️ Pause")
async def pause(interaction):
    player = interaction.guild.voice_client
    if not player or not player.playing:
        return await interaction.response.send_message("❌ Not playing!", ephemeral=True)
    await player.pause(True)
    await interaction.response.send_message(embed=discord.Embed(title="⏸️ Paused", color=0xffaa00))

@bot.tree.command(name="resume", description="▶️ Resume")
async def resume(interaction):
    player = interaction.guild.voice_client
    if not player or not player.paused:
        return await interaction.response.send_message("❌ Not paused!", ephemeral=True)
    await player.pause(False)
    await interaction.response.send_message(embed=discord.Embed(title="▶️ Resumed", color=0x00ff88))

@bot.tree.command(name="skip", description="⏭️ Skip")
async def skip(interaction):
    player = interaction.guild.voice_client
    if not player or not player.playing:
        return await interaction.response.send_message("❌ Nothing to skip!", ephemeral=True)
    await player.skip()
    await interaction.response.send_message(embed=discord.Embed(title="⏭️ Skipped", color=0x7289da))

@bot.tree.command(name="queue", description="📋 Queue")
async def queue(interaction):
    player = interaction.guild.voice_client
    if not player or (player.queue.is_empty and not player.current):
        return await interaction.response.send_message("📭 Empty!", ephemeral=True)
    embed = discord.Embed(title="📋 Queue", color=0x7289da)
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
    embed = discord.Embed(title="🎵 Now Playing", description=f"**[{track.title}]({track.uri})**", color=0x00ff88)
    embed.add_field(name="Artist", value=track.author or "Unknown", inline=True)
    embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
    if track.artwork:
        embed.set_thumbnail(url=track.artwork)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="volume", description="🔊 Volume (0-200)")
async def volume(interaction, volume: int):
    if not 0 <= volume <= 200:
        return await interaction.response.send_message("❌ 0-200!", ephemeral=True)
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    await player.set_volume(volume)
    emoji = "🔇" if volume == 0 else "🔈" if volume < 30 else "🔉" if volume < 70 else "🔊"
    await interaction.response.send_message(embed=discord.Embed(title=f"{emoji} {volume}%", color=0x7289da))

@bot.tree.command(name="loop", description="🔁 Loop mode")
async def loop(interaction, mode: discord.app_commands.Choice[str]):
    bot.loop_mode[interaction.guild.id] = mode.value
    desc = {"off": "Off", "track": "Track", "queue": "Queue"}
    await interaction.response.send_message(embed=discord.Embed(
        title=f"{get_loop_emoji(mode.value)} {mode.name}",
        description=desc[mode.value],
        color=0x7289da
    ))

@bot.tree.command(name="stop", description="⏹️ Stop")
async def stop(interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    player.queue.clear()
    bot.loop_mode[interaction.guild.id] = "off"
    await player.stop()
    await interaction.response.send_message(embed=discord.Embed(title="⏹️ Stopped", color=0xff0000))

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    await player.disconnect()
    await interaction.response.send_message(embed=discord.Embed(title="👋 Disconnected", color=0x7289da))

bot.run(TOKEN)

