#!/usr/bin/env python3
"""
Test script to verify the half-life calculation works correctly.
"""

import sys
import os

# Add the parent directory to the path so we can import our models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage import GameStorage

def test_half_life_calculation():
    """Test the half-life calculation with various scenarios"""
    
    storage = GameStorage()
    
    # Test cases
    test_cases = [
        {
            'name': 'No half-life (24 hours)',
            'hours': 24,
            'base_cph': 400,
            'half_life_hours': None,
            'expected': 9600  # 24 * 400
        },
        {
            'name': 'Half-life 24h, 24 hours played',
            'hours': 24,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 9600  # 24 * 400 (all at full rate)
        },
        {
            'name': 'Half-life 24h, 48 hours played',
            'hours': 48,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 14400  # 24 * 400 + 24 * 200
        },
        {
            'name': 'Half-life 24h, 96 hours played',
            'hours': 96,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 16800  # 24 * 400 + 24 * 200 + 48 * 100
        },
        {
            'name': 'Half-life 24h, 168 hours played',
            'hours': 168,
            'base_cph': 400,
            'half_life_hours': 24,
            'expected': 18000  # 24 * 400 + 24 * 200 + 48 * 100 + 72 * 50
        }
    ]
    
    print("Testing half-life calculation...")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        result = storage.calculate_credits_with_half_life(
            test_case['hours'],
            test_case['base_cph'],
            test_case['half_life_hours']
        )
        
        expected = test_case['expected']
        passed = abs(result - expected) < 0.01
        
        print(f"Test {i}: {test_case['name']}")
        print(f"  Hours: {test_case['hours']}, Base CPH: {test_case['base_cph']}, Half-life: {test_case['half_life_hours']}")
        print(f"  Expected: {expected}, Got: {result}")
        print(f"  Status: {'✅ PASS' if passed else '❌ FAIL'}")
        print()
    
    print("=" * 50)
    print("Half-life calculation test completed!")

if __name__ == "__main__":
    test_half_life_calculation() 