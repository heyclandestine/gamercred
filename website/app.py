from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for
import os
import sys # Import the sys module
import re # Import re for HTML cleaning
from dotenv import load_dotenv
from flask_cors import CORS
from requests_oauthlib import OAuth2Session
print("sys.path before storage import:", sys.path) # Print sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Add parent directory to path
from storage import GameStorage # Import GameStorage
import requests # Import requests library
from functools import lru_cache
import time
import asyncio
import aiohttp # Import aiohttp for async requests
from datetime import datetime # Import datetime
from models import LeaderboardType # Import LeaderboardType
import traceback
from sqlalchemy import text
from sqlalchemy.ext.declarative import declarative_base
from models import Base # Import Base for table creation
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Load environment variables
load_dotenv()

# Discord OAuth2 Configuration
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://localhost:5000/callback')
DISCORD_AUTH_URL = 'https://discord.com/api/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
DISCORD_API_URL = 'https://discord.com/api/v10'

# Initialize Flask app with correct static folder path
app = Flask(__name__, 
            static_folder='public',
            static_url_path='',
            template_folder='public')

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# Add debug logging for database URL
database_url = os.getenv('DATABASE_URL')
print(f"Database URL: {database_url}")

# Initialize storage
storage = GameStorage()

# Cache for Discord user info with 5-minute expiration
discord_user_cache = {}
discord_user_cache_timestamps = {}

# Cache for leaderboard and popular games data
cache = {
    'leaderboard': {'data': None, 'timestamp': 0},
    'popular_games': {'data': None, 'timestamp': 0},
    'recent_activity': {'data': None, 'timestamp': 0}
}

# Get RAWG API key from environment variable
RAWG_API_KEY = os.getenv('RAWG_API_KEY')
RAWG_API_URL = os.getenv('RAWG_API_URL', 'https://api.rawg.io/api')

if not RAWG_API_KEY:
    print("Warning: RAWG_API_KEY environment variable not set. Game details may not load.")

# Add a function to refresh the cache
def refresh_cache():
    global cache
    current_time = time.time()
    try:
        if current_time - cache['leaderboard']['timestamp'] > 30:
            print("Refreshing leaderboard cache...")
            try:
                # Get current period and leaderboard data for weekly
                current_period = run_async(storage.get_or_create_current_period(LeaderboardType.WEEKLY))
                print(f"Got current period: {current_period}")
                leaderboard_data = run_async(storage.get_leaderboard_by_timeframe(LeaderboardType.WEEKLY, period=current_period))
                print(f"Got leaderboard data: {leaderboard_data}")
                cache['leaderboard']['data'] = leaderboard_data
                cache['leaderboard']['timestamp'] = current_time
                print("Leaderboard cache refreshed successfully")
            except Exception as e:
                print(f"Error refreshing leaderboard cache: {str(e)}")
                print("Full traceback:")
                traceback.print_exc()
        
        if current_time - cache['popular_games']['timestamp'] > 30:
            print("Refreshing popular games cache...")
            try:
                cache['popular_games']['data'] = run_async(storage.get_total_game_hours_by_timeframe('weekly'))
                cache['popular_games']['timestamp'] = current_time
                print("Popular games cache refreshed successfully")
            except Exception as e:
                print(f"Error refreshing popular games cache: {str(e)}")
                print("Full traceback:")
                traceback.print_exc()
        
        if current_time - cache['recent_activity']['timestamp'] > 30:
            print("Refreshing recent activity cache...")
            try:
                cache['recent_activity']['data'] = run_async(storage.get_recent_gaming_sessions())
                cache['recent_activity']['timestamp'] = current_time
                print("Recent activity cache refreshed successfully")
            except Exception as e:
                print(f"Error refreshing recent activity cache: {str(e)}")
                print("Full traceback:")
                traceback.print_exc()
    except Exception as e:
        print(f"Error in refresh_cache: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        # Don't raise the exception, just log it and continue

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
    if not os.getenv('DISCORD_TOKEN'):
        print("DISCORD_TOKEN not set.")
        return None

    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}"
    }
    
    # First try the guild members endpoint since we know they were in our server
    guild_id = "693741073394040843"
    guild_url = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id_str}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(guild_url, headers=headers) as guild_response:
                if guild_response.status == 200:
                    guild_data = await guild_response.json()
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
                url = f"https://discord.com/api/v10/users/{user_id_str}"
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_data = await response.json()
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
                        # Return a default user object instead of None
                        return {
                            'username': f'Unknown User {user_id_str}',
                            'avatar_url': f'https://cdn.discordapp.com/embed/avatars/{int(user_id_str[-1]) % 6}.png'
                        }
    except Exception as e:
        # Return a default user object instead of None
        return {
            'username': f'Unknown User {user_id_str}',
            'avatar_url': f'https://cdn.discordapp.com/embed/avatars/{int(user_id_str[-1]) % 6}.png'
        }

