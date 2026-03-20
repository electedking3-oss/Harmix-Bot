import discord
from discord import app_commands
from discord.ext import commands
import pomice
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
    
    try:
        await pomice.NodePool().create_node(
            bot=bot,
            host=LAVALINK_HOST,
            port=LAVALINK_PORT,
            password=LAVALINK_PASSWORD,
            identifier="MAIN_NODE"
        )
        print("✅ Lavalink connected")
    except Exception as e:
        print(f"❌ Lavalink error: {e}")

@bot.tree.command(name="play", description="🎵 Play music (Apple Music & SoundCloud)")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Join a voice channel!")
    
    channel = interaction.user.voice.channel
    
    player = interaction.guild.voice_client
    if not player:
        try:
            player = await channel.connect(cls=pomice.Player, self_deaf=False)
            print(f"✅ Connected to {channel.name}")
        except Exception as e:
            return await interaction.followup.send(f"❌ Connection failed: {e}")
    elif player.channel.id != channel.id:
        await player.move_to(channel)
    
    try:
        print(f"🔍 Searching: {query}")
        
        # Determine source from query
        if "music.apple.com" in query.lower():
            source = "Apple Music"
        elif "soundcloud.com" in query.lower():
            source = "SoundCloud"
        else:
            source = "Apple Music/SoundCloud"
        
        # Search
        results = await player.get_tracks(query=query)
        
        if not results:
            return await interaction.followup.send("❌ No tracks found! Try Apple Music or SoundCloud links.")
        
        track = results[0] if not isinstance(results, pomice.Playlist) else results.tracks[0]
        print(f"🎵 Found: {track.title} from {source}")
        
        # Play
        await player.play(track)
        print(f"▶️ Playing: {track.title}")
        
        # Check if actually playing
        await asyncio.sleep(1)
        print(f"   is_playing: {player.is_playing}")
        print(f"   position: {player.position}")
        
        await interaction.followup.send(f"🎵 Now Playing: **{track.title}** ({source})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"❌ Error: {e}")

@bot.tree.command(name="disconnect", description="👋 Disconnect")
async def disconnect(interaction: discord.Interaction):
    player = interaction.guild.voice_client
    if not player:
        return await interaction.response.send_message("❌ Not connected!", ephemeral=True)
    
    await player.destroy()
    await interaction.response.send_message("👋 Disconnected")

print("🚀 Starting Harmix (Apple Music + SoundCloud only)...")
bot.run(TOKEN)
