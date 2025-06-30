#!/usr/bin/env python3
"""
Test script to verify the session-based half-life calculation works correctly.
"""

import sys
import os

# Add the parent directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage import GameStorage

def test_session_half_life_calculation():
    """Test the session-based half-life calculation with various scenarios"""
    
    storage = GameStorage()
    
    # Test cases: (session_hours, total_game_hours, base_cph, half_life_hours, expected_credits)
    test_cases = [
        {
            'name': 'First session, no half-life',
            'session_hours': 24,
            'total_game_hours': 0,
            'base_cph': 400,
            'half_life_hours': None,
            'expected': 9600  # 24 * 400
        },
        {
            'name': 'First session, half-life 24h',
            'session_hours': 24,
            'total_game_hours': 0,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 9600  # 24 * 400 (all at full rate)
        },
        {
            'name': 'Second session, half-life 24h, total 48h',
            'session_hours': 24,
            'total_game_hours': 24,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 4800  # 24 * 200 (second half at half rate)
        },
        {
            'name': 'Third session, half-life 24h, total 72h',
            'session_hours': 24,
            'total_game_hours': 48,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 2400  # 24 * 100 (third half at quarter rate)
        },
        {
            'name': 'Fourth session, half-life 24h, total 96h',
            'session_hours': 24,
            'total_game_hours': 72,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 1200  # 24 * 50 (fourth half at eighth rate)
        },
        {
            'name': 'Large session spanning multiple half-lives',
            'session_hours': 100,
            'total_game_hours': 50,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 16800  # Complex calculation across multiple brackets
        }
    ]
    
    print("Testing session-based half-life calculation...")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        result = storage.calculate_credits_with_half_life_for_session(
            test_case['session_hours'],
            test_case['total_game_hours'],
            test_case['base_cph'],
            test_case['half_life_hours']
        )
        
        expected = test_case['expected']
        passed = abs(result - expected) < 0.01
        
        print(f"Test {i}: {test_case['name']}")
        print(f"  Session hours: {test_case['session_hours']}")
        print(f"  Total game hours (before): {test_case['total_game_hours']}")
        print(f"  Base CPH: {test_case['base_cph']}, Half-life: {test_case['half_life_hours']}")
        print(f"  Expected: {expected}, Got: {result}")
        print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")
        print()
    
    print("=" * 60)
    print("Session-based half-life calculation test completed!")

if __name__ == "__main__":
    test_session_half_life_calculation() 