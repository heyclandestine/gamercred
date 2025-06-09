import os
from flask import Flask, send_from_directory, jsonify, request
from dotenv import load_dotenv
import sqlite3
from flask import g # Import g
import requests # Import the requests library to make API calls
from flask_cors import CORS # Import CORS
import sys
import os
import aiohttp # Import aiohttp for async HTTP requests
from functools import lru_cache # Import lru_cache for caching
import time # Import time for cache expiration
from datetime import datetime
import pytz

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import GameStorage # Import GameStorage
from models import LeaderboardType # Import LeaderboardType
import asyncio

# Load environment variables (though we'll use the provided path directly for now)
# Get the directory where app.py is located
app_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the path to the .env file in the project root
env_path = os.path.join(app_dir, '..', '.env')
load_dotenv(dotenv_path=env_path)

# Debug print to check if the key was loaded
print(f"Debug: RAWG_API_KEY value after loading .env: {os.getenv('RAWG_API_KEY')}")
print(f"Debug: DISCORD_TOKEN value after loading .env: {os.getenv('DISCORD_TOKEN')}") # Debug print for Discord token

# Get the database path from the environment variable
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('LOCAL_DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("LOCAL_DATABASE_URL environment variable is not set")

# Initialize the GameStorage instance
storage = GameStorage()

# Use an absolute path for the static folder
static_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'website', 'public')
app = Flask(__name__, static_folder=static_folder_path)
CORS(app) # Enable CORS for all routes

DATABASE = 'C:/Users/kende/Downloads/DiscordCompanion/gamer_cred.db' # Use the manually provided path
RAWG_API_KEY = os.getenv('RAWG_API_KEY') # Get RAWG API key from environment variables
RAWG_API_URL = 'https://api.rawg.io/api'
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN') # Get Discord Token

cst = pytz.timezone('America/Chicago')

def format_timestamp_cst(timestamp):
    """Format a timestamp in CST"""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=pytz.UTC)
    return timestamp.astimezone(cst).strftime('%Y-%m-%d %H:%M:%S')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_db(error):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Serve index.html at the root route
@app.route('/')
def serve_index():
    return send_from_directory(static_folder_path, 'index.html')

# Route to serve the game.html file
@app.route('/game.html')
def serve_game():
    return send_from_directory(static_folder_path, 'game.html')

# Explicitly define a route for all static files
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(static_folder_path, filename)

# Add endpoint to fetch game data
# @app.route('/api/game/<game_name>')
# def get_game(game_name):
#     db = get_db()
#     cursor = db.execute('SELECT name, backloggd_url FROM games WHERE name = ?', (game_name,))
#     game_data = cursor.fetchone()

#     if game_data:
#         game_info = {
#             'name': game_data[0],
#             'backloggd_url': game_data[1]
#         }

#         # Call RAWG API to get description and cover art
#         rawg_response = requests.get(f'{RAWG_API_URL}/games?key={RAWG_API_KEY}&search={game_name}')

#         if rawg_response.status_code == 200:
#             rawg_data = rawg_response.json()
#             if rawg_data and rawg_data['results']:
#                 # Assuming the first result is the correct game
#                 game_info['description'] = rawg_data['results'][0].get('description_raw', 'No description available.')
#                 game_info['cover_image_url'] = rawg_data['results'][0].get('background_image', '')

#         return jsonify(game_info)
#     else:
#         return jsonify({'error': 'Game not found in database'}), 404

# Helper function to run async functions
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Cache for Discord user info with 5-minute expiration
@lru_cache(maxsize=1000)
def get_cached_discord_user_info(user_id):
    # Get the current time
    current_time = time.time()
    # Check if the cache entry exists and is not expired
    cache_key = f"{user_id}_{current_time // 300}"  # 300 seconds = 5 minutes
    # Run the async function in a sync context
    return run_async(get_discord_user_info(user_id))  # user_id is already a string

