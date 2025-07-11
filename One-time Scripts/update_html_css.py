#!/usr/bin/env python3
"""
HTML CSS Update Script
Updates HTML files to use the new modular CSS structure
"""

import os
import re

def update_html_file(filepath, new_css_file):
    """Update an HTML file to use the new CSS file"""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the old style.css reference with the new CSS file
    # Look for both relative and absolute paths
    patterns = [
        r'href=["\']style\.css["\']',
        r'href=["\']/style\.css["\']',
        r'href=["\']\./style\.css["\']',
        r'href=["\']\.\./style\.css["\']'
    ]
    
    updated = False
    for pattern in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, f'href="{new_css_file}"', content)
            updated = True
    
    if updated:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath} to use {new_css_file}")
    else:
        print(f"No style.css reference found in {filepath}")

def main():
    """Update all HTML files to use the new CSS structure"""
    
    html_files = [
        ('website/public/index.html', 'main.css'),
        ('website/public/all_games.html', 'main.css'),
        ('website/public/game.html', 'main.css'),
        ('website/public/user.html', 'main.css')
    ]
    
    print("Updating HTML files to use new modular CSS structure...")
    
    for html_file, css_file in html_files:
        if os.path.exists(html_file):
            update_html_file(html_file, css_file)
        else:
            print(f"Warning: {html_file} not found")
    
    print("\nCSS reorganization complete!")
    print("\nNew CSS structure:")
    print("├── main.css (imports all files)")
    print("├── base.css (global styles)")
    print("├── components.css (reusable components)")
    print("├── home.css (homepage styles)")
    print("├── games.css (games listing page)")
    print("├── game.css (individual game page)")
    print("├── user.css (user profile page)")
    print("└── responsive.css (mobile/responsive)")
    
    print("\nBenefits of this structure:")
    print("✅ Better organization and maintainability")
    print("✅ Faster development (find styles faster)")
    print("✅ Easier debugging (isolated styles)")
    print("✅ Better caching (only load needed styles)")
    print("✅ Team collaboration (work on different files)")
    
    print("\nTo use page-specific CSS only:")
    print("For homepage: <link rel='stylesheet' href='base.css'> + <link rel='stylesheet' href='home.css'>")
    print("For games page: <link rel='stylesheet' href='base.css'> + <link rel='stylesheet' href='games.css'>")
    print("For game page: <link rel='stylesheet' href='base.css'> + <link rel='stylesheet' href='game.css'>")
    print("For user page: <link rel='stylesheet' href='base.css'> + <link rel='stylesheet' href='user.css'>")

if __name__ == "__main__":
    main() 