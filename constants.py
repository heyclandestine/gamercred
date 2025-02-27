import os
from collections import OrderedDict

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN', '')
COMMAND_PREFIX = '!'

# Command list - ordered by frequency of use
COMMANDS = OrderedDict([
    ('log', '!log <hours> <game> - Log your gaming hours'),
    ('balance', '!balance - Check your gamer cred balance'),
    ('history', '!history - View your gaming history'),
    ('mystats', '!mystats - Show your overall gaming statistics or use !mystats <game> for game-specific stats'),
    ('achievements', '!achievements - View your gaming achievements'),
    ('leaderboard', '!leaderboard - View the all-time gamer cred leaderboard'),
    ('weekly', '!weekly - View the weekly gamer cred leaderboard'),
    ('monthly', '!monthly - View the monthly gamer cred leaderboard'),
    ('rate', '!rate <game> - Check credits per hour for a game'),
    ('setrate', '!setrate <credits> <game> - Set credits per hour for a game'),
    ('gamestats', '!gamestats <game> - View detailed statistics for a specific game'),
    ('userstats', '!userstats @user <game> - View another user\'s gaming statistics, optionally for a specific game'),
    ('addbonus', '!addbonus @user <amount> <reason> - Add or remove bonus cred (Mod only)'),
    ('renamegame', '!renamegame "Old Name" "New Name" - Rename a game (Mod only)'),
    ('deletegame', '!deletegame <game> - Delete a game from the database (Mod only)'),
    ('help', '!help - Show this help message')
])

# Messages
MESSAGES = {
    'invalid_hours': '❌ Please provide a valid number of hours',
    'invalid_game': '❌ Please provide both hours and game name (!log <hours> <game>)',
    'success_log': '✅ Successfully {action} {hours} hours for {game}! {earned} {credits} cred!',
    'no_balance': '😢 You haven\'t earned any gamer cred yet. Start playing!',
    'balance': '🎮 Your current gamer cred balance is: {credits}',
    'error': '❌ An error occurred: {error}',
    'no_data': '📝 No gaming data available yet!'
}