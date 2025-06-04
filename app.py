from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import sys # Import the sys module
import re # Import re for HTML cleaning
from dotenv import load_dotenv
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

# Load environment variables
load_dotenv()

# Initialize Flask app with correct static folder path
app = Flask(__name__, 
            static_folder='public',
            static_url_path='',
            template_folder='public')

# Enable CORS for your domain
CORS(app, resources={r"/api/*": {"origins": ["https://www.gamercred.co", "http://localhost:5000"]}})

# Add debug logging for database URL
database_url = os.getenv('DATABASE_URL')
print(f"DEBUG: Database URL: {database_url}")

storage = GameStorage() # Instantiate GameStorage
print("DEBUG: GameStorage initialized")

# Get RAWG API key from environment variable
RAWG_API_KEY = os.getenv('RAWG_API_KEY')
RAWG_API_URL = os.getenv('RAWG_API_URL', 'https://api.rawg.io/api')

if not RAWG_API_KEY:
    print("Warning: RAWG_API_KEY environment variable not set. Game details may not load.")

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
                            # Check for presence of Premium Discord badge
                            # if user_data.get('premium_type', 0) > 0:
                            #     # User has Nitro or Nitro Classic, use different avatar URL if available
                            #     # Discord's documentation isn't fully clear on a separate Nitro avatar URL for bots
                            #     # Keeping this commented for now, but might be needed later
                            #     pass
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

# Helper function to run async functions
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

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

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/game.html')
def game():
    return send_from_directory(app.static_folder, 'game.html')

@app.route('/user.html')
def user():
    return send_from_directory(app.static_folder, 'user.html')

