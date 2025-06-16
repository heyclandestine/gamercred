import os
import sys
import socket
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

import discord
from discord.ext import commands
from commands import GamingCommands
from constants import TOKEN, COMMAND_PREFIX
from keepalive import keep_alive
import asyncio
from storage import GameStorage  # Add this import
import logging

# Set up logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Singleton check to prevent multiple instances
def is_bot_already_running():
    """Check if another instance of the bot is already running"""
    try:
        # Try to create a TCP socket and bind to a specific port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set SO_REUSEADDR to avoid "Address already in use" errors when restarting
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('localhost', 50000))  # Use port 50000 for instance checking
        return False  # Socket created successfully, no other instance running
    except socket.error:
        return True  # Socket creation failed, another instance is running

# Set up the bot with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable members intent for user information
intents.guilds = True   # Enable guilds intent for server information
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Create a single GameStorage instance
storage = None

@bot.event
async def on_ready():
    global storage
    logger.info(f'Bot is ready! Logged in as {bot.user.name}')
    logger.info(f'Connected to {len(bot.guilds)} servers')
    
    # Always reinitialize commands on ready
    logger.info('Initializing commands...')
    try:
        # Remove existing commands if any
        for cog in bot.cogs:
            await bot.remove_cog(cog)
        
        # Add commands
        gaming_commands = GamingCommands(bot, storage)
        await bot.add_cog(gaming_commands)
        logger.info('Commands initialized successfully!')
        logger.info(f'Command prefix is: {bot.command_prefix}')
        logger.info('Available commands:')
        for command in bot.commands:
            logger.info(f'  {command.name}: {command.help}')
    except Exception as e:
        logger.error(f'Error initializing commands: {str(e)}', exc_info=True)
        raise  # Re-raise the exception to see the full error

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` to see command usage.")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"❌ Command not found. Use `!help` to see available commands.")
    else:
        logger.error(f"Error occurred: {str(error)}", exc_info=True)
        await ctx.send(f"❌ An error occurred: {str(error)}")

@bot.event
async def on_disconnect():
    print("Bot disconnected. Cleaning up...")
    # Clean up any resources here
    if hasattr(bot, 'commands_added'):
        delattr(bot, 'commands_added')

async def async_main():
    global storage
    # Check if bot is already running
    if is_bot_already_running():
        logger.error("Bot is already running! Exiting to prevent duplicate instances.")
        logger.info("Use 'python kill_bots.py' to kill all instances and restart.")
        return

    if not TOKEN:
        logger.error("Discord token not found in environment variables!")
        return

    try:
        logger.info("Initializing database...")
        # Initialize the database before starting the bot
        storage = GameStorage()
        logger.info("Database initialized successfully!")
        
        logger.info("Starting bot...")
        # Start the keep alive server
        keep_alive()
        # Run the bot
        await bot.start(TOKEN)
    except discord.errors.LoginFailure:
        logger.error("Failed to login. Please check your Discord token.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nBot shutdown requested...")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        print("Full error details:", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()