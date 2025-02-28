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

# Singleton check to prevent multiple instances
def is_bot_already_running():
    """Check if another instance of the bot is already running"""
    try:
        # Try to create a socket with a unique name
        socket_name = "discord_gamer_cred_bot_socket"
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind('\0' + socket_name)
        return False  # Socket created successfully, no other instance running
    except socket.error:
        return True  # Socket creation failed, another instance is running

# Set up the bot with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Enable members intent for user information
intents.guilds = True   # Enable guilds intent for server information
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user.name}')
    print(f'Connected to {len(bot.guilds)} servers')

    # Add commands
    await bot.add_cog(GamingCommands(bot))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `!help` to see command usage.")
    elif isinstance(error, commands.errors.CommandNotFound):
        await ctx.send(f"❌ Command not found. Use `!help` to see available commands.")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")

def main():
    # Check if bot is already running
    if is_bot_already_running():
        print("Error: Bot is already running! Exiting to prevent duplicate instances.")
        print("Use 'python kill_bots.py' to kill all instances and restart.")
        return

    if not TOKEN:
        print("Error: Discord token not found in environment variables!")
        return

    try:
        print("Starting bot with single instance...")
        # Start the keep alive server
        keep_alive()
        # Run the bot
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Failed to login. Please check your Discord token.")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()