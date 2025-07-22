#!/usr/bin/env python3
"""
Test script to log hours and then test completion with credits
"""

import requests
import json
from datetime import datetime

def get_real_game():
    """Get a real game from the database"""
    try:
        response = requests.get("http://localhost:5000/api/all-games")
        if response.status_code == 200:
            games = response.json()
            if games:
                return games[0]['name']  # Return the first game
        return None
    except Exception as e:
        print(f"Error getting games: {e}")
        return None

def log_game_hours(game_name, hours=3.5):
    """Log hours for a game"""
    user_id = "123456789"
    
    cookies = {
        'user_id': user_id,
        'discord_token': 'test_token'
    }
    
    data = {
        'user_id': user_id,
        'game_name': game_name,
        'hours': hours,
        'players': 1
    }
    
    url = "http://localhost:5000/api/log-game"
    
    print(f"Logging {hours} hours for game: {game_name}")
    
    try:
        response = requests.post(url, json=data, cookies=cookies)
        print(f"Log game response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Log game response: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error logging game: {e}")
        return False

def test_completion_with_hours():
    """Test completion after logging hours"""
    
    game_name = get_real_game()
    if not game_name:
        print("Could not get a real game from database")
        return
    
    user_id = "123456789"
    
    # Step 1: Log some hours
    print("Step 1: Logging hours...")
    if not log_game_hours(game_name, 3.5):
        print("Failed to log hours")
        return
    
    # Step 2: Check completion requirements
    print("\nStep 2: Checking completion requirements...")
    cookies = {'user_id': user_id, 'discord_token': 'test_token'}
    
    response = requests.get(f"http://localhost:5000/api/game/completion-requirements?name={game_name}", cookies=cookies)
    if response.status_code == 200:
        data = response.json()
        print(f"Completion requirements: {json.dumps(data, indent=2)}")
    else:
        print(f"Error checking requirements: {response.text}")
        return
    
    # Step 3: Try to complete the game
    print("\nStep 3: Attempting to complete the game...")
    data = {'game_name': game_name}
    
    response = requests.post("http://localhost:5000/api/game/complete", json=data, cookies=cookies)
    print(f"Completion response status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Completion response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error response: {response.text}")
        return
    
    # Step 4: Check user stats to see if credits were added
    print("\nStep 4: Checking user stats...")
    response = requests.get(f"http://localhost:5000/api/user-stats/{user_id}")
    if response.status_code == 200:
        data = response.json()
        print(f"User stats after completion: {json.dumps(data, indent=2)}")
    else:
        print(f"Error checking user stats: {response.text}")

if __name__ == "__main__":
    print("Testing Completion with Hours and Credits")
    print("=" * 50)
    
    test_completion_with_hours() 