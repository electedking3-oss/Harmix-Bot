import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

LAVALINK_HOST = "localhost"
LAVALINK_PORT = 2333
LAVALINK_PASSWORD = "LkJhGfDsA19181716"

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🎶 Harmix Online: {bot.user}")
    
    # Connect to Lavalink
    try:
        node = wavelink.Node(
            uri=f"ws://{LAVALINK_HOST}:{LAVALINK_PORT}",
            password=LAVALINK_PASSWORD
        )
        await wavelink.Pool.connect(nodes=[node], client=bot)
        print("✅ Lavalink connected")
    except Exception as e:
        print(f"❌ Lavalink error: {e}")

@bot.tree.command(name="play", description="🎵 Play music")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    
    # Check user in voice
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a voice channel first!")
    
    channel = interaction.user.voice.channel
    
    # Get or create player
    player = interaction.guild.voice_client
    if not player:
        try:
            player = await channel.connect(cls=wavelink.Player, self_deaf=False)
            print(f"✅ Connected to {channel.name}")
        except Exception as e:
            return await interaction.followup.send(f"❌ Connection failed: {e}")
    elif player.channel.id != channel.id:
        await player.move_to(channel)
    
    # Search and play
    try:
        print(f"🔍 Searching: {query}")
        tracks = await wavelink.Playable.search(query)
        
        if not tracks:
            return await interaction.followup.send("❌ No tracks found!")
        
        track = tracks[0]
        print(f"🎵 Found: {track.title}")
        
        # Play without any events or filters
        await player.play(track)
        print(f"▶️ Playing: {track.title}")
        
        await interaction.followup.send(f"🎵 Now Playing: **{track.title}**")
        
    except Exception as e:
        print(f"❌ Play error: {e}")
        await interaction.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    
    await player.disconnect()
    await interaction.response.send_message("👋 Disconnected")

# NO EVENT HANDLERS AT ALL - Let Wavelink handle everything internally

print("🚀 Starting Harmix...")
bot.run(TOKEN)