# Function to fetch Discord user info
async def get_discord_user_info(user_id_str):
    if not DISCORD_TOKEN:
        print("DISCORD_TOKEN not set.")
        return None
    
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}"
    }
    
    # First try the guild members endpoint since we know they were in our server
    guild_id = "693741073394040843"
    guild_url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id_str}"
    
    print(f"DEBUG: Attempting to fetch guild member info for user ID: {user_id_str}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(guild_url, headers=headers) as guild_response:
                print(f"DEBUG: Guild API response status for user ID {user_id_str}: {guild_response.status}")
                
                if guild_response.status == 200:
                    guild_data = await guild_response.json()
                    print(f"DEBUG: Guild API response data: {guild_data}")
                    user_data = guild_data.get('user', {})
                    avatar_hash = user_data.get('avatar')
                    
                    if avatar_hash:
                        if avatar_hash.startswith('a_'):
                            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_str}/{avatar_hash}.gif"
                        else:
                            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_str}/{avatar_hash}.png"
                    else:
                        # Use string manipulation for the default avatar index to avoid rounding
                        default_avatar_index = int(user_id_str[-1]) % 6
                        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_avatar_index}.png"
                    
                    # Get username from user data, fallback to display name from member data
                    username = user_data.get('username')
                    if not username and 'nick' in guild_data:
                        username = guild_data['nick']
                    if not username:
                        username = f'Unknown User {user_id_str}'
                    
                    return {
                        'username': username,
                        'avatar_url': avatar_url
                    }
                
                # If not found in guild, try global user endpoint
                print(f"DEBUG: User {user_id_str} not found in guild, trying global user endpoint")
                url = f"https://discord.com/api/v10/users/{user_id_str}"
                async with session.get(url, headers=headers) as response:
                    print(f"DEBUG: Global API response status for user ID {user_id_str}: {response.status}")
                    
                    if response.status == 200:
                        user_data = await response.json()
                        print(f"DEBUG: Global API response data: {user_data}")
                        avatar_hash = user_data.get('avatar')
                        
                        if avatar_hash:
                            if avatar_hash.startswith('a_'):
                                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_str}/{avatar_hash}.gif"
                            else:
                                avatar_url = f"https://cdn.discordapp.com/avatars/{user_id_str}/{avatar_hash}.png"
                        else:
                            # Use string manipulation for the default avatar index to avoid rounding
                            default_avatar_index = int(user_id_str[-1]) % 6
                            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_avatar_index}.png"
                        
                        username = user_data.get('username')
                        if not username:
                            username = f'Unknown User {user_id_str}'
                        
                        return {
                            'username': username,
                            'avatar_url': avatar_url
                        }
                    else:
                        print(f"DEBUG: User {user_id_str} not found in either guild or global endpoints")
                        # Return a default user object instead of None
                        return {
                            'username': f'Unknown User {user_id_str}',
                            'avatar_url': f'https://cdn.discordapp.com/embed/avatars/{int(user_id_str[-1]) % 6}.png'
                        }
    except Exception as e:
        print(f"Error fetching Discord user info for {user_id_str}: {e}")
        # Return a default user object instead of None
        return {
            'username': f'Unknown User {user_id_str}',
            'avatar_url': f'https://cdn.discordapp.com/embed/avatars/{int(user_id_str[-1]) % 6}.png'
        }

# Add endpoint to fetch leaderboard data
@app.route('/api/leaderboard')
def get_leaderboard():
    timeframe = request.args.get('timeframe', 'weekly')
    print(f"Fetching leaderboard for timeframe: {timeframe}")
    try:
        if timeframe == 'weekly' or timeframe == 'monthly':
            leaderboard_type = LeaderboardType.WEEKLY if timeframe == 'weekly' else LeaderboardType.MONTHLY
            # Get the current active period for the requested timeframe
            current_period = run_async(storage.get_or_create_current_period(leaderboard_type))
            # Get the leaderboard data for the current period
            leaderboard_data = run_async(storage.get_leaderboard_by_timeframe(leaderboard_type))
            print(f"Backend weekly/monthly data: {leaderboard_data}")

            # Format the data for the frontend
            formatted_data = []
            for user_id, credits, games_played, most_played_game, most_played_hours in leaderboard_data:
                # Convert user_id to string immediately
                user_id_str = str(user_id)
                # Use cached Discord user info
                discord_info = get_cached_discord_user_info(user_id_str)
                if discord_info:
                    avatar_url = discord_info['avatar_url']
                    username = discord_info['username']
                else:
                    avatar_url = "https://www.gravatar.com/avatar/?d=mp&s=50"
                    username = f"User{user_id_str}"
                
                formatted_data.append({
                    'user_id': user_id_str,
                    'username': username,
                    'avatar_url': avatar_url,
                    'points': credits,
                    'games_played': games_played,
                    'most_played_game': most_played_game,
                    'most_played_hours': most_played_hours
                })
        elif timeframe == 'alltime':
            # Get all-time leaderboard data
            alltime_leaderboard_data = storage.get_leaderboard()
            print(f"Backend all-time data: {alltime_leaderboard_data}")

            # Format the data for the frontend
            formatted_data = []
            for index, (user_id, total_credits) in enumerate(alltime_leaderboard_data):
                # Convert user_id to string immediately
                user_id_str = str(user_id)
                # Use cached Discord user info
                discord_info = get_cached_discord_user_info(user_id_str)
                if discord_info:
                    avatar_url = discord_info['avatar_url']
                    username = discord_info['username']
                else:
                    avatar_url = "https://www.gravatar.com/avatar/?d=mp&s=50"
                    username = f"User{user_id_str}"

                formatted_data.append({
                    'user_id': user_id_str,
                    'username': username,
                    'avatar_url': avatar_url,
                    'points': total_credits,
                    'games_played': 0,
                    'most_played_game': 'N/A',
                    'most_played_hours': 0
                })

        else:
            return jsonify({'error': 'Invalid timeframe specified'}), 400

        return jsonify(formatted_data)
    except Exception as e:
        print(f"Error getting leaderboard data: {str(e)}")
        return jsonify({'error': 'Failed to get leaderboard data'}), 500

