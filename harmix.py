import discord
from discord import app_commands
from discord.ext import commands
import pomice
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🎶 Harmix Online: {bot.user}")
    
    try:
        await pomice.NodePool().create_node(
            bot=bot,
            host="localhost",
            port=2333,
            password="LkJhGfDsA19181716",
            identifier="MAIN_NODE"
        )
        print("✅ Lavalink connected")
    except Exception as e:
        print(f"❌ Lavalink error: {e}")

@bot.tree.command(name="play", description="🎵 Play music")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    
    # Check voice
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a voice channel!")
    
    channel = interaction.user.voice.channel
    
    # Connect or get player
    player = interaction.guild.voice_client
    if not player:
        try:
            player = await channel.connect(cls=pomice.Player, self_deaf=False)
            print(f"✅ Connected to {channel.name}")
        except Exception as e:
            return await interaction.followup.send(f"❌ Connection failed: {e}")
    
    # Search
    try:
        print(f"🔍 Searching: {query}")
        results = await player.get_tracks(query=query)
        
        if not results:
            return await interaction.followup.send("❌ No tracks found!")
        
        track = results[0] if not isinstance(results, pomice.Playlist) else results.tracks[0]
        print(f"🎵 Playing: {track.title}")
        
        # SIMPLE PLAY - No filters, no volume changes, just play
        await player.play(track)
        
        # Check if actually playing
        print(f"   is_playing: {player.is_playing}")
        print(f"   volume: {player.volume}")
        print(f"   position: {player.position}")
        
        await interaction.followup.send(f"🎵 Now Playing: **{track.title}**")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="volume", description="🔊 Check/Set volume")
async def volume(interaction: discord.Interaction, vol: int = None):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    
    if vol is None:
        # Just check current volume
        return await interaction.response.send_message(f"🔊 Current volume: {player.volume}%")
    
    # Set volume
    await player.set_volume(vol)
    await interaction.response.send_message(f"🔊 Volume set to: {vol}%")

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    
    await player.destroy()
    await interaction.response.send_message("👋 Disconnected")

print("🚀 Starting Harmix...")
bot.run(TOKEN)
