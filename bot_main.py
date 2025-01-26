import discord
from discord.ext import commands
import logging
import time
from config import BOT_TOKEN
from database_setup import initialize_db
from character_management import CharacterManagement
from alliance_management import AllianceManagement
from interaction_helpers import InteractionHelpers
from war_schedule import WarScheduler, setup_scheduler

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Scheduler initialization flag
scheduler_initialized = False

# Database setup with retry logic
def initialize_database_with_retries(retries=3, delay=5):
    for attempt in range(retries):
        try:
            initialize_db()
            logger.info("Database initialized successfully.")
            return
        except Exception as e:
            logger.error(f"Database initialization failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise

try:
    initialize_database_with_retries()
except Exception as e:
    logger.critical(f"Critical error: Unable to initialize database. Exiting. {e}")
    exit(1)

@bot.event
async def on_ready():
    global scheduler_initialized
    logger.info(f"Logged in as {bot.user} ({bot.user.id})")
    if not scheduler_initialized:
        setup_scheduler()
        scheduler_initialized = True
        logger.info("Scheduler started!")
        await WarScheduler.reload_jobs_from_db(bot)


async def setup_bot():
    cogs = [
        ("CharacterManagement", CharacterManagement),
        ("AllianceManagement", AllianceManagement),
        ("InteractionHelpers", InteractionHelpers),
        ("WarScheduler", WarScheduler),
    ]

    for cog_name, cog_class in cogs:
        try:
            await bot.add_cog(cog_class(bot))
            logger.info(f"{cog_name} cog loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading {cog_name} cog: {e}")

async def main():
    async with bot:
        try:
            await setup_bot()
            await bot.start(BOT_TOKEN)
        except Exception as e:
            logger.critical(f"Bot failed to start: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