# Helper function to run async functions
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        print(f"Error in run_async: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        raise

# Helper function to clean HTML and truncate text
def clean_and_truncate_description(html_text):
    if not html_text:
        return "No description available."
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_text)
    # Replace HTML entities
    clean_text = clean_text.replace('&quot;', '"').replace('&#39;', "'").replace('&amp;', '&')
    # Removed truncation logic
    return clean_text

# Static file routes
@app.route('/')
def index():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"Error serving index.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving index.html", 500

@app.route('/game.html')
def game():
    try:
        return send_from_directory(app.static_folder, 'game.html')
    except Exception as e:
        print(f"Error serving game.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving game.html", 500

@app.route('/user.html')
def user():
    try:
        return send_from_directory(app.static_folder, 'user.html')
    except Exception as e:
        print(f"Error serving user.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving user.html", 500

@app.route('/<path:path>')
def serve_static(path):
    try:
        # Skip API routes
        if path.startswith('api/'):
            return jsonify({'error': 'API endpoint not found'}), 404
        
        # Skip root path
        if path == '':
            return send_from_directory(app.static_folder, 'index.html')
        
        # Handle HTML files
        if path.endswith('.html'):
            return send_from_directory(app.static_folder, path)
        
        # Handle static assets
        return send_from_directory(app.static_folder, path)
    except Exception as e:
        print(f"Error serving static file {path}: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return f"Error serving {path}", 500

# API routes
@app.route('/api/game')
def get_game():
    try:
        game_name = request.args.get('name')
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        # Get game info from database
        game_db_info = storage.get_game_stats(game_name)
        if not game_db_info:
            return jsonify({'error': 'Game not found'}), 404

        # Get additional info from RAWG
        rawg_data = run_async(storage.fetch_game_details_from_rawg(game_name))
        if rawg_data:
            description = rawg_data.get('description', '')
            box_art_url = rawg_data.get('box_art_url', '')
            backloggd_url = rawg_data.get('backloggd_url', '')
        else:
            description = ''
            box_art_url = ''
            backloggd_url = ''

        print(f"DEBUG: Description after RAWG fetch: {description}")

        # Combine database info with API info
        final_game_data = {
            'name': game_db_info['name'],  # Use the name from the database
            'box_art_url': box_art_url or game_db_info.get('box_art_url', ''),
            'description': description,
            'backloggd_url': backloggd_url or game_db_info.get('backloggd_url', ''),
            'unique_players': game_db_info.get('unique_players', 0),
            'total_hours': game_db_info.get('total_hours', 0.0),
            'credits_per_hour': game_db_info.get('credits_per_hour', 1.0),
            'avg_hours': game_db_info.get('total_hours', 0.0) / game_db_info.get('unique_players', 1) if game_db_info.get('unique_players', 0) > 0 else 0.0,
        }

        return jsonify(final_game_data)
    except Exception as e:
        print(f"Error getting game info: {str(e)}")
        return jsonify({'error': 'Failed to get game information'}), 500

@app.route('/api/game/players')
def get_game_players():
    try:
        game_name = request.args.get('name')
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        players_data = storage.get_recent_players_for_game(game_name, timeframe='weekly', limit=6)

        # Fetch Discord info for players
        formatted_players = []
        for player in players_data:
            user_id = player['user_id']
            discord_info = get_cached_discord_user_info(user_id)
            formatted_players.append({
                'user_id': user_id,
                'username': discord_info['username'] if discord_info else f'User{user_id}',
                'avatar_url': discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id}.jpg',
                'hours': player['hours']
            })

        return jsonify(formatted_players)

    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/game/activity')
def get_game_activity():
    try:
        game_name = request.args.get('name')
        limit = int(request.args.get('limit', 15))  # Get limit from query params, default to 15
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        activity_data = storage.get_recent_activity_for_game(game_name, limit=limit)

        # Fetch Discord info for users in activity
        formatted_activity = []
        for activity in activity_data:
            user_id = activity['user_id']
            discord_info = get_cached_discord_user_info(user_id)
            formatted_activity.append({
                'id': activity['id'],
                'user_id': user_id,
                'hours': activity['hours'],
                'timestamp': activity['timestamp'],
                'username': discord_info['username'] if discord_info else f'User{user_id}',
                'avatar_url': discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id}.jpg',
                'game_name': activity['game_name'],
                'type': 'played',
                'box_art_url': activity['box_art_url']
            })

        return jsonify(formatted_activity)

    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler for all routes"""
    print(f"ERROR: {str(error)}")
    print("Full traceback:")
    traceback.print_exc()
    return jsonify({'error': str(error)}), 500

# Add endpoint to fetch leaderboard data
@app.route('/api/leaderboard')
def get_leaderboard():
    timeframe = request.args.get('timeframe', 'weekly')
    try:
        print(f"Getting leaderboard for timeframe: {timeframe}")
        if timeframe == 'weekly':
            # For weekly, use the cache
            print("Using weekly cache")
            refresh_cache()
            leaderboard_data = cache['leaderboard']['data']
            print(f"Got leaderboard data from cache: {leaderboard_data}")
            if not leaderboard_data:
                print("No leaderboard data found in cache")
                return jsonify([])
            formatted_data = []
            for user_id, credits, games_played, most_played_game, most_played_hours, total_hours in leaderboard_data:
                try:
                    user_id_str = str(user_id)
                    discord_info = get_cached_discord_user_info(user_id_str)
                    if discord_info:
                        user_data = {
                            'user_id': user_id_str,
                            'username': discord_info.get('username', 'Unknown'),
                            'avatar_url': discord_info.get('avatar_url', ''),
                            'total_credits': float(credits or 0),
                            'games_played': int(games_played or 0),
                            'most_played_game': most_played_game or 'Unknown',
                            'most_played_hours': float(most_played_hours or 0),
                            'total_hours': float(total_hours or 0)
                        }
                        formatted_data.append(user_data)
                except Exception as e:
                    print(f"Error formatting user data for user {user_id}: {str(e)}")
                    print("Full traceback:")
                    traceback.print_exc()
            print(f"Returning formatted data: {formatted_data}")
            return jsonify(formatted_data)
        elif timeframe == 'monthly':
            # For monthly, query the database directly
            print("Getting monthly leaderboard")
            leaderboard_type = LeaderboardType.MONTHLY
            current_period = run_async(storage.get_or_create_current_period(leaderboard_type))
            print(f"Got current period: {current_period}")
            leaderboard_data = run_async(storage.get_leaderboard_by_timeframe(leaderboard_type, period=current_period))
            print(f"Got leaderboard data: {leaderboard_data}")
            if not leaderboard_data:
                print("No leaderboard data found")
                return jsonify([])
            formatted_data = []
            for user_id, credits, games_played, most_played_game, most_played_hours, total_hours in leaderboard_data:
                try:
                    user_id_str = str(user_id)
                    discord_info = get_cached_discord_user_info(user_id_str)
                    if discord_info:
                        user_data = {
                            'user_id': user_id_str,
                            'username': discord_info.get('username', 'Unknown'),
                            'avatar_url': discord_info.get('avatar_url', ''),
                            'total_credits': float(credits or 0),
                            'games_played': int(games_played or 0),
                            'most_played_game': most_played_game or 'Unknown',
                            'most_played_hours': float(most_played_hours or 0),
                            'total_hours': float(total_hours or 0)
                        }
                        formatted_data.append(user_data)
                except Exception as e:
                    print(f"Error formatting user data for user {user_id}: {str(e)}")
                    print("Full traceback:")
                    traceback.print_exc()
            print(f"Returning formatted data: {formatted_data}")
            return jsonify(formatted_data)
        elif timeframe == 'alltime':
            # Get all-time leaderboard data
            print("Getting all-time leaderboard")
            leaderboard_data = storage.get_alltime_leaderboard()
            print(f"Got leaderboard data: {leaderboard_data}")
            if not leaderboard_data:
                print("No leaderboard data found")
                return jsonify([])
            formatted_data = []
            for user_id, credits, games_played, most_played_game, most_played_hours, total_hours in leaderboard_data:
                try:
                    user_id_str = str(user_id)
                    discord_info = get_cached_discord_user_info(user_id_str)
                    if discord_info:
                        user_data = {
                            'user_id': user_id_str,
                            'username': discord_info.get('username', 'Unknown'),
                            'avatar_url': discord_info.get('avatar_url', ''),
                            'total_credits': float(credits or 0),
                            'games_played': int(games_played or 0),
                            'most_played_game': most_played_game or 'Unknown',
                            'most_played_hours': float(most_played_hours or 0),
                            'total_hours': float(total_hours or 0)
                        }
                        formatted_data.append(user_data)
                except Exception as e:
                    print(f"Error formatting user data for user {user_id}: {str(e)}")
                    print("Full traceback:")
                    traceback.print_exc()
            print(f"Returning formatted data: {formatted_data}")
            return jsonify(formatted_data)
        else:
            print(f"Invalid timeframe specified: {timeframe}")
            return jsonify({'error': 'Invalid timeframe specified'}), 400
    except Exception as e:
        print(f"Error getting leaderboard data: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return jsonify({'error': 'Failed to get leaderboard data'}), 500

# Add endpoint to fetch recent bonuses
@app.route('/api/recent-bonuses')
def get_recent_bonuses():
    try:
        recent_bonuses_data = run_async(storage.get_recent_bonuses(limit=10))

        formatted_bonuses = []
        for bonus_data in recent_bonuses_data:
            user_id = bonus_data['user_id']
            discord_info = get_cached_discord_user_info(user_id)
            username = discord_info['username'] if discord_info else f'User{user_id}'
            avatar_url = discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id}.jpg'

            timestamp = bonus_data['timestamp']
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)

            formatted_bonuses.append({
                'id': bonus_data['id'],
                'user_id': user_id,
                'username': username,
                'avatar_url': avatar_url,
                'credits': bonus_data['credits'],
                'reason': bonus_data['reason'],
                'granted_by': bonus_data['granted_by'],
                'timestamp': timestamp_str
            })

        return jsonify(formatted_bonuses)
    except Exception as e:
        return jsonify({'error': 'Failed to get recent bonuses'}), 500

# Add endpoint to fetch popular games data
@app.route('/api/popular-games')
def get_popular_games():
    timeframe = request.args.get('timeframe', 'weekly')
    try:
        if timeframe == 'weekly':
            refresh_cache()
            popular_games_data = cache['popular_games']['data']
            if not popular_games_data:
                return jsonify([])
            formatted_data = []
            for game_name, total_hours, box_art_url in popular_games_data:
                # Format the game name with proper capitalization
                name = game_name.strip()
                if name:
                    # First, capitalize the first letter of the entire string
                    name = name[0].upper() + name[1:]
                    
                    # Then capitalize each word, preserving Roman numerals
                    words = name.split()
                    formatted_words = []
                    for word in words:
                        # Check if the word is a Roman numeral (case-insensitive)
                        roman_numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV']
                        if word.upper() in roman_numerals:
                            formatted_words.append(word.upper())
                        else:
                            formatted_words.append(word.capitalize())
                    
                    name = ' '.join(formatted_words)

                formatted_data.append({
                    'name': name or 'Unknown',
                    'total_hours': float(total_hours or 0),
                    'box_art_url': box_art_url or ''
                })
            final_popular_games = formatted_data[:5]
            return jsonify(final_popular_games)
        else:
            # For other timeframes, query the database directly
            popular_games_data = run_async(storage.get_total_game_hours_by_timeframe(timeframe))
            if not popular_games_data:
                return jsonify([])
            formatted_data = []
            for game_name, total_hours, box_art_url in popular_games_data:
                # Format the game name with proper capitalization
                name = game_name.strip()
                if name:
                    # First, capitalize the first letter of the entire string
                    name = name[0].upper() + name[1:]
                    
                    # Then capitalize each word, preserving Roman numerals
                    words = name.split()
                    formatted_words = []
                    for word in words:
                        # Check if the word is a Roman numeral (case-insensitive)
                        roman_numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV']
                        if word.upper() in roman_numerals:
                            formatted_words.append(word.upper())
                        else:
                            formatted_words.append(word.capitalize())
                    
                    name = ' '.join(formatted_words)

                formatted_data.append({
                    'name': name or 'Unknown',
                    'total_hours': float(total_hours or 0),
                    'box_art_url': box_art_url or ''
                })
            final_popular_games = formatted_data[:5]
            return jsonify(final_popular_games)
    except Exception as e:
        return jsonify({'error': 'Failed to get popular games'}), 500

# Add endpoint to fetch user overall stats
@app.route('/api/user-stats/<user_identifier>')
def get_user_stats_endpoint(user_identifier):
    try:
        # Get timeframe from query parameters, default to 'alltime'
        timeframe = request.args.get('timeframe', 'alltime')
        
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

        # --- Update username in DB if missing or outdated ---
        if discord_info and discord_info.get('username'):
            storage.update_user_username_and_avatar(
                user_id_str,
                discord_info['username'],
                discord_info.get('avatar_url')
            )

        # Combine stats with Discord info and most played game data
        formatted_stats = {
            'user_id': user_id_str,  # Use string version
            'total_credits': user_overall_stats.get('total_credits', 0),
            'rank': user_overall_stats.get('rank'),
            'username': discord_info.get('username', f'User{user_id_str}'), # Use fetched username or fallback
            'avatar_url': discord_info.get('avatar_url', f'https://randomuser.me/api/portraits/men/{user_id_str}.jpg'), # Use fetched avatar or fallback
            'most_played': most_played_games_data # Include list of most played games data
        }

        return jsonify(formatted_stats)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch user gaming history (recent activity)
@app.route('/api/user-stats/<user_identifier>/history')
def get_user_history_endpoint(user_identifier):
    try:
        start_total = time.time()
        
        # Keep as string to preserve precision
        user_id_str = str(user_identifier)
        
        # Profile DB query
        start_db = time.time()
        user_history = storage.get_user_gaming_history(user_id_str) # Removed limit
        end_db = time.time()
        
        if not user_history:
            return jsonify([])

        # Batch fetch game info
        game_names = list({entry.get('game') for entry in user_history if entry.get('game')})
        
        start_batch = time.time()
        game_info_map = storage.get_multiple_game_stats(game_names)
        end_batch = time.time()

        # Format the history data
        formatted_history = []
        start_loop = time.time()
        for entry in user_history:
            try:
                game_name = entry.get('game')
                game_info = game_info_map.get(game_name, {})
                box_art_url = game_info.get('box_art_url')
                
                # Get Discord info for the user
                discord_info = get_cached_discord_user_info(user_id_str)
                username = discord_info['username'] if discord_info else f'User{user_id_str}'
                avatar_url = discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id_str}.jpg'
                
                formatted_entry = {
                    'game_name': game_name or 'Unknown Game',
                    'hours': float(entry.get('hours', 0.0)),
                    'credits_earned': float(entry.get('credits_earned', 0.0)),
                    'timestamp': entry.get('timestamp', datetime.now()).isoformat(),
                    'box_art_url': box_art_url,
                    'user_id': user_id_str,
                    'username': username,
                    'avatar_url': avatar_url
                }
                formatted_history.append(formatted_entry)
            except Exception as e:
                continue

        end_loop = time.time()
        print(f"DEBUG: Total endpoint time: {end_loop - start_total:.3f} seconds")
        print(f"DEBUG: Returning {len(formatted_history)} formatted entries")
        
        return jsonify(formatted_history)
        
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# Add endpoint to fetch user leaderboard history
@app.route('/api/user-stats/<user_identifier>/leaderboard-history')
def get_user_leaderboard_history(user_identifier):
    try:
        # Get optional type filter from query params
        type_param = request.args.get('type')
        leaderboard_type = None
        if type_param:
            from models import LeaderboardType
            if type_param.lower() == 'weekly':
                leaderboard_type = LeaderboardType.WEEKLY
            elif type_param.lower() == 'monthly':
                leaderboard_type = LeaderboardType.MONTHLY
            else:
                return jsonify({'error': 'Invalid leaderboard type'}), 400

        # Keep as string to preserve precision
        user_id_str = str(user_identifier)

        # Get leaderboard history from storage, optionally filtered by type
        leaderboard_history = storage.get_user_placement_history(user_id_str, leaderboard_type=leaderboard_type)

        # Format the history data with Discord info
        formatted_history = []
        for entry in leaderboard_history:
            # Get Discord info for the user
            discord_info = get_cached_discord_user_info(user_id_str)
            username = discord_info.get('username', f'User{user_id_str}')
            avatar_url = discord_info.get('avatar_url', f'https://randomuser.me/api/portraits/men/{user_id_str}.jpg')

            # Format the dates properly
            start_date = entry.get('start_time')
            end_date = entry.get('end_time')
            
            # Format dates as strings in YYYY-MM-DD format
            start_date_str = start_date.split('T')[0] if start_date else None
            end_date_str = end_date.split('T')[0] if end_date else None
            
            formatted_entry = {
                **entry,
                'username': username,
                'avatar_url': avatar_url,
                'start_date': start_date_str,
                'end_date': end_date_str
            }
            formatted_history.append(formatted_entry)

        return jsonify(formatted_history)
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch recent gaming sessions
@app.route('/api/recent-activity')
def recent_activity():
    try:
        refresh_cache()
        recent_sessions_data = cache['recent_activity']['data']
        if not recent_sessions_data:
            return jsonify([])
        formatted_sessions = []
        for session in recent_sessions_data:
            user_id_str = str(session['user_id'])
            discord_info = get_cached_discord_user_info(user_id_str)
            if discord_info:
                formatted_sessions.append({
                    'id': session['id'],
                    'user_id': user_id_str,
                    'username': discord_info.get('username', 'Unknown'),
                    'avatar_url': discord_info.get('avatar_url', ''),
                    'game_name': session['game_name'],
                    'hours': session['hours'],
                    'timestamp': session['timestamp'].isoformat(),
                    'box_art_url': session['box_art_url']
                })
        return jsonify(formatted_sessions)
    except Exception as e:
        return jsonify({'error': 'Failed to get recent activity'}), 500

@app.route('/api/search')
def search_api():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'users': [], 'games': []})

    # Search games by partial name match (case-insensitive)
    games = storage.search_games_by_name(query)
    # Search users by partial username match (case-insensitive)
    users = storage.search_users_by_name(query)

    return jsonify({'games': games, 'users': users})

@app.route('/api/all-games')
def get_all_games():
    try:
        # Test database connection
        with storage.Session() as session:
            try:
                result = session.execute(text("SELECT 1")).scalar()
                
                # Check if tables exist
                tables = session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)).fetchall()
                
                # Check games table specifically
                games_count = session.execute(text("SELECT COUNT(*) FROM games")).scalar()
            except Exception as e:
                print(f"ERROR: Database query failed: {str(e)}")
                print("Full traceback:")
                traceback.print_exc()
                raise
        
        games_data = storage.get_all_games_with_stats()
        response = jsonify(games_data)
        # Prevent caching
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        return jsonify({'error': 'Failed to get all games'}), 500

@app.route('/login')
def login():
    """Redirect to Discord OAuth2 login page"""
    return redirect('https://discord.com/oauth2/authorize?client_id=1344451764530708571&response_type=code&redirect_uri=https%3A%2F%2Fgamercred.onrender.com%2Fcallback&scope=identify+guilds+email+guilds.join+connections')
    #return redirect('https://discord.com/oauth2/authorize?client_id=1344451764530708571&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A5000%2Fcallback&scope=identify+guilds+email+guilds.join+connections')

@app.route('/callback')
def callback():
    """Handle the OAuth2 callback from Discord"""
    if request.values.get('error'):
        return f"Error: {request.values['error']}"
    
    code = request.values.get('code')
    if not code:
        return "No code provided", 400

    # Exchange the code for an access token
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers)
    if response.status_code != 200:
        return f"Error getting token: {response.text}", 400
    
    token_data = response.json()
    access_token = token_data['access_token']
    
    # Get user info
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    user_response = requests.get(f'{DISCORD_API_URL}/users/@me', headers=headers)
    if user_response.status_code != 200:
        return f"Error getting user info: {user_response.text}", 400
    
    user = user_response.json()
    
    # Get user's guilds
    guilds_response = requests.get(f'{DISCORD_API_URL}/users/@me/guilds', headers=headers)
    guilds = guilds_response.json() if guilds_response.status_code == 200 else []
    
    # Get user's connections
    connections_response = requests.get(f'{DISCORD_API_URL}/users/@me/connections', headers=headers)
    connections = connections_response.json() if connections_response.status_code == 200 else []
    
    # Store the access token in a cookie
    resp = redirect(url_for('index'))
    # Set cookies to expire in 30 days
    resp.set_cookie('discord_token', access_token, httponly=True, max_age=30*24*60*60)
    resp.set_cookie('user_id', user['id'], httponly=True, max_age=30*24*60*60)
    resp.set_cookie('username', user['username'], httponly=True, max_age=30*24*60*60)
    resp.set_cookie('avatar', user.get('avatar', ''), httponly=True, max_age=30*24*60*60)
    
    return resp

@app.route('/logout')
def logout():
    """Log out the user"""
    resp = redirect(url_for('index'))
    resp.delete_cookie('discord_token')
    resp.delete_cookie('user_id')
    resp.delete_cookie('username')
    resp.delete_cookie('avatar')
    return resp

@app.route('/api/user')
def get_user():
    """Get the current user's information"""
    access_token = request.cookies.get('discord_token')
    if not access_token:
        return jsonify({'error': 'Not logged in'}), 401
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    user_response = requests.get(f'{DISCORD_API_URL}/users/@me', headers=headers)
    if user_response.status_code != 200:
        return jsonify({'error': 'Invalid token'}), 401
    
    user = user_response.json()
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'avatar': user.get('avatar'),
        'email': user.get('email')
    })

