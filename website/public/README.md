# Website Folder Structure

This directory contains the organized static files for the Gamer Cred website.

## Folder Organization

### `/css/` - Stylesheets
- `main.css` - Main stylesheet (contains all styles)
- `base.css` - Base/global styles (modular, unused)
- `components.css` - Reusable component styles (modular, unused)
- `home.css` - Homepage-specific styles (modular, unused)
- `games.css` - Games listing styles (modular, unused)
- `game.css` - Individual game page styles (modular, unused)
- `user.css` - User profile styles (modular, unused)
- `responsive.css` - Mobile/responsive styles (modular, unused)
- `style.css` - Original stylesheet (backup)
- `styles.css` - Additional styles

### `/js/` - JavaScript Files
- `script.js` - Main JavaScript functionality
- `search.js` - Search functionality

### `/images/` - Image Assets
- `favicon.png` - Website favicon

### `/pages/` - HTML Pages
- `index.html` - Homepage (served from root route)
- `all_games.html` - All games listing page
- `game.html` - Individual game page
- `user.html` - User profile page (includes total hours, games played, sessions stats)

### `/docs/` - Documentation
- `CSS_STRUCTURE.md` - CSS organization documentation

## File Paths

All HTML files now reference assets using absolute paths:
- CSS: `/css/main.css`
- JavaScript: `/js/script.js`
- Images: `/images/favicon.png`
- Pages: `/pages/game.html`, `/pages/user.html`, etc.

## Notes

- The modular CSS files (base.css, components.css, etc.) are created but currently unused
- The main.css file contains all the original styles
- All file paths have been updated to reference the new folder structure
- Flask routes have been updated to serve HTML files from the `/pages/` folder 

## Features

### User Profile Page
The user profile page (`/pages/user.html`) displays comprehensive user statistics including:
- **Total Credits** - Points earned from gaming
- **Rank** - User's position on the leaderboard
- **Total Hours** - Total time spent gaming
- **Games Played** - Number of unique games played
- **Total Sessions** - Number of gaming sessions logged
- **Most Played Games** - Top games by playtime (weekly/monthly/all-time)
- **Recent Activity** - Latest gaming sessions
- **Leaderboard History** - Previous leaderboard placements 