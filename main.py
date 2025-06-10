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

print("main.py started")

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
    print(f'Bot is ready! Logged in as {bot.user.name}')
    print(f'Connected to {len(bot.guilds)} servers')
    
    # Always reinitialize commands on ready
    print('Initializing commands...')
    try:
        # Remove existing commands if any
        for cog in bot.cogs:
            await bot.remove_cog(cog)
        
        # Add commands
        gaming_commands = GamingCommands(bot, storage)
        await bot.add_cog(gaming_commands)
        print('Commands initialized successfully!')
        print(f'Command prefix is: {bot.command_prefix}')
        print('Available commands:')
        for command in bot.commands:
            print(f'  {command.name}: {command.help}')
    except Exception as e:
        print(f'Error initializing commands: {str(e)}')
        print('Full error details:', file=sys.stderr)
        import traceback
        traceback.print_exc()
        raise  # Re-raise the exception to see the full error

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` to see command usage.")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"❌ Command not found. Use `!help` to see available commands.")
    else:
        print(f"Error occurred: {str(error)}")  # Add debug logging
        print(f"Full error details: {error.__class__.__name__}")  # Print error class name
        print(f"Error traceback:", file=sys.stderr)  # Print full traceback
        import traceback
        traceback.print_exc()
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
        print("Error: Bot is already running! Exiting to prevent duplicate instances.")
        print("Use 'python kill_bots.py' to kill all instances and restart.")
        return

    if not TOKEN:
        print("Error: Discord token not found in environment variables!")
        return

    try:
        print("Initializing database...")
        # Initialize the database before starting the bot
        storage = GameStorage()
        print("Database initialized successfully!")
        
        print("Checking for running instance...")
        print("No other instance running, continuing...")
        # Start the keep alive server
        keep_alive()
        # Run the bot
        await bot.start(TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Failed to login. Please check your Discord token.")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}")
        print("Full error details:", file=sys.stderr)
        import traceback
        traceback.print_exc()

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