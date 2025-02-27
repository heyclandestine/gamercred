import os

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN', '')
COMMAND_PREFIX = '!'

# Command list
COMMANDS = {
    'log': '!log <hours> <game> - Log your gaming hours',
    'setrate': '!setrate <credits> <game> - Set credits per hour for a game (0.1-10.0)',
    'rate': '!rate <game> - Check credits per hour for a game',
    'balance': '!balance - Check your gamer cred balance',
    'leaderboard': '!leaderboard - View the gamer cred leaderboard',
    'help': '!help - Show this help message'
}

# Messages
MESSAGES = {
    'invalid_hours': '❌ Please provide a valid number of hours (between 0.5 and 24)',
    'invalid_game': '❌ Please provide a game name',
    'success_log': '✅ Successfully logged {hours} hours for {game}! You earned {credits} cred!',
    'no_balance': '😢 You haven\'t earned any gamer cred yet. Start playing!',
    'balance': '🎮 Your current gamer cred balance is: {credits}',
    'error': '❌ An error occurred: {error}',
    'no_data': '📝 No gaming data available yet!'
}