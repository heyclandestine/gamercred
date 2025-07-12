#!/usr/bin/env python3
import os
import re

def update_html_file(file_path):
    """Update an HTML file to include the theme system."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add themes.css link
    if 'themes.css' not in content:
        # Find the last link rel="stylesheet" and add themes.css after it
        content = re.sub(
            r'(<link rel="stylesheet" href="[^"]*\.css">)',
            r'\1\n  <link rel="stylesheet" href="/css/themes.css">',
            content,
            count=1
        )
    
    # Add theme switcher to nav-right
    theme_switcher_html = '''      <div class="theme-switcher">
        <button class="theme-switcher-btn" id="theme-switcher-btn">
          <i class="fas fa-palette"></i>
          Theme
        </button>
        <div class="theme-dropdown" id="theme-dropdown">
          <div class="theme-option active" data-theme="default">
            <div class="theme-preview" style="background: linear-gradient(45deg, #23232b, #ff6fae);"></div>
            <span class="theme-name">Dark Gaming</span>
          </div>
          <div class="theme-option" data-theme="light-gaming">
            <div class="theme-preview" style="background: linear-gradient(45deg, #f8f9fa, #ff6fae);"></div>
            <span class="theme-name">Light Gaming</span>
          </div>
          <div class="theme-option" data-theme="cyberpunk">
            <div class="theme-preview" style="background: linear-gradient(45deg, #0a0a0f, #e94560);"></div>
            <span class="theme-name">Cyberpunk</span>
          </div>
          <div class="theme-option" data-theme="forest">
            <div class="theme-preview" style="background: linear-gradient(45deg, #1a2f1a, #4ade80);"></div>
            <span class="theme-name">Forest</span>
          </div>
          <div class="theme-option" data-theme="ocean">
            <div class="theme-preview" style="background: linear-gradient(45deg, #0f172a, #06b6d4);"></div>
            <span class="theme-name">Ocean</span>
          </div>
          <div class="theme-option" data-theme="sunset">
            <div class="theme-preview" style="background: linear-gradient(45deg, #1f1f2e, #fd79a8);"></div>
            <span class="theme-name">Sunset</span>
          </div>
          <div class="theme-option" data-theme="retro">
            <div class="theme-preview" style="background: linear-gradient(45deg, #2d1b69, #ffd700);"></div>
            <span class="theme-name">Retro</span>
          </div>
        </div>
      </div>'''
    
    # Replace nav-right section
    nav_right_pattern = r'<div class="nav-right">\s*<div id="auth-container">'
    if re.search(nav_right_pattern, content):
        content = re.sub(
            nav_right_pattern,
            f'<div class="nav-right">\n{theme_switcher_html}\n      <div id="auth-container">',
            content
        )
    
    # Add theme switcher JavaScript
    theme_js = '''  <script>
    // Theme Switcher Functionality
    document.addEventListener('DOMContentLoaded', function() {
      const themeSwitcherBtn = document.getElementById('theme-switcher-btn');
      const themeDropdown = document.getElementById('theme-dropdown');
      const themeOptions = document.querySelectorAll('.theme-option');
      
      // Load saved theme from localStorage
      const savedTheme = localStorage.getItem('selected-theme') || 'default';
      document.documentElement.setAttribute('data-theme', savedTheme);
      
      // Update active theme option
      themeOptions.forEach(option => {
        if (option.dataset.theme === savedTheme) {
          option.classList.add('active');
        } else {
          option.classList.remove('active');
        }
      });
      
      // Toggle dropdown
      themeSwitcherBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        themeDropdown.classList.toggle('show');
      });
      
      // Close dropdown when clicking outside
      document.addEventListener('click', function() {
        themeDropdown.classList.remove('show');
      });
      
      // Theme selection
      themeOptions.forEach(option => {
        option.addEventListener('click', function() {
          const selectedTheme = this.dataset.theme;
          
          // Remove active class from all options
          themeOptions.forEach(opt => opt.classList.remove('active'));
          
          // Add active class to selected option
          this.classList.add('active');
          
          // Apply theme
          document.documentElement.setAttribute('data-theme', selectedTheme);
          
          // Save to localStorage
          localStorage.setItem('selected-theme', selectedTheme);
          
          // Close dropdown
          themeDropdown.classList.remove('show');
        });
      });
    });
  </script>'''
    
    # Add JavaScript before closing body tag
    if '</body>' in content and 'Theme Switcher Functionality' not in content:
        content = re.sub(
            r'(</body>)',
            f'{theme_js}\n\\1',
            content
        )
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated {file_path}")

def main():
    """Update all HTML files in the pages directory."""
    pages_dir = "website/public/pages"
    
    # Files to update (excluding already updated ones)
    files_to_update = [
        "setrate.html",
        "user_stats.html", 
        "user.html"
    ]
    
    for filename in files_to_update:
        file_path = os.path.join(pages_dir, filename)
        if os.path.exists(file_path):
            update_html_file(file_path)
        else:
            print(f"File not found: {file_path}")

if __name__ == "__main__":
    main() 