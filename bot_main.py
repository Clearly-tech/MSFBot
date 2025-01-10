import discord
from discord.ext import commands
from config import BOT_TOKEN, MSF_URL
from database_setup import db_setup
from selenium_setup import SeleniumSetup as selenium_setup
from alliance_management import setup as setup_alliance
from character_management import setup as setup_characters
from gamemodes import setup as setup_gamemodes
from interaction_helpers import setup as setup_helpers

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Database setup
db_setup.initialize_db()

# Setup cogs
async def setup_cogs():
    try:
        await setup_alliance(bot)  # Load AllianceManager cog
        await setup_characters(bot)  # Load character management cog
        await setup_gamemodes(bot)  # Load gamemodes cog
        await setup_helpers(bot)  # Load interaction helpers cog
        print("All cogs loaded successfully!")
    except Exception as e:
        print(f"Failed to load cogs: {e}")

# Run the bot after setting up
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await setup_cogs()  # Set up all cogs
    await bot.tree.sync()  # Sync commands with Discord

# Run the bot
bot.run(BOT_TOKEN)
