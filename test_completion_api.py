#!/usr/bin/env python3
"""
Test script to check completion requirements API
"""

import requests
import json

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

def test_completion_requirements():
    """Test the completion requirements API"""
    
    # Get a real game from the database
    game_name = get_real_game()
    if not game_name:
        print("Could not get a real game from database")
        return
    
    user_id = "123456789"    # Replace with an actual user ID
    
    # Set up cookies to simulate logged-in user
    cookies = {
        'user_id': user_id,
        'discord_token': 'test_token'
    }
    
    # Test completion requirements endpoint
    url = f"http://localhost:5000/api/game/completion-requirements?name={game_name}"
    
    print(f"Testing completion requirements for game: {game_name}")
    print(f"URL: {url}")
    print(f"Cookies: {cookies}")
    
    try:
        response = requests.get(url, cookies=cookies)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error making request: {e}")

def test_completion_submission():
    """Test the completion submission API"""
    
    game_name = get_real_game()
    if not game_name:
        print("Could not get a real game from database")
        return
    
    user_id = "123456789"    # Replace with an actual user ID
    
    cookies = {
        'user_id': user_id,
        'discord_token': 'test_token'
    }
    
    data = {
        'game_name': game_name
    }
    
    url = "http://localhost:5000/api/game/complete"
    
    print(f"\nTesting completion submission for game: {game_name}")
    print(f"URL: {url}")
    print(f"Data: {data}")
    
    try:
        response = requests.post(url, json=data, cookies=cookies)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error making request: {e}")

def check_user_stats():
    """Check user stats to see if credits were added"""
    user_id = "123456789"
    
    url = f"http://localhost:5000/api/user-stats/{user_id}"
    
    print(f"\nChecking user stats for user: {user_id}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"User stats: {json.dumps(data, indent=2)}")
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    print("Testing Completion Requirements API")
    print("=" * 50)
    
    test_completion_requirements()
    test_completion_submission()
    check_user_stats()