# Add endpoint to fetch most popular games
@app.route('/api/popular-games')
def get_popular_games():
    timeframe = request.args.get('timeframe', 'weekly')
    print(f"Fetching popular games for timeframe: {timeframe}")
    try:
        # Use the new function to get aggregated game hours and box art URL
        # The storage function now returns (game_name, total_hours, box_art_url)
        game_data_from_storage = run_async(storage.get_total_game_hours_by_timeframe(timeframe))
        print(f"Backend popular games data from storage for {timeframe}: {game_data_from_storage}")

        # Format the data for the frontend
        formatted_data = []
        for game_name, total_hours, box_art_url in game_data_from_storage:
            if game_name and total_hours:
                 # Use the box_art_url fetched and stored by storage.py
                formatted_data.append({
                    'name': game_name, # Use name from storage
                    'hours': total_hours,
                    'cover_url': box_art_url if box_art_url else f"https://static-cdn.jtvnw.net/ttv-boxart/{game_name}-144x192.jpg" # Use stored URL, fallback to placeholder
                })

        # Sort by hours played and take top 5
        formatted_data.sort(key=lambda x: x['hours'], reverse=True)
        formatted_data = formatted_data[:5]  # Take top 5

        return jsonify(formatted_data)
    except Exception as e:
        print(f"Error getting popular games data: {str(e)}")
        return jsonify({'error': 'Failed to get popular games data'}), 500