@app.route('/api/game')
def get_game():
    print(f"DEBUG: /api/game endpoint hit with args: {request.args}") # Debug print
    try:
        game_name = request.args.get('name')
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        # Get game info from the database
        game_db_info = storage.get_game_stats(game_name)
        print(f"DEBUG: Game DB info: {game_db_info}") # Debug print

        if not game_db_info:
            return jsonify({'error': 'Game not found in database'}), 404

        # Use the correct game name from the database for the API call
        correct_game_name = game_db_info.get('name', game_name)
        cover_image_url = game_db_info.get('cover_image_url')
        backloggd_url = game_db_info.get('backloggd_url')
        description = 'No description available.'

        # Fetch description and potentially updated cover art from RAWG if rawg_id exists
        rawg_id = game_db_info.get('rawg_id')
        if rawg_id:
            print(f"DEBUG: Fetching RAWG details for game with RAWG ID: {rawg_id}")
            rawg_details = run_async(storage.fetch_game_details_from_rawg(correct_game_name))
            if rawg_details:
                description = rawg_details.get('description', description)
                # Optionally update cover_image_url if RAWG returned a better one
                if rawg_details.get('box_art_url'):
                    cover_image_url = rawg_details.get('box_art_url')

        print(f"DEBUG: Description after RAWG fetch: {description}") # Debug print

        # Combine database info with API info
        final_game_data = {
            'name': correct_game_name,
            'cover_image_url': cover_image_url,
            'description': description,  # Make sure description is included
            'backloggd_url': backloggd_url,
            'total_players': game_db_info.get('unique_players', 0),
            'total_hours': game_db_info.get('total_hours', 0.0),
            'credits_per_hour': game_db_info.get('credits_per_hour', 1.0),
            'avg_hours': game_db_info.get('total_hours', 0.0) / game_db_info.get('unique_players', 1) if game_db_info.get('unique_players', 0) > 0 else 0.0,
        }

        print(f"DEBUG: Returning final game data: {final_game_data}") # Debug print
        return jsonify(final_game_data)

    except Exception as e:
        print(f"Error processing /api/game: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/game/players')
def get_game_players():
    try:
        game_name = request.args.get('name')
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        print(f"DEBUG: Getting players for game: {game_name}") # Debug print
        players_data = storage.get_recent_players_for_game(game_name, timeframe='weekly', limit=6)
        print(f"DEBUG: Players data: {players_data}") # Debug print

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
        print(f"Error processing /api/game/players: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/game/activity')
def get_game_activity():
    try:
        game_name = request.args.get('name')
        if not game_name:
            return jsonify({'error': 'Game name parameter missing'}), 400

        print(f"DEBUG: Getting activity for game: {game_name}") # Debug print
        activity_data = storage.get_recent_activity_for_game(game_name, limit=10)
        print(f"DEBUG: Activity data: {activity_data}") # Debug print

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
        print(f"Error processing /api/game/activity: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch leaderboard data
@app.route('/api/leaderboard')
def get_leaderboard():
    try:
        timeframe = request.args.get('timeframe', 'weekly')
        print(f"DEBUG: Fetching leaderboard for timeframe: {timeframe}")
        
        # Convert timeframe to LeaderboardType
        if timeframe == 'weekly':
            leaderboard_type = LeaderboardType.WEEKLY
        elif timeframe == 'monthly':
            leaderboard_type = LeaderboardType.MONTHLY
        else:
            return jsonify({'error': 'Invalid timeframe'}), 400

        # Get leaderboard data
        leaderboard_data = storage.get_leaderboard_by_timeframe(leaderboard_type)
        return jsonify(leaderboard_data)
    except Exception as e:
        print(f"Error in get_leaderboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add endpoint to fetch recent bonuses
@app.route('/api/recent-bonuses')
def get_recent_bonuses_endpoint():
    try:
        print("DEBUG: Fetching recent bonuses")
        bonuses_data = storage.get_recent_bonuses()
        return jsonify(bonuses_data)
    except Exception as e:
        print(f"Error in get_recent_bonuses_endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add endpoint to fetch popular games data
@app.route('/api/popular-games')
def get_popular_games():
    try:
        timeframe = request.args.get('timeframe', 'weekly')
        print(f"DEBUG: Fetching popular games for timeframe: {timeframe}")
        
        # Get popular games data
        games_data = storage.get_total_game_hours_by_timeframe(timeframe)
        return jsonify(games_data)
    except Exception as e:
        print(f"Error in get_popular_games: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

# Add endpoint to fetch user gaming history (recent activity)
@app.route('/api/user-stats/<user_identifier>/history')
def get_user_history_endpoint(user_identifier):
    try:
        print(f"DEBUG: /api/user-stats/{user_identifier}/history endpoint hit")
        print(f"DEBUG: user_identifier type: {type(user_identifier)}")
        start_total = time.time()
        
        # Keep as string to preserve precision
        user_id_str = str(user_identifier)
        print(f"DEBUG: Processing history for user_id: {user_id_str}")
        
        # Profile DB query
        start_db = time.time()
        user_history = storage.get_user_gaming_history(user_id_str, limit=5) # Limit to 5 for recent activity
        end_db = time.time()
        print(f"DEBUG: DB query took {end_db - start_db:.3f} seconds")
        print(f"DEBUG: Retrieved {len(user_history)} history entries")
        print(f"DEBUG: Raw user_history data: {user_history}")

        if not user_history:
            print(f"DEBUG: No history found for user {user_id_str}")
            return jsonify([])

        # Batch fetch game info
        game_names = list({entry.get('game') for entry in user_history if entry.get('game')})
        print(f"DEBUG: Fetching info for games: {game_names}")
        
        start_batch = time.time()
        game_info_map = storage.get_multiple_game_stats(game_names)
        end_batch = time.time()
        print(f"DEBUG: Batch game info fetch took {end_batch - start_batch:.3f} seconds for {len(game_names)} games")
        print(f"DEBUG: Game info map: {game_info_map}")

        # Format the history data
        formatted_history = []
        start_loop = time.time()
        for entry in user_history:
            try:
                game_name = entry.get('game')
                game_info = game_info_map.get(game_name, {})
                box_art_url = game_info.get('cover_image_url')
                
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
                print(f"DEBUG: Formatted entry: {formatted_entry}")
            except Exception as e:
                print(f"Error formatting history entry: {e}")
                print(f"Problematic entry data: {entry}")
                continue

        end_loop = time.time()
        print(f"DEBUG: Per-entry processing took {end_loop - start_loop:.3f} seconds for {len(user_history)} entries")
        print(f"DEBUG: Total endpoint time: {end_loop - start_total:.3f} seconds")
        print(f"DEBUG: Returning {len(formatted_history)} formatted entries")
        print(f"DEBUG: Final formatted history: {formatted_history}")
        
        return jsonify(formatted_history)
        
    except Exception as e:
        print(f"Error processing /api/user-stats/{user_identifier}/history: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# Add endpoint to fetch user leaderboard history
@app.route('/api/user-stats/<user_identifier>/leaderboard-history')
def get_user_leaderboard_history(user_identifier):
    try:
        print(f"DEBUG: /api/user-stats/{user_identifier}/leaderboard-history endpoint hit")
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
            username = discord_info['username'] if discord_info else f'User{user_id_str}'
            avatar_url = discord_info['avatar_url'] if discord_info else f'https://randomuser.me/api/portraits/men/{user_id_str}.jpg'

            formatted_entry = {
                **entry,
                'username': username,
                'avatar_url': avatar_url
            }
            formatted_history.append(formatted_entry)

        print(f"DEBUG: /api/user-stats/{user_identifier}/leaderboard-history returning: {formatted_history}")
        return jsonify(formatted_history)
    except Exception as e:
        print(f"Error processing /api/user-stats/{user_identifier}/leaderboard-history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Add endpoint to fetch recent gaming sessions
# This route seems redundant with /api/user-stats/<user_identifier>/history
# Keeping it for now but may need to be removed later.
@app.route('/api/recent-activity')
def recent_activity():
    try:
        print("DEBUG: Fetching recent activity")
        activity_data = storage.get_recent_gaming_sessions()
        return jsonify(activity_data)
    except Exception as e:
        print(f"Error in recent_activity: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # In production, this won't be used as gunicorn will run the app
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port) 