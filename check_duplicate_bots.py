
import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

# Get token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

async def check_for_duplicate_sessions():
    # Create a minimal client to check sessions
    intents = discord.Intents.default()
    client = commands.Bot(command_prefix='!', intents=intents)
    
    @client.event
    async def on_ready():
        print(f"Logged in as {client.user.name}")
        print(f"Bot ID: {client.user.id}")
        
        # Get session information
        sessions = await client.http.get_gateway()
        session_start_limit = sessions.get('session_start_limit', {})
        
        print("\n=== BOT SESSION INFORMATION ===")
        print(f"Total Sessions: {session_start_limit.get('total', 'Unknown')}")
        print(f"Remaining Sessions: {session_start_limit.get('remaining', 'Unknown')}")
        print(f"Reset After: {session_start_limit.get('reset_after', 'Unknown')} ms")
        print(f"Max Concurrency: {session_start_limit.get('max_concurrency', 'Unknown')}")
        
        # Check if we have multiple active sessions
        if session_start_limit.get('total', 1) - session_start_limit.get('remaining', 0) > 1:
            print("\n⚠️ WARNING: MULTIPLE BOT SESSIONS DETECTED!")
            print("You have more than one instance of this bot running.")
            print("This will cause duplicate responses and other issues.")
            print("\nRecommended steps:")
            print("1. Stop all bot instances on your local machine")
            print("2. If using Replit, check if the bot is running there")
            print("3. Restart only one instance of the bot")
        else:
            print("\n✅ Good news! Only one bot session is active.")
        
        await client.close()

    try:
        await client.start(TOKEN)
    except Exception as e:
        print(f"Error connecting to Discord: {e}")

# Run the check
asyncio.run(check_for_duplicate_sessions())