# Add endpoint to fetch recent bonuses
@app.route('/api/recent-bonuses')
def get_recent_bonuses_endpoint():
    try:
        recent_bonuses_data = run_async(storage.get_recent_bonuses(limit=10))
        formatted_bonuses = []
        
        for bonus_data in recent_bonuses_data:
            user_id = bonus_data['user_id']
            discord_info = get_cached_discord_user_info(user_id)

            # Format timestamp in CST
            timestamp = bonus_data['timestamp']
            timestamp_str = format_timestamp_cst(timestamp)

            formatted_bonuses.append({
                'id': bonus_data['id'],
                'user_id': user_id,
                'credits': bonus_data['credits'],
                'reason': bonus_data['reason'],
                'granted_by': bonus_data['granted_by'],
                'timestamp': timestamp_str,
                'username': discord_info['username'] if discord_info else f'User{user_id}',
                'avatar_url': discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id}.jpg'
            })

        return jsonify(formatted_bonuses[:5])
    except Exception as e:
        print(f"Error processing /api/recent-bonuses: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch user overall stats
@app.route('/api/user-stats/<user_identifier>')
def get_user_stats_endpoint(user_identifier):
    try:
        # Get timeframe from query parameters, default to 'alltime'
        timeframe = request.args.get('timeframe', 'alltime')
        print(f"DEBUG: Fetching user stats for {user_identifier} with timeframe: {timeframe}") # Debug print

        # Keep as string to preserve precision
        user_id_str = str(user_identifier)
        
        # Get overall stats from storage (this always gets all-time total_credits and rank)
        user_overall_stats = storage.get_user_overall_stats(user_id_str)

        if not user_overall_stats:
            # Even if no stats, we might still have Discord info
            user_overall_stats = {'total_credits': 0, 'rank': None}

        # Get most played game for the specified timeframe (fetch top 3)
        most_played_games_data = run_async(storage.get_user_most_played_game_by_timeframe(user_id_str, timeframe, limit=3))

        # Fetch Discord user info using the cached function
        discord_info = get_cached_discord_user_info(user_id_str)  # Use string version

        # Combine stats with Discord info and most played game data
        formatted_stats = {
            'user_id': user_id_str,  # Use string version
            'total_credits': user_overall_stats['total_credits'],
            'rank': user_overall_stats['rank'],
            'username': discord_info['username'] if discord_info else f'User{user_id_str}', # Use fetched username or fallback
            'avatar_url': discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id_str}.jpg', # Use fetched avatar or fallback
            'most_played': most_played_games_data # Include list of most played games data
        }

        print(f"DEBUG: /api/user-stats/{user_identifier} returning: {formatted_stats}") # Debug print
        return jsonify(formatted_stats)
    except Exception as e:
        print(f"Error processing /api/user-stats/{user_identifier}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch user gaming history
@app.route('/api/user-stats/<user_identifier>/history')
def get_user_history_endpoint(user_identifier):
    try:
        # Keep as string to preserve precision
        user_id_str = str(user_identifier)
        
        # Get user's gaming history
        history = storage.get_user_gaming_history(user_id_str, limit=5)  # Limit to 5 entries
        
        # Format the history data
        formatted_history = []
        for entry in history:
            # Get game info to get box art URL
            game_info = storage.get_game_info(entry['game'])
            box_art_url = None
            if game_info:
                # Try to get box art from RAWG API
                try:
                    rawg_response = requests.get(f'{RAWG_API_URL}/games?key={RAWG_API_KEY}&search={entry["game"]}')
                    if rawg_response.status_code == 200:
                        rawg_data = rawg_response.json()
                        if rawg_data and rawg_data['results']:
                            box_art_url = rawg_data['results'][0].get('background_image')
                except Exception as e:
                    print(f"Error fetching RAWG data for {entry['game']}: {e}")
            
            formatted_history.append({
                'game': entry['game'],
                'hours': entry['hours'],
                'credits_earned': entry['credits_earned'],
                'timestamp': entry['timestamp'].isoformat(),
                'box_art_url': box_art_url
            })
        
        return jsonify(formatted_history)
    except Exception as e:
        print(f"Error processing /api/user-stats/{user_identifier}/history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch user leaderboard history
@app.route('/api/leaderboard-history')
def get_leaderboard_history_endpoint():
    try:
        user_identifier = request.args.get('user')
        if not user_identifier:
            return jsonify({'error': 'User identifier is required'}), 400
        
        # Keep as string to preserve precision
        user_id_str = str(user_identifier)
        
        # Get user's leaderboard history
        history = storage.get_user_placement_history(user_id_str)
        
        return jsonify(history)
    except Exception as e:
        print(f"Error processing /api/leaderboard-history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch recent gaming sessions
@app.route('/api/recent-activity')
def recent_activity():
    try:
        recent_sessions_data = run_async(storage.get_recent_gaming_sessions())
        formatted_sessions = []
        
        for session_data in recent_sessions_data:
            user_id = session_data['user_id']
            discord_info = get_cached_discord_user_info(user_id)
            username = discord_info['username'] if discord_info else f'User{user_id}'
            avatar_url = discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id}.jpg'

            # Format timestamp in CST
            timestamp = session_data['timestamp']
            timestamp_str = format_timestamp_cst(timestamp)

            formatted_sessions.append({
                'id': session_data['id'],
                'user_id': user_id,
                'game_id': session_data['game_id'],
                'hours': session_data['hours'],
                'timestamp': timestamp_str,
                'username': username,
                'avatar_url': avatar_url,
                'game_name': session_data['game_name'],
                'box_art_url': session_data['box_art_url']
            })

        return jsonify(formatted_sessions)
    except Exception as e:
        print(f"Error processing /api/recent-activity: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # In a production environment, you would use a production-ready WSGI server
    # For development, you can run with debug=True
    app.run(debug=True) 