from flask import Flask, render_template, jsonify, request, send_from_directory, redirect, url_for, make_response
import os
import sys # Import the sys module
import re # Import re for HTML cleaning
from dotenv import load_dotenv
from flask_cors import CORS
from requests_oauthlib import OAuth2Session
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
from sqlalchemy.sql import func
from models import GameReview, GameRating, GameCompletion, GameScreenshot, UserStats, Game
from sqlalchemy.orm import sessionmaker
from models import UserPreferences

# Set up basic logging
logging.basicConfig(
    level=logging.WARNING,  # Change from INFO to WARNING
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
logger.info("Storage initialized")

# Cache for Discord user info with 5-minute expiration
discord_user_cache = {}
discord_user_cache_timestamps = {}

# Cache for leaderboard and popular games data
cache = {
    'leaderboard': {'data': None, 'timestamp': 0},
    'popular_games': {'data': None, 'timestamp': 0},
    'recent_activity': {'data': None, 'timestamp': 0}
}

# Cache for background files (1 hour expiration)
background_file_cache = {}
background_file_cache_timestamps = {}

# Get RAWG API key from environment variable
RAWG_API_KEY = os.getenv('RAWG_API_KEY')
RAWG_API_URL = os.getenv('RAWG_API_URL', 'https://api.rawg.io/api')

if not RAWG_API_KEY:
    logger.warning("RAWG_API_KEY environment variable not set. Game details may not load.")

# Add a function to refresh the cache
def refresh_cache():
    global cache
    current_time = time.time()
    try:
        if current_time - cache['leaderboard']['timestamp'] > 30:
            try:
                # Get leaderboard data for weekly
                leaderboard_data = run_async(storage.get_leaderboard_by_timeframe(LeaderboardType.WEEKLY))
                cache['leaderboard']['data'] = leaderboard_data
                cache['leaderboard']['timestamp'] = current_time
            except Exception as e:
                logger.error(f"Error refreshing leaderboard cache: {str(e)}")
    except Exception as e:
        logger.error(f"Error in refresh_cache: {str(e)}")

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
        return send_from_directory(app.static_folder, 'pages/index.html')
    except Exception as e:
        print(f"Error serving index.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving index.html", 500

@app.route('/game.html')
def game():
    try:
        return send_from_directory(app.static_folder, 'pages/game.html')
    except Exception as e:
        print(f"Error serving game.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving game.html", 500

@app.route('/user.html')
def user():
    """Serve the user profile page"""
    try:
        return send_from_directory(app.static_folder, 'pages/user.html')
    except Exception as e:
        print(f"Error serving user.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving user.html", 500

@app.route('/user_stats.html')
def user_stats():
    """Serve the user stats page"""
    try:
        return send_from_directory(app.static_folder, 'pages/user_stats.html')
    except Exception as e:
        print(f"Error serving user_stats.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving user_stats.html", 500

@app.route('/all_games.html')
def all_games():
    try:
        return send_from_directory(app.static_folder, 'pages/all_games.html')
    except Exception as e:
        print(f"Error serving all_games.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving all_games.html", 500

@app.route('/setrate.html')
def setrate():
    try:
        return send_from_directory(app.static_folder, 'pages/setrate.html')
    except Exception as e:
        print(f"Error serving setrate.html: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return "Error serving setrate.html", 500

@app.route('/<path:path>')
def serve_static(path):
    try:
        # Skip API routes
        if path.startswith('api/'):
            return jsonify({'error': 'API endpoint not found'}), 404
        
        # Skip root path
        if path == '':
            return send_from_directory(app.static_folder, 'pages/index.html')
        
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

# Serve uploaded backgrounds (images/videos) as static files
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    try:
        # Split the filename to get the directory and file
        parts = filename.split('/')
        if len(parts) > 1:
            # If there are subdirectories (like backgrounds/images/file.jpg)
            subdir = '/'.join(parts[:-1])  # Get the subdirectory path
            file = parts[-1]  # Get the actual filename
            directory = os.path.join(app.static_folder, 'uploads', subdir)
        else:
            # If it's just a filename in the uploads root
            directory = os.path.join(app.static_folder, 'uploads')
            file = filename
        
        # Check if directory exists
        if not os.path.exists(directory):
            print(f"ERROR: Directory does not exist: {directory}")
            return jsonify({'error': 'Directory not found'}), 404
        
        # Check if file exists
        file_path = os.path.join(directory, file)
        if not os.path.exists(file_path):
            print(f"ERROR: File does not exist: {file_path}")
            return jsonify({'error': 'File not found'}), 404
        
        print(f"Serving file: {file_path}")
        return send_from_directory(directory, file)
    except Exception as e:
        print(f"ERROR in serve_uploads: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

# API routes
@app.route('/api/game')
def get_game():
    try:
        game_name = request.args.get('name')
        print(f"DEBUG: Requested game name: {game_name}")
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        # Get game info from database
        print(f"DEBUG: Calling storage.get_game_stats for: {game_name}")
        game_db_info = storage.get_game_stats(game_name)
        print(f"DEBUG: Game DB info result: {game_db_info}")
        if not game_db_info:
            return jsonify({'error': 'Game not found'}), 404

        # Use stored description from database
        description = game_db_info.get('description', '')
        box_art_url = game_db_info.get('box_art_url', '')
        backloggd_url = game_db_info.get('backloggd_url', '')

        # Only fetch from RAWG API if we don't have the data in the database
        if not description or not box_art_url:
            rawg_data = run_async(storage.fetch_game_details_from_rawg(game_name))
            if rawg_data:
                # Use RAWG data to fill in missing information
                if not description:
                    description = rawg_data.get('description', '')
                if not box_art_url:
                    box_art_url = rawg_data.get('box_art_url', '')
                if not backloggd_url:
                    backloggd_url = rawg_data.get('backloggd_url', '')

        # Combine database info with API info
        final_game_data = {
            'name': game_db_info['name'],  # Use the name from the database
            'box_art_url': box_art_url,
            'description': description,
            'backloggd_url': backloggd_url,
            'unique_players': game_db_info.get('unique_players', 0),
            'total_hours': game_db_info.get('total_hours', 0.0),
            'credits_per_hour': game_db_info.get('credits_per_hour', 1.0),
            'half_life_hours': game_db_info.get('half_life_hours'),
            'avg_hours': game_db_info.get('total_hours', 0.0) / game_db_info.get('unique_players', 1) if game_db_info.get('unique_players', 0) > 0 else 0.0,
            'release_date': game_db_info.get('release_date', '')
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
    logger.info(f"Fetching leaderboard for timeframe: {timeframe}")
    try:
        if timeframe == 'weekly':
            leaderboard_type = LeaderboardType.WEEKLY
        elif timeframe == 'monthly':
            leaderboard_type = LeaderboardType.MONTHLY
        elif timeframe == 'alltime':
            leaderboard_type = LeaderboardType.ALLTIME
        else:
            return jsonify({'error': 'Invalid timeframe specified'}), 400

        # Get the leaderboard data using the new timeframe calculation
        leaderboard_data = run_async(storage.get_leaderboard_by_timeframe(leaderboard_type))
        
        # Format the data for the frontend
        formatted_data = []
        if leaderboard_data:
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
                    logger.error(f"Error formatting user data for user {user_id}: {str(e)}", exc_info=True)

        return jsonify(formatted_data)

    except Exception as e:
        logger.error(f"Error getting leaderboard data: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get leaderboard data'}), 500

# Add endpoint to fetch recent bonuses
@app.route('/api/recent-bonuses')
def get_recent_bonuses():
    try:
        recent_bonuses_data = run_async(storage.get_recent_bonuses(limit=10))

        formatted_bonuses = []
        for bonus_data in recent_bonuses_data:
            # Ensure user_id is a string
            user_id = str(bonus_data['user_id'])
            discord_info = get_cached_discord_user_info(user_id)
            username = discord_info['username'] if discord_info else f'User{user_id}'
            avatar_url = discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id}.jpg'

            timestamp = bonus_data['timestamp']
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S') if isinstance(timestamp, datetime) else str(timestamp)

            formatted_bonuses.append({
                'id': bonus_data['id'],
                'user_id': user_id,  # Use string version
                'username': username,
                'avatar_url': avatar_url,
                'credits': bonus_data['credits'],
                'reason': bonus_data['reason'],
                'granted_by': str(bonus_data['granted_by']),  # Convert granted_by to string
                'timestamp': timestamp_str
            })

        return jsonify(formatted_bonuses)
    except Exception as e:
        return jsonify({'error': 'Failed to get recent bonuses'}), 500

# Add endpoint to fetch popular games data
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
                formatted_data.append({
                    'name': game_name,
                    'total_hours': total_hours,
                    'box_art_url': box_art_url if box_art_url else f"https://static-cdn.jtvnw.net/ttv-boxart/{game_name}-144x192.jpg"
                })

        # Sort by hours played and return all data (no limit)
        formatted_data.sort(key=lambda x: x['total_hours'], reverse=True)

        print(f"Returning formatted data: {formatted_data}")
        return jsonify(formatted_data)
    except Exception as e:
        print(f"Error getting popular games data: {str(e)}")
        print("Full traceback:")
        traceback.print_exc()
        return jsonify({'error': 'Failed to get popular games data'}), 500

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
            'total_hours': user_overall_stats.get('total_hours', 0),
            'games_played': user_overall_stats.get('games_played', 0),
            'total_sessions': user_overall_stats.get('total_sessions', 0),
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
        history = storage.get_user_gaming_history(user_id_str)
        end_db = time.time()
        
        if not history:
            return jsonify([])

        # Batch fetch game info
        game_names = list({entry.get('game') for entry in history if entry.get('game')})
        
        start_batch = time.time()
        game_info_map = storage.get_multiple_game_stats(game_names)
        end_batch = time.time()

        # Format the history data
        formatted_history = []
        start_loop = time.time()
        for entry in history:
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
                    'players': entry.get('players', 1),
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
        timeframe = request.args.get('timeframe', 'alltime')
        # Fetch recent sessions using the new timeframe logic
        recent_sessions_data = run_async(storage.get_recent_gaming_sessions(timeframe=timeframe))
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
                    'players': session.get('players', 1),
                    'timestamp': session['timestamp'].isoformat() if hasattr(session['timestamp'], 'isoformat') else str(session['timestamp']),
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
    #return redirect('https://discord.com/oauth2/authorize?client_id=1344451764530708571&response_type=code&redirect_uri=https%3A%2F%2Fgamercred.onrender.com%2Fcallback&scope=identify+guilds+email+guilds.join+connections')
    return redirect('https://discord.com/oauth2/authorize?client_id=1344451764530708571&response_type=code&redirect_uri=http://localhost:5000/callback&scope=identify+guilds+email+guilds.join+connections')

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
    resp = redirect(url_for('index') + '?just_logged_in=1')
    # Set cookies to expire in 30 days
    resp.set_cookie('discord_token', access_token, httponly=True, max_age=30*24*60*60)
    resp.set_cookie('user_id', user['id'], httponly=True, max_age=30*24*60*60)
    resp.set_cookie('username', user['username'], httponly=True, max_age=30*24*60*60)
    resp.set_cookie('avatar', user.get('avatar', ''), httponly=True, max_age=30*24*60*60)
    
    return resp

@app.route('/callback/desktop')
def callback_desktop():
    """Handle the OAuth2 callback for desktop app"""
    if request.values.get('error'):
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #23232b; color: white;">
            <h2 style="color: #ff6fae;">❌ Login Failed</h2>
            <p>Error: {request.values['error']}</p>
            <p>You can close this window and try again.</p>
        </body>
        </html>
        """
    
    code = request.values.get('code')
    if not code:
        return "No code provided", 400

    # Exchange the code for an access token
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'https://gamercred.onrender.com/callback/desktop'
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(DISCORD_TOKEN_URL, data=data, headers=headers)
    if response.status_code != 200:
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #23232b; color: white;">
            <h2 style="color: #ff6fae;">❌ Login Failed</h2>
            <p>Error getting token: {response.text}</p>
        </body>
        </html>
        """
    
    token_data = response.json()
    access_token = token_data['access_token']
    
    # Get user info
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    user_response = requests.get(f'{DISCORD_API_URL}/users/@me', headers=headers)
    if user_response.status_code != 200:
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #23232b; color: white;">
            <h2 style="color: #ff6fae;">❌ Login Failed</h2>
            <p>Error getting user info: {user_response.text}</p>
        </body>
        </html>
        """
    
    user = user_response.json()
    
    # Create response with success message
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #23232b; color: white;">
        <h2 style="color: #ff6fae;">✅ Login Successful!</h2>
        <p>Welcome, {user['username']}!</p>
        <p>You have been logged in successfully.</p>
        <p>You can now return to the desktop app and click "Check Login Status".</p>
        <script>
            setTimeout(function() {{
                window.close();
            }}, 3000);
        </script>
    </body>
    </html>
    """
    
    resp = make_response(html_content)
    
    # Set a simple session cookie that indicates desktop login
    resp.set_cookie('desktop_logged_in', 'true', httponly=False, max_age=3600, path='/', samesite='Lax')
    resp.set_cookie('desktop_user_id', user['id'], httponly=False, max_age=3600, path='/', samesite='Lax')
    resp.set_cookie('desktop_username', user['username'], httponly=False, max_age=3600, path='/', samesite='Lax')
    
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

@app.route('/api/user/desktop')
def get_user_desktop():
    """Get the current user's information for desktop app (uses Authorization header)"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'No valid authorization header'}), 401
    
    access_token = auth_header.split(' ')[1]
    
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

@app.route('/api/user/desktop-status')
def get_desktop_user_status():
    """Get user status for desktop app using desktop-specific cookies"""
    desktop_token = request.cookies.get('desktop_token')
    desktop_user_id = request.cookies.get('desktop_user_id')
    desktop_username = request.cookies.get('desktop_username')
    
    if not all([desktop_token, desktop_user_id, desktop_username]):
        return jsonify({'error': 'Not logged in via desktop'}), 401
    
    # Verify the token is still valid
    headers = {
        'Authorization': f'Bearer {desktop_token}'
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

@app.route('/api/user/desktop-token')
def get_desktop_user_by_token():
    """Get user status for desktop app using token from query parameter"""
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'No token provided'}), 401
    
    # Verify the token is still valid
    headers = {
        'Authorization': f'Bearer {token}'
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

@app.route('/api/user/desktop-check')
def check_desktop_login():
    """Simple endpoint to check if user is logged in via desktop flow"""
    desktop_logged_in = request.cookies.get('desktop_logged_in')
    desktop_user_id = request.cookies.get('desktop_user_id')
    desktop_username = request.cookies.get('desktop_username')
    
    if not all([desktop_logged_in, desktop_user_id, desktop_username]):
        return jsonify({'logged_in': False, 'error': 'Not logged in via desktop'}), 401
    
    return jsonify({
        'logged_in': True,
        'user': {
            'id': desktop_user_id,
            'username': desktop_username,
            'avatar': request.cookies.get('desktop_avatar', ''),
            'email': ''  # We don't store email in cookies for security
        }
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
        players = data.get('players', 1)

        if not all([user_id, game_name, hours]):
            logger.warning(f"Missing required fields for game logging. Received: {data}")
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            hours = float(hours)
            # Handle players parameter - convert string "5+" to integer 5
            if isinstance(players, str) and players == "5+":
                players = 5
            else:
                try:
                    players = int(players)
                except (ValueError, TypeError):
                    players = 1
        except ValueError:
            logger.warning(f"Invalid hours value: hours={hours}")
            return jsonify({'error': 'Hours must be a number'}), 400

        logger.info(f"Logging game session for user {user_id}: {game_name} - {hours} hours, {players} players")
        
        try:
            storage.log_game_session(user_id, game_name, hours, players)
            return jsonify({'message': 'Game session logged successfully'}), 200
        except Exception as e:
            logger.error(f"Error in storage.log_game_session: {str(e)}", exc_info=True)
            # Custom error for missing game
            if 'Game does not exist in the database' in str(e):
                return jsonify({'error': 'That game does not exist. Please add it or check the name.'}), 400
            return jsonify({'error': f'Failed to log game session: {str(e)}'}), 500

    except Exception as e:
        error_msg = f"Error logging game session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/rate-game', methods=['POST'])
def rate_game():
    """Rate a game (set credits per hour)"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        user_id = data.get('user_id')
        game_name = data.get('game_name')
        rating = data.get('rating')  # This is actually credits per hour, not a rating

        if not all([user_id, game_name, rating]):
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            rating = float(rating)
        except ValueError:
            return jsonify({'error': 'Rating must be a number'}), 400

        if rating < 0.1:
            return jsonify({'error': 'Rating must be at least 0.1'}), 400

        logger.info(f"Setting rate for game {game_name} to {rating} credits/hour by user {user_id}")
        
        try:
            # Use the storage method to set the game rate
            success = run_async(storage.set_game_credits_per_hour(game_name, rating, user_id))
            if success:
                return jsonify({'message': f'Successfully set rate for {game_name} to {rating} credits/hour'}), 200
            else:
                return jsonify({'error': f'Failed to set rate for {game_name}'}), 500
        except Exception as e:
            logger.error(f"Error setting game rate: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to set game rate: {str(e)}'}), 500

    except Exception as e:
        error_msg = f"Error rating game: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

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

@app.route('/api/user-game-summaries/<user_identifier>')
def get_user_game_summaries_endpoint(user_identifier):
    """Get detailed game summaries for a user"""
    try:
        print(f"Getting game summaries for user: {user_identifier}")
        
        # Get user's game summaries
        game_summaries = storage.get_user_game_summaries(user_identifier)
        
        print(f"Raw game summaries: {game_summaries}")
        
        if not game_summaries:
            return jsonify([])

        # Format the response with additional data
        formatted_summaries = []
        for summary in game_summaries:
            try:
                # Get game details to include box art and other info
                game_details = storage.get_game_stats(summary['game'])
                
                formatted_summary = {
                    'game_name': summary['game'],
                    'total_hours': summary['total_hours'],
                    'total_credits': summary['total_credits'],
                    'total_sessions': summary['sessions'],
                    'first_played': summary['first_played'],
                    'last_played': summary['last_played'],
                    'box_art_url': game_details.get('box_art_url') if game_details else None,
                    'backloggd_url': game_details.get('backloggd_url') if game_details else None,
                    'credits_per_hour': game_details.get('credits_per_hour') if game_details else 1.0
                }
                formatted_summaries.append(formatted_summary)
            except Exception as e:
                print(f"Error formatting summary for game {summary.get('game', 'unknown')}: {str(e)}")
                continue

        print(f"Formatted summaries: {formatted_summaries}")
        return jsonify(formatted_summaries)

    except Exception as e:
        print(f"Error getting user game summaries: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to get user game summaries'}), 500

# Add endpoint to fetch pre-aggregated daily credits for the heatmap
@app.route('/api/user-daily-credits/<user_identifier>')
def get_user_daily_credits(user_identifier):
    try:
        user_id_str = str(user_identifier)
        # Use a new or existing storage method to get daily credits
        daily_credits = storage.get_user_daily_credits(user_id_str)
        return jsonify(daily_credits)
    except Exception as e:
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/set-game-rate', methods=['POST'])
def set_game_rate():
    """Set game rate, half-life, and box art"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        user_id = data.get('user_id')
        game_name = data.get('game_name')
        cph = data.get('cph')
        half_life = data.get('half_life', 0)
        box_art_url = data.get('box_art_url', '')

        if not all([user_id, game_name, cph]):
            return jsonify({'error': 'Missing required fields'}), 400

        try:
            cph = float(cph)
            half_life = float(half_life) if half_life else 0
        except ValueError:
            return jsonify({'error': 'Invalid numeric values'}), 400

        if cph < 0.1:
            return jsonify({'error': 'CPH must be at least 0.1'}), 400

        logger.info(f"Setting rate for game {game_name} to {cph} CPH, {half_life}h half-life by user {user_id}")
        
        try:
            # Set CPH
            cph_success = run_async(storage.set_game_credits_per_hour(game_name, cph, user_id))
            if not cph_success:
                return jsonify({'error': f'Failed to set CPH for {game_name}'}), 500

            # Set half-life
            half_life_success = run_async(storage.set_game_half_life(game_name, half_life, user_id))
            if not half_life_success:
                return jsonify({'error': f'Failed to set half-life for {game_name}'}), 500

            # Set box art if provided
            if box_art_url:
                box_art_success = storage.set_game_box_art(game_name, box_art_url, user_id)
                if not box_art_success:
                    logger.warning(f"Failed to set box art for {game_name}")

            return jsonify({'message': f'Successfully updated {game_name}'}), 200

        except Exception as e:
            logger.error(f"Error setting game rate: {str(e)}", exc_info=True)
            return jsonify({'error': f'Failed to set game rate: {str(e)}'}), 500

    except Exception as e:
        error_msg = f"Error setting game rate: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/recent-rate-changes')
def get_recent_rate_changes():
    """Get recent rate changes"""
    try:
        changes = storage.get_recent_rate_changes(limit=10)
        
        # Fetch Discord usernames for each change
        for change in changes:
            user_id = change.get('user_id')
            if user_id:
                discord_info = get_cached_discord_user_info(user_id)
                if discord_info:
                    change['user_name'] = discord_info.get('username', f'User{user_id}')
                else:
                    change['user_name'] = f'User{user_id}'
            else:
                change['user_name'] = 'Unknown'
        
        return jsonify(changes)
    except Exception as e:
        logger.error(f"Error getting recent rate changes: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to get recent changes'}), 500

# --- GAME REVIEWS ---
@app.route('/api/game/review', methods=['POST'])
def submit_game_review():
    access_token = request.cookies.get('discord_token')
    user_id = request.cookies.get('user_id')
    if not access_token or not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    game_name = data.get('game_name')
    review_text = data.get('review_text', '').strip()
    if not game_name or not review_text:
        return jsonify({'error': 'Missing game name or review text'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        # Upsert review
        review = session.query(GameReview).filter_by(user_id=user_id, game_id=game.id).first()
        if review:
            review.review_text = review_text
            review.timestamp = datetime.utcnow()
        else:
            review = GameReview(user_id=user_id, game_id=game.id, review_text=review_text, timestamp=datetime.utcnow())
            session.add(review)
        session.commit()
        return jsonify({'message': 'Review submitted successfully'})

@app.route('/api/game/reviews')
def get_game_reviews():
    game_name = request.args.get('name')
    if not game_name:
        return jsonify({'error': 'Game name parameter missing'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        reviews = session.query(GameReview).filter_by(game_id=game.id).order_by(GameReview.timestamp.desc()).all()
        result = []
        for r in reviews:
            user = session.query(UserStats).filter_by(user_id=r.user_id).first()
            
            # Get user's rating for this game
            user_rating = session.query(GameRating).filter_by(user_id=r.user_id, game_id=game.id).first()
            rating = user_rating.rating if user_rating else None
            
            # Get user's total hours for this game
            total_hours_result = session.execute(text("""
                SELECT COALESCE(SUM(hours), 0) as total_hours
                FROM gaming_sessions
                WHERE user_id = :user_id AND game_id = :game_id
            """), {"user_id": r.user_id, "game_id": game.id}).first()
            total_hours = float(total_hours_result.total_hours) if total_hours_result else 0.0
            
            # Get user's hours at the time of review (sum of sessions before review timestamp)
            hours_at_review_result = session.execute(text("""
                SELECT COALESCE(SUM(hours), 0) as hours_at_review
                FROM gaming_sessions
                WHERE user_id = :user_id AND game_id = :game_id AND timestamp <= :review_timestamp
            """), {"user_id": r.user_id, "game_id": game.id, "review_timestamp": r.timestamp}).first()
            hours_at_review = float(hours_at_review_result.hours_at_review) if hours_at_review_result else 0.0
            
            result.append({
                'user_id': r.user_id,
                'username': user.username if user else f'User{r.user_id}',
                'avatar_url': user.avatar_url if user else '',
                'review_text': r.review_text,
                'timestamp': r.timestamp.isoformat(),
                'rating': rating,
                'hours_at_review': hours_at_review,
                'total_hours': total_hours
            })
        return jsonify(result)

# --- GAME RATINGS ---
@app.route('/api/game/rating', methods=['POST'])
def submit_game_rating():
    access_token = request.cookies.get('discord_token')
    user_id = request.cookies.get('user_id')
    if not access_token or not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    game_name = data.get('game_name')
    rating = data.get('rating')
    if not game_name or rating is None:
        return jsonify({'error': 'Missing game name or rating'}), 400
    try:
        rating = float(rating)
        if rating < 0.5 or rating > 5.0:
            raise ValueError
    except Exception:
        return jsonify({'error': 'Rating must be a number between 0.5 and 5.0'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        # Upsert rating
        gr = session.query(GameRating).filter_by(user_id=user_id, game_id=game.id).first()
        if gr:
            gr.rating = rating
            gr.timestamp = datetime.utcnow()
        else:
            gr = GameRating(user_id=user_id, game_id=game.id, rating=rating, timestamp=datetime.utcnow())
            session.add(gr)
        session.commit()
        return jsonify({'message': 'Rating submitted successfully'})

@app.route('/api/game/ratings')
def get_game_ratings():
    game_name = request.args.get('name')
    user_id = request.cookies.get('user_id')
    if not game_name:
        return jsonify({'error': 'Game name parameter missing'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        ratings = session.query(GameRating).filter_by(game_id=game.id).all()
        avg_rating = round(sum(r.rating for r in ratings) / len(ratings), 2) if ratings else None
        user_rating = None
        if user_id:
            ur = session.query(GameRating).filter_by(game_id=game.id, user_id=user_id).first()
            if ur:
                user_rating = ur.rating
        return jsonify({
            'average': avg_rating,
            'count': len(ratings),
            'user_rating': user_rating
        })

# --- GAME COMPLETION ---
@app.route('/api/game/complete', methods=['POST'])
def complete_game():
    access_token = request.cookies.get('discord_token')
    user_id = request.cookies.get('user_id')
    if not access_token or not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    game_name = data.get('game_name')
    if not game_name:
        return jsonify({'error': 'Missing game name'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        # Check if already completed
        existing = session.query(GameCompletion).filter_by(user_id=user_id, game_id=game.id).first()
        if existing:
            return jsonify({'message': 'Already marked as completed', 'already_completed': True}), 200
        # Mark as completed
        completion = GameCompletion(user_id=user_id, game_id=game.id, completed_at=datetime.utcnow(), credits_awarded=1000.0)
        session.add(completion)
        # Award credits
        user = session.query(UserStats).filter_by(user_id=user_id).first()
        if user:
            user.total_credits = (user.total_credits or 0) + 1000.0
        session.commit()
        return jsonify({'message': 'Game marked as completed and 1,000 credits awarded', 'already_completed': False})

@app.route('/api/game/uncomplete', methods=['POST'])
def uncomplete_game():
    access_token = request.cookies.get('discord_token')
    user_id = request.cookies.get('user_id')
    if not access_token or not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    game_name = data.get('game_name')
    if not game_name:
        return jsonify({'error': 'Missing game name'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        completion = session.query(GameCompletion).filter_by(user_id=user_id, game_id=game.id).first()
        if not completion:
            return jsonify({'error': 'Game not marked as completed'}), 400
        # Remove completion and deduct credits
        session.delete(completion)
        user = session.query(UserStats).filter_by(user_id=user_id).first()
        if user and completion.credits_awarded:
            user.total_credits = max((user.total_credits or 0) - completion.credits_awarded, 0)
        session.commit()
        # Get new completion count
        completions = session.query(GameCompletion).filter_by(game_id=game.id).all()
        return jsonify({'message': 'Game completion undone and credits removed', 'completion_count': len(completions)})

@app.route('/api/game/completions')
def get_game_completions():
    game_name = request.args.get('name')
    user_id = request.cookies.get('user_id')
    if not game_name:
        return jsonify({'error': 'Game name parameter missing'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        completions = session.query(GameCompletion).filter_by(game_id=game.id).all()
        completed_user_ids = [c.user_id for c in completions]
        user_completed = user_id and int(user_id) in completed_user_ids
        return jsonify({
            'count': len(completions),
            'user_completed': user_completed
        })

# --- GAME SCREENSHOTS ---
import uuid
import base64
@app.route('/api/game/screenshot', methods=['POST'])
def upload_game_screenshot():
    access_token = request.cookies.get('discord_token')
    user_id = request.cookies.get('user_id')
    if not access_token or not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Check if it's a file upload or base64 data
    if 'screenshot' in request.files:
        # Handle file upload (for backward compatibility)
        file = request.files['screenshot']
        if file.filename == '':
            return jsonify({'error': 'No screenshot file provided'}), 400
        
        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_extension = file.filename.lower().split('.')[-1]
        if file_extension not in allowed_extensions:
            return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, or WebP'}), 400
        
        # Check file size (100MB limit for screenshots)
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)
        if file_size > 100 * 1024 * 1024:
            return jsonify({'error': 'File too large. Maximum size is 100MB'}), 400
        
        # Read file data and encode as base64
        file_data = file.read()
        image_data = base64.b64encode(file_data).decode('utf-8')
        filename = file.filename
        mime_type = file.content_type or f'image/{file_extension}'
        
    elif request.is_json:
        # Handle base64 data from JSON
        data = request.json
        image_data = data.get('image_data')
        filename = data.get('filename', 'screenshot.png')
        mime_type = data.get('mime_type', 'image/png')
        caption = data.get('caption', '')
        game_name = data.get('game_name')
        
        if not image_data or not game_name:
            return jsonify({'error': 'Missing image_data or game_name'}), 400
        
        # Validate base64 data
        try:
            # Check if it's valid base64
            decoded_data = base64.b64decode(image_data)
            if len(decoded_data) > 100 * 1024 * 1024:  # 100MB limit
                return jsonify({'error': 'Image too large. Maximum size is 100MB'}), 400
        except Exception:
            return jsonify({'error': 'Invalid base64 data'}), 400
    else:
        return jsonify({'error': 'No screenshot data provided'}), 400
    
    # Get caption and game name from form data if not from JSON
    if not request.is_json:
        caption = request.form.get('caption', '')
        game_name = request.form.get('game_name')
        if not game_name:
            return jsonify({'error': 'Missing game name'}), 400
    
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        
        screenshot = GameScreenshot(
            user_id=user_id, 
            game_id=game.id, 
            image_data=image_data,
            image_filename=filename,
            image_mime_type=mime_type,
            caption=caption, 
            uploaded_at=datetime.utcnow()
        )
        session.add(screenshot)
        session.commit()
        
        return jsonify({
            'message': 'Screenshot uploaded successfully', 
            'screenshot_id': screenshot.id
        })

@app.route('/api/game/screenshots')
def get_game_screenshots():
    game_name = request.args.get('name')
    if not game_name:
        return jsonify({'error': 'Game name parameter missing'}), 400
    with storage.Session() as session:
        game = session.query(Game).filter_by(name=game_name).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404
        screenshots = session.query(GameScreenshot).filter_by(game_id=game.id).order_by(GameScreenshot.uploaded_at.desc()).all()
        result = []
        for s in screenshots:
            user = session.query(UserStats).filter_by(user_id=s.user_id).first()
            result.append({
                'id': s.id,
                'user_id': s.user_id,
                'username': user.username if user else f'User{s.user_id}',
                'avatar_url': user.avatar_url if user else '',
                'image_url': f'/api/game/screenshot/{s.id}',  # URL to serve the image
                'caption': s.caption,
                'uploaded_at': s.uploaded_at.isoformat()
            })
        return jsonify(result)

@app.route('/api/game/screenshot/<int:screenshot_id>')
def serve_screenshot(screenshot_id):
    """Serve a screenshot image from the database"""
    with storage.Session() as session:
        screenshot = session.query(GameScreenshot).filter_by(id=screenshot_id).first()
        if not screenshot:
            return jsonify({'error': 'Screenshot not found'}), 404
        
        try:
            # Decode base64 data
            image_data = base64.b64decode(screenshot.image_data)
            
            # Set response headers
            response = make_response(image_data)
            response.headers['Content-Type'] = screenshot.image_mime_type or 'image/png'
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year cache
            response.headers['ETag'] = f'"screenshot-{screenshot_id}-{screenshot.uploaded_at.timestamp()}"'
            
            return response
        except Exception as e:
            print(f"Error serving screenshot {screenshot_id}: {e}")
            return jsonify({'error': 'Error serving image'}), 500

@app.route('/preferences.html')
def preferences():
    return app.send_static_file('pages/preferences.html')

@app.route('/api/preferences', methods=['GET'])
def get_user_preferences():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    with storage.Session() as session:
        prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
        if prefs:
                            return jsonify({
                    'theme': prefs.theme,
                    'background_image_url': prefs.background_image_url,
                    'background_video_url': prefs.background_video_url,
                    'background_image_data': prefs.background_image_data,
                    'background_video_data': prefs.background_video_data,
                    'background_image_filename': prefs.background_image_filename,
                    'background_video_filename': prefs.background_video_filename,
                    'background_image_mime_type': prefs.background_image_mime_type,
                    'background_video_mime_type': prefs.background_video_mime_type,
                    'background_opacity': prefs.background_opacity,
                    'background_type': prefs.background_type or 'image',
                    'user_id': user_id
                })
        else:
            return jsonify({
                'theme': None,
                'background_image_url': None,
                'background_video_url': None,
                'background_opacity': 0.3,
                'background_type': 'image'
            })

@app.route('/api/preferences', methods=['POST'])
def set_user_preferences():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    theme = data.get('theme')
    background_image_url = data.get('background_image_url')
    background_video_url = data.get('background_video_url')
    background_opacity = data.get('background_opacity', 0.3)
    background_type = data.get('background_type', 'image')
    
    if not theme:
        return jsonify({'error': 'Missing theme'}), 400
    
    with storage.Session() as session:
        prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
        if prefs:
            prefs.theme = theme
            prefs.background_opacity = background_opacity
            prefs.background_type = background_type
            
            # Only update URL fields if they're external URLs (not internal API endpoints)
            if background_image_url and not background_image_url.startswith('/api/preferences/background/'):
                prefs.background_image_url = background_image_url
                # Clear database-stored image data if switching to external URL
                prefs.background_image_data = None
                prefs.background_image_filename = None
                prefs.background_image_mime_type = None
            elif background_image_url is None:
                # Clear external URL if setting to None
                prefs.background_image_url = None
                
            if background_video_url and not background_video_url.startswith('/api/preferences/background/'):
                prefs.background_video_url = background_video_url
                # Clear database-stored video data if switching to external URL
                prefs.background_video_data = None
                prefs.background_video_filename = None
                prefs.background_video_mime_type = None
            elif background_video_url is None:
                # Clear external URL if setting to None
                prefs.background_video_url = None
        else:
            # For new preferences, only store external URLs
            image_url = background_image_url if background_image_url and not background_image_url.startswith('/api/preferences/background/') else None
            video_url = background_video_url if background_video_url and not background_video_url.startswith('/api/preferences/background/') else None
            
            prefs = UserPreferences(
                user_id=user_id, 
                theme=theme,
                background_image_url=image_url,
                background_video_url=video_url,
                background_opacity=background_opacity,
                background_type=background_type
            )
            session.add(prefs)
        session.commit()
        return jsonify({
            'message': 'Preferences updated', 
            'theme': theme,
            'background_image_url': prefs.background_image_url,
            'background_video_url': prefs.background_video_url,
            'background_opacity': background_opacity,
            'background_type': background_type
        })

@app.route('/api/preferences/upload-background', methods=['POST'])
def upload_background_image():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not logged in'}), 401
    
    if 'background_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['background_file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file type
    allowed_image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    allowed_video_extensions = {'mp4', 'webm', 'ogg', 'mov'}
    file_extension = file.filename.lower().split('.')[-1]
    
    if file_extension in allowed_image_extensions:
        file_type = 'image'
        mime_type = file.content_type or f'image/{file_extension}'
        max_size = None  # No size limit for images
    elif file_extension in allowed_video_extensions:
        file_type = 'video'
        mime_type = file.content_type or f'video/{file_extension}'
        max_size = 100 * 1024 * 1024  # 100MB for videos
    else:
        return jsonify({'error': 'Invalid file type. Please upload PNG, JPG, JPEG, GIF, WebP, MP4, WebM, OGG, or MOV'}), 400
    
    try:
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if max_size and file_size > max_size:
            size_mb = max_size / (1024 * 1024)
            return jsonify({'error': f'File too large. Maximum size is {size_mb}MB'}), 400
        
        # For videos, check duration (approximate based on file size)
        if file_type == 'video':
            # Rough estimate: 1MB per second for compressed video
            estimated_duration = file_size / (1024 * 1024)  # seconds
            if estimated_duration > 15:  # Allow some buffer
                return jsonify({'error': 'Video too long. Maximum duration is 10 seconds'}), 400
        
        # Read file data and encode as base64
        file_data = file.read()
        import base64
        encoded_data = base64.b64encode(file_data).decode('utf-8')
        
        # Check encoded size (base64 increases size by ~33%)
        encoded_size = len(encoded_data)
        if encoded_size > 100 * 1024 * 1024:  # 100MB limit for database storage
            return jsonify({'error': 'File too large for database storage. Please use a smaller file or external URL'}), 400
        
        # Update user preferences with the file data stored in database
        with storage.Session() as session:
            prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
            if prefs:
                if file_type == 'image':
                    prefs.background_image_data = encoded_data
                    prefs.background_image_filename = file.filename
                    prefs.background_image_mime_type = mime_type
                    prefs.background_image_url = None  # Clear URL if storing in DB
                    prefs.background_type = 'image'
                else:
                    prefs.background_video_data = encoded_data
                    prefs.background_video_filename = file.filename
                    prefs.background_video_mime_type = mime_type
                    prefs.background_video_url = None  # Clear URL if storing in DB
                    prefs.background_type = 'video'
            else:
                prefs = UserPreferences(
                    user_id=user_id,
                    theme='dark',  # Default theme
                    background_image_data=encoded_data if file_type == 'image' else None,
                    background_video_data=encoded_data if file_type == 'video' else None,
                    background_image_filename=file.filename if file_type == 'image' else None,
                    background_video_filename=file.filename if file_type == 'video' else None,
                    background_image_mime_type=mime_type if file_type == 'image' else None,
                    background_video_mime_type=mime_type if file_type == 'video' else None,
                    background_opacity=0.3,
                    background_type=file_type
                )
                session.add(prefs)
            
            try:
                session.commit()
                # Clear cache for this user's background files
                cache_key_image = f"{user_id}_image"
                cache_key_video = f"{user_id}_video"
                if cache_key_image in background_file_cache:
                    del background_file_cache[cache_key_image]
                if cache_key_video in background_file_cache:
                    del background_file_cache[cache_key_video]
            except Exception as db_error:
                session.rollback()
                print(f"Database error: {str(db_error)}")
                if "SSL connection has been closed" in str(db_error):
                    return jsonify({'error': 'File too large for database storage. Please use a smaller file or external URL'}), 400
                else:
                    raise db_error
        
        return jsonify({
            'message': f'Background {file_type} uploaded successfully',
            'file_url': f'/api/preferences/background/{user_id}/{file_type}?t={int(time.time())}',
            'file_type': file_type
        })
    except Exception as e:
        print(f"Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to upload {file_type}: {str(e)}'}), 500

@app.route('/api/preferences/background/<user_id>/<file_type>')
def serve_background_file(user_id, file_type):
    """Serve background files stored in the database with caching."""
    try:
        # Check cache first
        cache_key = f"{user_id}_{file_type}"
        current_time = time.time()
        cache_expiry = 3600  # 1 hour
        
        if (cache_key in background_file_cache and 
            current_time - background_file_cache_timestamps.get(cache_key, 0) < cache_expiry):
            cached_data = background_file_cache[cache_key]
            from flask import Response
            response = Response(cached_data['file_data'], mimetype=cached_data['mime_type'])
            response.headers['Content-Disposition'] = f'inline; filename="{cached_data["filename"]}"'
            response.headers['Cache-Control'] = 'public, max-age=31536000'
            response.headers['ETag'] = cached_data['etag']
            return response
        
        # If not in cache, get from database
        with storage.Session() as session:
            prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
            if not prefs:
                return jsonify({'error': 'User preferences not found'}), 404
            
            if file_type == 'image' and prefs.background_image_data:
                import base64
                file_data = base64.b64decode(prefs.background_image_data)
                mime_type = prefs.background_image_mime_type or 'image/jpeg'
                filename = prefs.background_image_filename or 'background.jpg'
            elif file_type == 'video' and prefs.background_video_data:
                import base64
                file_data = base64.b64decode(prefs.background_video_data)
                mime_type = prefs.background_video_mime_type or 'video/mp4'
                filename = prefs.background_video_filename or 'background.mp4'
            else:
                return jsonify({'error': 'File not found'}), 404
            
            # Cache the result
            etag = f'"{user_id}_{file_type}_{hash(file_data) % 1000000}"'
            background_file_cache[cache_key] = {
                'file_data': file_data,
                'mime_type': mime_type,
                'filename': filename,
                'etag': etag
            }
            background_file_cache_timestamps[cache_key] = current_time
            
            from flask import Response
            response = Response(file_data, mimetype=mime_type)
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            response.headers['Cache-Control'] = 'public, max-age=31536000'
            response.headers['ETag'] = etag
            return response
            
    except Exception as e:
        print(f"Error serving background file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 