@app.route('/api/log-game', methods=['POST'])
def log_game():
    """Log a new game session"""
    try:
        data = request.json
        if not data:
            logger.warning("No data provided for game logging")
            return jsonify({'error': 'No data provided'}), 400

        user_id = data.get('user_id')
        game_name = data.get('game_name')
        hours = data.get('hours')

        if not all([user_id, game_name, hours]):
            logger.warning(f"Missing required fields for game logging. Received: {data}")
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            hours = float(hours)
        except ValueError:
            logger.warning(f"Invalid hours value: {hours}")
            return jsonify({'error': 'Hours must be a number'}), 400

        logger.info(f"Logging game session for user {user_id}: {game_name} - {hours} hours")
        
        try:
            storage.log_game_session(user_id, game_name, hours)
            return jsonify({'message': 'Game session logged successfully'}), 200
        except Exception as e:
            logger.error(f"Error in storage.log_game_session: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to log game session: {str(e)}'}), 500

    except Exception as e:
        error_msg = f"Error logging game session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/search-games', methods=['GET'])
def search_games():
    """Search for games by name"""
    try:
        query = request.args.get('query', '').strip()
        if not query:
            return jsonify([])

        # Get games from storage that match the query
        games = storage.search_games(query)
        
        # Format the response
        results = [{
            'name': game.name,
            'box_art_url': game.box_art_url
        } for game in games]

        return jsonify(results)

    except Exception as e:
        logger.error(f"Error searching games: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to search games'}), 500

@app.route('/api/user-stats/<user_identifier>/game')
def get_user_game_stats_endpoint(user_identifier):
    try:
        game_name = request.args.get('name')
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        # Get user's stats for this game
        user_game_stats = storage.get_user_game_stats(user_identifier, game_name)
        
        if not user_game_stats:
            return jsonify({
                'total_hours': 0,
                'total_credits': 0,
                'total_sessions': 0,
                'first_played': None,
                'last_played': None
            })

        return jsonify(user_game_stats)

    except Exception as e:
        print(f"Error getting user game stats: {str(e)}")
        return jsonify({'error': 'Failed to get user game stats'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 