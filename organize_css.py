#!/usr/bin/env python3
"""
CSS Organization Script
Extracts and organizes CSS from the main style.css file into separate files
"""

import re
import os

def extract_css_sections():
    """Extract CSS sections from the main style.css file"""
    
    # Read the main CSS file
    with open('website/public/style.css', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Define the sections to extract
    sections = {
        'base.css': {
            'start': 'body {',
            'end': '/* ===== TOAST NOTIFICATIONS ===== */',
            'includes': ['body', 'navbar', 'nav-', 'user-', 'discord-', 'main', 'card', 'avatar', 'user-link', 'game-link', 'back-link', 'loading-spinner', 'footer', 'toast']
        },
        'components.css': {
            'start': '/* ===== REUSABLE COMPONENTS ===== */',
            'end': '/* ===== RESPONSIVE DESIGN ===== */',
            'includes': ['react-btn', 'tab-btn', 'form-', 'search-', 'autocomplete', 'stat', 'game-cover', 'leaderboard', 'activity', 'bonuses']
        },
        'home.css': {
            'start': '/* ===== MAIN GRID LAYOUT ===== */',
            'end': '/* ===== RESPONSIVE DESIGN ===== */',
            'includes': ['main-grid', 'most-popular', 'log-game', 'activity-wide', 'timer-', 'carousel', 'activity-card']
        },
        'games.css': {
            'start': '/* ===== GAMES PAGE STYLES ===== */',
            'end': '/* ===== RESPONSIVE DESIGN ===== */',
            'includes': ['games-main', 'games-header', 'games-grid', 'game-card', 'sort-', 'filter-']
        },
        'game.css': {
            'start': '/* ===== GAME PAGE STYLES ===== */',
            'end': '/* ===== RESPONSIVE DESIGN ===== */',
            'includes': ['game-main', 'game-header', 'game-cover', 'game-stats', 'game-playing', 'game-activity', 'game-trailer']
        },
        'user.css': {
            'start': '/* ===== PROFILE PAGE ===== */',
            'end': '/* ===== RESPONSIVE DESIGN ===== */',
            'includes': ['profile-main', 'profile-card', 'profile-avatar', 'profile-stats', 'profile-activity']
        },
        'responsive.css': {
            'start': '/* ===== RESPONSIVE DESIGN ===== */',
            'end': None,
            'includes': ['@media', 'mobile-', 'desktop-']
        }
    }
    
    # Extract each section
    for filename, config in sections.items():
        print(f"Creating {filename}...")
        
        # Find the start and end positions
        start_pos = content.find(config['start'])
        if start_pos == -1:
            print(f"  Warning: Could not find start marker '{config['start']}' for {filename}")
            continue
            
        if config['end']:
            end_pos = content.find(config['end'], start_pos)
            if end_pos == -1:
                print(f"  Warning: Could not find end marker '{config['end']}' for {filename}")
                end_pos = len(content)
        else:
            end_pos = len(content)
        
        # Extract the section
        section_content = content[start_pos:end_pos]
        
        # Write to file
        with open(f'website/public/{filename}', 'w', encoding='utf-8') as f:
            f.write(f"/* ===== {filename.upper().replace('.CSS', '')} ===== */\n")
            f.write(f"/* Extracted from style.css */\n\n")
            f.write(section_content)
        
        print(f"  Created {filename} ({len(section_content)} characters)")

def create_css_import_file():
    """Create a main CSS file that imports all the separate files"""
    
    css_files = [
        'base.css',
        'components.css', 
        'home.css',
        'games.css',
        'game.css',
        'user.css',
        'responsive.css'
    ]
    
    with open('website/public/main.css', 'w', encoding='utf-8') as f:
        f.write("/* ===== MAIN CSS FILE ===== */\n")
        f.write("/* This file imports all CSS modules */\n\n")
        
        for css_file in css_files:
            if os.path.exists(f'website/public/{css_file}'):
                f.write(f"@import url('{css_file}');\n")
        
        f.write("\n/* ===== END OF IMPORTS ===== */\n")

if __name__ == "__main__":
    print("Organizing CSS files...")
    extract_css_sections()
    create_css_import_file()
    print("CSS organization complete!")
    print("\nFiles created:")
    print("- base.css (global styles)")
    print("- components.css (reusable components)")
    print("- home.css (homepage styles)")
    print("- games.css (games listing page)")
    print("- game.css (individual game page)")
    print("- user.css (user profile page)")
    print("- responsive.css (mobile/responsive)")
    print("- main.css (imports all files)") 